import yaml
import logging
import models
import utils


# Load configuration
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)
    config = utils.process_env_variables(config)

logging.basicConfig(level=getattr(logging, config.get('gadjit').get('log_level').upper()))

def run(event):

    # Load all plugins
    iga_plugins = utils.load_plugins('iga', config)
    if len(iga_plugins) != 1:
        raise RuntimeError("Only one IGA plugin can be enabled at a time.")
    iga_plugin = iga_plugins[0]

    llm_plugins = utils.load_plugins('llm', config)
    if len(llm_plugins) != 1:
        raise RuntimeError("Only one LLM plugin can be enabled at a time.")
    llm_plugin = llm_plugins[0]

    scoring_plugins = utils.load_plugins('scoring', config)
    if len(scoring_plugins) < 1:
        raise RuntimeError("At least one Scoring plugin must be enabled.")

    access_requests = iga_plugin.retrieve_requests(event)
    for access_request in access_requests:
        scores = []
        for score_result in utils.plugins_run_function(scoring_plugins, "compute_scores", access_request, llm_plugin):
            scores.append(score_result)

        final_score = sum(scores) / len(scores)
        final_score = round(final_score, 2)

        comment = None
        if final_score >= 1:
            logging.info(
                f"Recommending {access_request.requester.email} be added to {access_request.entitlement.name} automatically."
            )
            comment = (
                f"The Instacart Security team's AI-powered access assistance bot "
                f"has reviewed this access request and believes this access is appropriate. "
                f"This is an automated message. [{final_score}]"
            )
            iga_plugin.comment_request(access_request, comment)
            iga_plugin.approve_request(access_request)
        else:
            logging.info(
                f"Recommending {access_request.requester.email} NOT be added to {access_request.entitlement.name} automatically."
            )
            comment = (
                f"The Instacart Security team's AI-powered access assistance bot "
                f"has reviewed this access request and found that most of the requestor's "
                f"peers do not utilize this role as part of their job functions. "
                f"Please carefully review this request and ensure it is appropriate "
                f"to provide the requestor access. This is an automated message. [{final_score}]"
            )
            iga_plugin.comment_request(access_request, comment)
