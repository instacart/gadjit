#!/usr/bin/env python3

import click
import json
import os
import yaml
import logging

from collections import defaultdict
from gadjit import utils
from gadjit import models


# Entrypoint for use as a command-line tool
@click.command()
@click.option(
    "--config",
    "config_path",
    default="config.yaml",
    help="Path to the configuration file.",
)
def main(config_path):
    run(config_path=config_path)


# Entrypoint as an AWS Lambda deployment
def lambda_handler(event, context):
    try:
        run(event=event)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": True}),
        }
    except Exception as e:
        raise e
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": False, "message": str(e)}),
        }


def run(config_path=None, event=None):
    """
    Run the access approval workflow using various plugins.

    Args:
        config_path: The path to a config.yaml file.
        event: The event triggering the access approval workflow, if invoked via Lambda.

    Raises:
        RuntimeError: If more than one IGA or LLM plugin is enabled, or if no Scoring plugins are enabled.
    """

    # Try to load the config from disk, then fall back to envs.
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
            config = utils.process_env_variables(config)
    else:
        config = _config_from_environment()

    # Set global log level
    logging.basicConfig(
        level=getattr(logging, config.get("gadjit").get("log_level", "info").upper())
    )

    # Load all plugins
    iga_plugins = utils.load_plugins("iga", config)
    if len(iga_plugins) != 1:
        raise RuntimeError("Exactly one IGA plugin can be enabled at a time.")
    iga_plugin = iga_plugins[0]

    llm_plugins = utils.load_plugins("llm", config)
    if len(llm_plugins) != 1:
        raise RuntimeError("Exactly one LLM plugin can be enabled at a time.")
    llm_plugin = llm_plugins[0]

    scoring_plugins = utils.load_plugins("scoring", config)
    if len(scoring_plugins) < 1:
        raise RuntimeError("At least one Scoring plugin must be enabled.")

    # Get all access requests and process them
    access_requests = iga_plugin.retrieve_requests(event)
    for access_request in access_requests:

        enforce_rejection = False
        enforce_needs_manual_review = False
        scores = []
        for score_result in utils.plugins_run_function(
            scoring_plugins, "compute_scores", access_request, llm_plugin
        ):
            # If any Score plugin returns '0', don't auto-approve no matter what other plugins say
            if score_result == 0:
                enforce_needs_manual_review = True
            # If any Score plugin returns '-1', instantly reject the request
            elif score_result < 0:
                enforce_rejection = True

            scores.append(score_result)

        final_score = sum(scores) / len(scores)
        final_score = round(final_score, 2)

        refer_to_myself_as = config.get("gadjit").get("refer_to_myself_as", "Gadjit")
        comment = None
        if enforce_rejection:
            logging.info(
                f"Rejecting {access_request.requester.email} be added to {access_request.entitlement.name} as a plugin requested immediate rejection."
            )
            comment = (
                f"{refer_to_myself_as} "
                f"has reviewed this access request and does not believe this access is appropriate. "
                f"This is an automated message."
            )
            iga_plugin.comment_request(access_request, comment)
            # iga_plugin.deny_request(access_request)  # TODO uncomment
        elif enforce_needs_manual_review or final_score < 1:
            logging.info(
                f"Score: {final_score}; recommending {access_request.requester.email} NOT be added to {access_request.entitlement.name}."
            )
            comment = (
                f"{refer_to_myself_as} "
                f"has reviewed this access request and found that most of the requestor's "
                f"peers do not utilize this role as part of their job functions. "
                f"Please carefully review this request and ensure it is appropriate "
                f"to provide the requestor access. This is an automated message."
            )
            if config.get("gadjit").get("include_score_in_comments", False):
                comment = f"{comment} [{final_score}]"
            # iga_plugin.comment_request(access_request, comment)  # TODO uncomment
        elif final_score >= 1:
            logging.info(
                f"Score: {final_score}; recommending {access_request.requester.email} be added to {access_request.entitlement.name}."
            )
            comment = (
                f"{refer_to_myself_as} "
                f"has reviewed this access request and believes this access is appropriate. "
                f"This is an automated message."
            )
            if config.get("gadjit").get("include_score_in_comments", False):
                comment = f"{comment} [{final_score}]"
            # iga_plugin.comment_request(access_request, comment)  # TODO uncomment

            # Some config sanity needed here. This value can come in as a comma-delimited string or a list
            entitlements_to_auto_approve = config.get("gadjit").get(
                "entitlements_to_auto_approve", []
            )
            if isinstance(entitlements_to_auto_approve, str):
                entitlements_to_auto_approve = entitlements_to_auto_approve.split(",")

            # Clean up the list entries
            entitlements_to_auto_approve = [
                x.strip().lower() for x in entitlements_to_auto_approve
            ]

            # Check if the entitlement requested is on the list
            if (
                access_request.entitlement.name.lower() in entitlements_to_auto_approve
            ) or (
                access_request.entitlement.id.lower() in entitlements_to_auto_approve
            ):
                # iga_plugin.approve_request(access_request)  # TODO uncomment
                logging.info(
                    f"Requested entitlement is on the allow list for automatic approval. User {access_request.requester.email} has been added to {access_request.entitlement.name}."
                )


def _config_from_environment():
    """
    Create a scheme for configuring with environmental variables
    (especially nice for lambda/container deployments). This logic
    converts envs to a dictionary compatible with the one assembled
    from the YAML config file in the following manner:

    Example 1: Configure the Gadjit option "log_level"
    GADJIT_GADJIT_LOG_LEVEL="info"

    Example 2: Enable the first-defined IGA plugin
    GADJIT_IGA_PLUGINS_0_ENABLED=true

    Example 3: Set the first-defined LLM plugin's config value 'secret_key'
    GADJIT_LLM_PLUGINS_0_CONFIG_SECRET_KEY="OPENAI_API_KEY"

    Args:
        None

    Returns:
        dict: A full config dictionary.
    """
    config = {}

    for key, value in os.environ.items():
        if key.startswith("GADJIT_"):
            parts = key.split("__")
            section = parts[1].lower()
            if section == "gadjit":
                config.setdefault("gadjit", {})[parts[2].lower()] = (
                    value.lower() in ["true"]
                    if value.lower() in ["true", "false"]
                    else value
                )
            else:
                plugin_index = int(parts[3])
                plugin_key = parts[4].lower()

                if not f"{section}_plugins" in config:
                    config[f"{section}_plugins"] = []

                if len(parts) > 5:
                    plugin_subkey = parts[5].lower()
                    try:
                        config[f"{section}_plugins"][plugin_index]
                    except IndexError:
                        config[f"{section}_plugins"].append(
                            {"name": None, "enabled": None, "config": None}
                        )

                    if not config[f"{section}_plugins"][plugin_index][plugin_key]:
                        config[f"{section}_plugins"][plugin_index][plugin_key] = {}

                    config[f"{section}_plugins"][plugin_index][plugin_key].update(
                        {plugin_subkey: value}
                    )
                else:
                    try:
                        config[f"{section}_plugins"][plugin_index]
                    except IndexError:
                        config[f"{section}_plugins"].append(
                            {"name": None, "enabled": None, "config": None}
                        )

                    config[f"{section}_plugins"][plugin_index][plugin_key] = (
                        value.lower() in ["true"]
                        if value.lower() in ["true", "false"]
                        else value
                    )
    return config


if __name__ == "__main__":
    main()
