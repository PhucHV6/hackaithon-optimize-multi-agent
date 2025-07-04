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

    def save_file(self, content: str, content_type: str, file_name: str = None):
        """Save file to S3 bucket in specified folder"""
        try:
            # Use the actual file name with timestamp prefix
            if file_name:
                # Extract file extension for proper handling
                if file_name.endswith('.json'):
                    # Parse JSON content for proper formatting
                    body = json.loads(content)
                    body_content = json.dumps(body, indent=2)
                else:
                    # Use content as-is for other file types
                    body_content = content
                
                # Create key using actual file name with timestamp
                key = f"save_data/{self.timestamp}_{file_name}"
            else:
                # Fallback for backward compatibility
                key = f"save_data/{self.timestamp}_file"
                body_content = content

            logger.info(f"Uploading file to S3 bucket '{self.bucket_name}' with key '{key}' and content_type '{content_type}'")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body_content.encode("utf-8"),
                ContentType=content_type
            )
            logger.info("✅ Upload successful.")

            # Generate presigned URL for download (expires in 5 hours)
            try:
                download_url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': key},
                    ExpiresIn=18000  # 5 hours in seconds
                )
                logger.info(f"Generated presigned URL: {download_url[:100]}...")
            except Exception as e:
                logger.error(f"Failed to generate presigned URL: {str(e)}")
                download_url = None

            response_body = {
                'TEXT': {
                    'body': json.dumps({
                        "status": "success",
                        "message": f"✅ File '{file_name or key.split('/')[-1]}' uploaded successfully!",
                        "file_details": {
                            "name": file_name or key.split('/')[-1],
                            "size_bytes": len(body_content.encode("utf-8")),
                            "type": content_type,
                            "location": f"S3: {self.bucket_name}/{key}"
                        },
                        "download_info": {
                            "url": download_url,
                            "instructions": f"Copy and paste this URL in your browser to download: {download_url}" if download_url else f"File saved to S3 bucket '{self.bucket_name}' with key '{key}'. Access via AWS Console or CLI.",
                            "aws_cli_command": f"aws s3 cp s3://{self.bucket_name}/{key} ./{key.split('/')[-1]}"
                        }
                    })
                }
            }

            return response_body
        
        except Exception as e:
            logger.error("Error uploading to S3: %s", str(e), exc_info=True)
            response_body = {
                'TEXT': {
                    'body': json.dumps({
                        "status": "error",
                        "message": f"Upload failed: {str(e)}",
                        "file_details": None,
                        "download_info": None
                    })
                }
            }
            return response_body

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
                        "status": "success",
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