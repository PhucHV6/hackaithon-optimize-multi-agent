import json
import logging
from aws_agent import AWSAgent

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Lambda invoked with event: %s", json.dumps(event))

    action_group = event['actionGroup']
    function = event['function']
    message_version = event.get('messageVersion',1)
    parameters = event.get("parameters", [{"name": "content", "type": "string", "value": "blank"}])
    file_name = parameters[0]["value"]
    content = parameters[1]["value"]

    logger.info("File name: %s", file_name)

    if not content:
        logger.warning("Missing 'content' in request.")
        return {"statusCode": 400, "body": "Missing 'content' in request."}

    # AWS agent config
    region = 'us-west-2'
    bucket_name = 'hackaithon-knowledge-base-us-west-2'
    knowledge_base_id = 'CKXZIGUZF8'

    client = AWSAgent(
        region_name=region,
        bucket_name=bucket_name,
        knowledge_base_id=knowledge_base_id
    )

    if file_name == "application_inventory.json":
        response_body = client.save_application_inventory(content)
    else:
        # Save portfolio to s3
        response_body = client.save_portfolio(content)

    # Sync data source in knowledge base
    response_body = client.sync_knowledge_base()

    action_response = {
        'actionGroup': action_group,
        'function': function,
        'functionResponse': {
            'responseBody': response_body
        }
    }
    response = {
        'response': action_response,
        'messageVersion': message_version
    }

    return response