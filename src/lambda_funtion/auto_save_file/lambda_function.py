import json
import logging
from aws_agent import AWSAgent
import mimetypes

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_content_type(file_name):
    # Try to guess the content type based on the file extension
    content_type, _ = mimetypes.guess_type(file_name)
    # Fallbacks for common types
    if file_name.endswith('.md'):
        return 'text/markdown'
    if file_name.endswith('.json'):
        return 'application/json'
    if file_name.endswith('.xml'):
        return 'application/xml'
    return content_type or 'application/octet-stream'

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

    content_type = get_content_type(file_name)

    # Use unified save_file method
    upload_response = client.save_file(content, content_type, file_name)

    # Sync data source in knowledge base
    sync_response = client.sync_knowledge_base()
    
    # Combine responses
    response_body = {
        'TEXT': {
            'body': json.dumps({
                "upload_result": json.loads(upload_response['TEXT']['body']),
                "sync_result": json.loads(sync_response['TEXT']['body'])
            })
        }
    }

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