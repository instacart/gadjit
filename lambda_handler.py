import gadjit


def lambda_handler(event, context):
    """
    Handle Lambda function event.

    Args:
        event (dict): The input event data for the Lambda function.
        context (object): The runtime context object for the Lambda function.

    Returns:
        None

    Notes:
        This function is a Lambda handler that executes the 'gadjit.run' function with the provided event data.
    """
    gadjit.run(event)


lambda_handler({}, None)
