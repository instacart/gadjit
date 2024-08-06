# Gadjit: Automated Access Request Reviews

<img src="https://i.imgur.com/9LFOj2T.png" width="200">

**Gadjit** (pronounced "gadget") is an LLM-powered security bot framework designed to automate analyizing and taking action on access requests. Developed and open-sourced by **Instacart**, Gadjit leverages the power of Large Language Models (LLMs) to sift through identity information and seeks to end the status quo of "rubber stamp" access approvals commonly seen within manual access request processes.

## Plugin Architecture

Gadjit attempts to be a vendor-neutral framework for reviewing access requests. We achieve this with a plugin system which supports three different types of plugins:

-   **IGA Plugins**: integrate with governance tools such as ConductorOne, Opal, or Lumos.
-   **LLM Plugins**: integrate with LLMs such as OpenAI, Athropic, or Gemini.
-   **Scoring Plugins**: evaluate an access request based on a set of factors and return a score.

We strongly encourage contribution of new plugins, please open a pull request!

### Currently-Supported IGA Plugins
-   [ConductorOne](https://www.conductorone.com/)

### Currently-Supported LLM Plugins
-   [OpenAI GPT-4o](https://openai.com/)
-   [OpenAI GPT-4o via AWS API Gateway with IAM Authentication](https://mattslifebytes.com/2024/06/13/safely-accessing-an-internal-alb-in-a-private-subnet-using-aws-api-gateway-and-terraform-and-python/) (Instacart uses an OpenAI proxy internally)

### Currently-Supported Scoring Plugins

#### Requester Profile Attribute Proximity
Analyzes the requested entitlement's members looking for commonality with the requester ("Does the requester's peers use this role in their day to day work?").

## Installation

### Prerequisites

-   Python 3.12
-   Library dependencies (see `requirements.txt`)
    
## Deployment

Gadjit can be run as a web server / AWS Lambda (best used for receiving webhook events), or as a one-shot application invoked with a cron job once per minute.

### Using With an AWS Lambda

Package the Lambda zip. For an ARM-based Mac, this can be done with Docker:
```
docker run --platform linux/amd64 --mount type=bind,source=$PWD,target=/tmp --entrypoint "/bin/bash" -it public.ecr.aws/lambda/python:3.12 "-c" "dnf install -y zip && cd /tmp && rm -f lambda.zip && mkdir -p build && pip install . -t build && pip install -r requirements.txt -t build && cd build && zip -r ../lambda.zip * && cd .. && rm -rf build"
```

Deploy the resulting `lambda.zip` to AWS Lambda with at least 512MB of memory and at least a 120-second timeout. Set the runtime handler to `gadjit.lambda_handler`. Enable "Function URL" for your Lambda (with Auth Type=NONE and save. It is now ready to receive webhooks.

### Using as a Web Server

Install requirements:
`pip install -Ur requirements.txt`

Invoke:
`python -m gadjit --server (--port 8080) (--config config.yaml)`

### Using as a CLI Tool

Install requirements:
`pip install -Ur requirements.txt`

Invoke:
`python -m gadjit (--config config.yaml)`

## Configuration

### YAML-Based Config
Copy `config.yaml.template` to `config.yaml` and set the necessary values. A value can be defined in the YAML file or be referenced to an environmental variable by adding the prefix "env:"; whatever follows will be looked up in the current environment variables. For example:

```yaml
gadjit:
  log_level: "env:GADJIT_LOG_LEVEL"
```
... means that the log level will be set to whatever the current value of the `GADJIT_LOG_LEVEL` env may be.

### Env-Based Config
In some deployments (such as AWS Lambda), file-based configuration may not be ideal. In these cases, you can also configure Gadjit entirely with environment variables.

```bash
GADJIT__GADJIT__LOG_LEVEL=debug \
GADJIT__GADJIT__ENTITLEMENTS_TO_AUTO_APPROVE="Some-Entitlement-Name,2cxuJXhzhPoqvbJR75xq8ZVCBsK,Team - Security" \
GADJIT__IGA__PLUGINS__0__NAME=conductorone_cron \
GADJIT__IGA__PLUGINS__0__ENABLED=true \
GADJIT__IGA__PLUGINS__0__CONFIG__REASSIGN_TO_USER=2cxuJXhzhPoqvbJR75xq8ZVCBsK \
GADJIT__IGA__PLUGINS__0__CONFIG__BASE_URL="https://acme.conductor.one" \
GADJIT__IGA__PLUGINS__0__CONFIG__CLIENT_ID="strange-hydra-68836@acme.conductor.one/pcc" \
GADJIT__IGA__PLUGINS__0__CONFIG__CLIENT_SECRET="CONDUCTORONE_API_SECRET" \
GADJIT__SCORING__PLUGINS__0__NAME=requester_profile_attribute_proximity \
GADJIT__SCORING__PLUGINS__0__ENABLED=true \
GADJIT__LLM__PLUGINS__0__NAME=openai \
GADJIT__LLM__PLUGINS__0__ENABLED=true \
GADJIT__LLM__PLUGINS__0__CONFIG__SECRET_KEY="OPENAI_API_KEY"
```

## Contributing

We welcome contributions from the community. We are especially interested in adding support for more IGA tools and additional configurability.

## License

This project is licensed under the The **2.0** version of the **Apache License** - see the LICENSE file for details.

## Contact

For questions or support, please open an issue in the repository.

----------

Developed with ❤️  by Instacart

