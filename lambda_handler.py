import gadjit


def lambda_handler(event, context):
    gadjit.run(event)


lambda_handler({}, None)
