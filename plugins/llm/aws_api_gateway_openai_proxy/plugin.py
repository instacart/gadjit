import base64
import boto3
import json
import requests
import logging

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timedelta
from models import BaseGadjitLLMPlugin


class AWSAPIGatewayOpenAIProxyPlugin(BaseGadjitLLMPlugin):
    api_gateway_role_credentials = None
    api_gateway_role_credentials_timestamp = None

    def query(self, system_prompt, user_prompt):
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
            url=self.config.get('api_gateway_url'),
            data=json.dumps(data),
            params=None,
            headers=headers,
        )
        SigV4Auth(self._get_access_token(), "execute-api", "us-east-1").add_auth(req)
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

    def _get_access_token(self):
        # Have we assumed our target role and saved session creds?
        if not self.api_gateway_role_credentials or (
            datetime.now() - self.api_gateway_role_credentials_timestamp > timedelta(minutes=5)
        ):
            logging.debug(
                f"Refreshing AWS credentials. Last cached timestamp: {self.api_gateway_role_credentials_timestamp}"
            )
            credentials = self.__assume_role(self.config.get('api_gateway_role_arn'))

            # Update boto3 session with assumed role credentials
            boto3_session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
            self.api_gateway_role_credentials = (
                boto3_session.get_credentials().get_frozen_credentials()
            )
            self.api_gateway_role_credentials_timestamp = datetime.now()
        else:
            logging.debug(
                f"Using cached AWS credentials. Last cached timestamp: {self.api_gateway_role_credentials_timestamp}"
            )

        return self.api_gateway_role_credentials

    def __assume_role(self, role_arn):
        sts_client = boto3.client("sts")
        assumed_role = sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName="aigateway-session"
        )
        credentials = assumed_role["Credentials"]
        return credentials
