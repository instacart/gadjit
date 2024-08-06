#!/usr/bin/env python3

import click
import logging
import os

from flask import Flask, request, jsonify
from gadjit import handler

app = Flask(__name__)


# Entrypoint for use as a command-line tool
@click.command()
@click.option(
    "--config",
    "config_path",
    default="config.yaml",
    help="Path to the configuration file.",
)
@click.option("--server", is_flag=True, help="Enable server mode.")
@click.option(
    "--port",
    default=8080,
    type=int,
    show_default=True,
    help="Port to run the server on.",
)
@click.pass_context
def main(ctx, config_path, server, port):
    if server and port is None:
        raise click.UsageError(
            "The '--port' option is required when '--server' is specified."
        )

    if server:
        app.config["CONFIG_PATH"] = config_path
        os.environ["FLASK_ENV"] = "production"
        app.run(host="0.0.0.0", port=port)
    else:
        handler.run(config_path=config_path)


# Handler for the Flask HTTP request
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        event = request.get_json()
    else:
        event = None

    try:
        handler.run(config_path=app.config.get("CONFIG_PATH"), event=event)
        return jsonify({"success": True}), 200
    except Exception as e:
        logging.exception("An unhandled exception was raised during execution.")
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    main()
