import base64
import boto3
import json
import requests
import logging
import os

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timedelta

AI_GATEWAY_URL = os.getenv("AI_GATEWAY_URL")
AI_GATEWAY_ROLE_ARN = os.getenv("AI_GATEWAY_ROLE_ARN")

AI_GATEWAY_ROLE_CREDENTIALS = None
AI_GATEWAY_ROLE_CREDENTIALS_TIMESTAMP = None


def initialize():
    """
    Initialize function with no parameters.

    This function does not perform any operation and serves as a placeholder for future functionality.

    Args:
        None

    Returns:
        None
    """
    pass


def query(system_prompt, user_prompt):
    """
    Send a query to an AI system and retrieve the response.

    Args:
        system_prompt (str): The prompt for the AI system.
        user_prompt (str): The prompt for the user.

    Returns:
        str: The response from the AI system.

    Raises:
        Exception: If the response from the AI system contains an error message.
        JSONDecodeError: If there is an issue decoding the JSON response.
        KeyError: If there is a key error in parsing the response.
        TypeError: If there is a type error in parsing the response.
    """
    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 1,
        "max_tokens": 512,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
    }
    method = "POST"

    # Generate SigV4 signed request
    req = AWSRequest(
        method=method,
        url=AI_GATEWAY_URL,
        data=json.dumps(data),
        params=None,
        headers=headers,
    )
    SigV4Auth(_get_access_token(), "execute-api", "us-east-1").add_auth(req)
    req = req.prepare()

    # send request
    response = requests.request(
        method=req.method, url=req.url, headers=req.headers, data=req.body
    )

    try:
        result = response.json()
    except JSONDecodeError as e:
        logging.exception(
            f"The following content caused the JSONDecodeError: {response.content}"
        )
        raise e

    if result.get("error"):
        raise Exception(result.get("error").get("message"))

    try:
        if result.get("choices")[0].get("finish_reason") != "stop":
            return None
    except (KeyError, TypeError) as e:
        logging.exception(
            f"OpenAI response could not be understood. The API returned the following content: {response.content}"
        )
        raise e

    else:
        content = result.get("choices")[0].get("message", {}).get("content")
        try:
            # Diagnostic use, log the base64 of the response content for later debugging
            logging.debug(base64.b64encode(content.encode("utf-8")))
        except Exception as e:
            logging.exception(f"Could not base64 the content: {content}")

        return content


def _get_access_token():
    """
    Get the access token for AWS credentials.

    If the AWS credentials are not cached or have expired, refresh them by assuming the specified role.

    Returns:
        credentials (botocore.credentials.Credentials): The AWS credentials after assuming the specified role.

    Notes:
        The function updates the global variables AI_GATEWAY_ROLE_CREDENTIALS and AI_GATEWAY_ROLE_CREDENTIALS_TIMESTAMP.

    Raises:
        RuntimeError: If there is an issue assuming the role or getting the credentials.
    """
    global AI_GATEWAY_ROLE_CREDENTIALS, AI_GATEWAY_ROLE_CREDENTIALS_TIMESTAMP

    # Have we assumed our target role and saved session creds?
    if not AI_GATEWAY_ROLE_CREDENTIALS or (
        datetime.now() - AI_GATEWAY_ROLE_CREDENTIALS_TIMESTAMP > timedelta(minutes=5)
    ):
        logging.debug(
            f"Refreshing AWS credentials. Last cached timestamp: {AI_GATEWAY_ROLE_CREDENTIALS_TIMESTAMP}"
        )
        credentials = __assume_role(AI_GATEWAY_ROLE_ARN)

        # Update boto3 session with assumed role credentials
        boto3_session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
        AI_GATEWAY_ROLE_CREDENTIALS = (
            boto3_session.get_credentials().get_frozen_credentials()
        )
        AI_GATEWAY_ROLE_CREDENTIALS_TIMESTAMP = datetime.now()
    else:
        logging.debug(
            f"Using cached AWS credentials. Last cached timestamp: {AI_GATEWAY_ROLE_CREDENTIALS_TIMESTAMP}"
        )

    return AI_GATEWAY_ROLE_CREDENTIALS


def __assume_role(role_arn):
    """
    Assume an IAM Role using AWS STS service.

    Args:
        role_arn (str): The Amazon Resource Name (ARN) of the IAM role to assume.

    Returns:
        dict: A dictionary containing the temporary security credentials.

    Raises:
        AWSClientError: If there's an issue with the boto3 client or assuming the role.
    """
    sts_client = boto3.client("sts")
    assumed_role = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName="aigateway-session"
    )
    credentials = assumed_role["Credentials"]
    return credentials
