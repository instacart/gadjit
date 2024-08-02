# Gadjit

**Gadjit** (pronounced "gadget") is an LLM-powered bot designed to automate access request approvals. Developed and open-sourced by Instacart, Gadjit leverages the power of Large Language Models (LLMs) to review and approve access requests.

## Installation

### Prerequisites

-   Python 3.12
-   AWS CLI configured with appropriate permissions
-   Docker (for local testing and deployment)
    
## Build on M1 Mac

```
docker run --platform linux/amd64 --mount type=bind,source=$PWD,target=/tmp --entrypoint "/bin/bash" -it public.ecr.aws/lambda/python:3.12 "-c" "dnf install -y zip && cd /tmp && rm -f lambda.zip && mkdir -p build && cp -r *.py build && pip install -r requirements.txt -t build && cd build && zip -r ../lambda.zip * && cd .. && rm -rf build"
```

## Usage

After deployment, Gadjit can be triggered by AWS Lambda function URL. You can integrate it with your access request systems to start automating approvals immediately.

## Contributing

We welcome contributions from the community.

## License

This project is licensed under the The **2.0** version of the **Apache License** - see the LICENSE file for details.

## Contact

For questions or support, please open an issue in the repository.

----------

Developed with ❤️  by Instacart
