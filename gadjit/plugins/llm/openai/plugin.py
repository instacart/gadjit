import base64
import boto3
import json
import requests
import logging

from gadjit.models import BaseGadjitLLMPlugin


class OpenAIPlugin(BaseGadjitLLMPlugin):
    """
    A class representing an OpenAI Plugin.

    Methods:
        query(self, system_prompt, user_prompt): Sends a query to the OpenAI API and retrieves a response.

    Attributes:
        Inherits from BaseGadjitLLMPlugin.
    """

    def query(self, system_prompt, user_prompt):
        """
        Query the OpenAI API for a completion given system and user prompts.

        Args:
            system_prompt (str): A prompt for the system to start the conversation.
            user_prompt (str): A prompt for the user to continue the conversation.

        Returns:
            str: The completion of the conversation generated by the OpenAI API.

        Raises:
            Exception: If there is an error message returned by the API.
            JSONDecodeError: If there is an issue decoding the JSON response.
            KeyError: If a key is missing in the response JSON.
            TypeError: If there is a type error while processing the response.
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.get('secret_key')}",
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

        response = requests.post(url, headers=headers, json=data)

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
