import json
import boto3
import datetime
from botocore.exceptions import ClientError
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class AWSAgent:
    def __init__(self, region_name: str = 'us-west-2', 
                 bucket_name: str = 'hackaithon-knowledge-base-us-west-2', 
                 knowledge_base_id: str = 'CKXZIGUZF8'):
        """Initialize AWS clients"""
        self.region_name = region_name
        self.bucket_name = bucket_name
        self.knowledge_base_id = knowledge_base_id
        self.setup_aws_clients()
        self.timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")

    def setup_aws_clients(self):
        """Initialize AWS service clients"""
        try:
            # Configure boto3 with longer timeouts for slow agents
            from botocore.config import Config
            
            config = Config(
                region_name=self.region_name,
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                },
                read_timeout=300,  # 5 minutes read timeout
                connect_timeout=60,  # 1 minute connect timeout
                max_pool_connections=50
            )
            # Initialize AWS clients
            self.s3_client = boto3.client('s3')
            self.bedrock_agent_client = boto3.client('bedrock-agent', config=config)
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            return {"statusCode": 500, "body": f"Setup failed: {str(e)}"}

    def save_portfolio(self, content: str):
        """Save complete portfolio to S3 bucket in specified folder"""
        try:
            key = f"save_data/{self.timestamp}_portfolio.md"
            body = content
            content_type = "text/markdown"

            logger.info(f"Uploading file to S3 bucket '{self.bucket_name}' with key '{key}'")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body.encode("utf-8"),
                ContentType=content_type
            )
            logger.info("✅ Upload successful.")

            response_body = {
                'TEXT': {
                    'body': json.dumps({
                        "message": "File uploaded successfully.",
                        "s3_key": key
                    })
                }
            }

            return response_body
        
        except Exception as e:
            logger.error("Error uploading to S3: %s", str(e), exc_info=True)
            return {"statusCode": 500, "body": f"Upload failed: {str(e)}"}

    def save_application_inventory(self, content: str):
        """Save complete portfolio to S3 bucket in specified folder"""
        try:
            key = f"save_data/{self.timestamp}_application_inventory.json"
            body = json.loads(content)
            content_type = "application/json"

            logger.info(f"Uploading file to S3 bucket '{self.bucket_name}' with key '{key}'")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(body, indent=2),
                ContentType=content_type
            )
            logger.info("✅ Upload successful.")

            response_body = {
                'TEXT': {
                    'body': json.dumps({
                        "message": "File uploaded successfully.",
                        "s3_key": key
                    })
                }
            }

            return response_body
        
        except Exception as e:
            logger.error("Error uploading to S3: %s", str(e), exc_info=True)
            return {"statusCode": 500, "body": f"Upload failed: {str(e)}"}

    def sync_knowledge_base(self):
        """Trigger knowledge base synchronization"""
        try:
            logger.info(f"Syncing file to knowledge base '{self.knowledge_base_id}'")
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.get_data_source_id()
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"🔄 Knowledge base sync started. Job ID: {job_id}")

            response_body = {
                'TEXT': {
                    'body': json.dumps({
                        "message": "File synced successfully.",
                        "ingestion_Job_Id": job_id
                    })
                }
            }

            return response_body
            
        except ClientError as e:
            logger.error(f"❌ Failed to sync knowledge base: {str(e)}")
            return {"statusCode": 500, "body": f"Failed to sync knowledge base: {str(e)}"}
    
    def get_data_source_id(self):
        """Get the first data source ID for the knowledge base"""
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.knowledge_base_id
            )
            
            if response['dataSourceSummaries']:
                return response['dataSourceSummaries'][0]['dataSourceId']
            else:
                logger.error("No data sources found for knowledge base")
                return None
                
        except ClientError as e:
            logger.error(f"Failed to get data source: {str(e)}")
            return {"statusCode": 500, "body": f"Failed to get data source: {str(e)}"}