import streamlit as st
import boto3
from datetime import datetime
from typing import List, Dict, Any
from botocore.exceptions import ClientError
import mimetypes
import os
from utils import sanitize_filename


class AWSAgentChatbot:
    def __init__(self, region_name: str = 'us-west-2', aws_access_key_id: str = None, 
                 aws_secret_access_key: str = None):
        """Initialize AWS clients and configuration"""
        self.setup_aws_clients(region_name, aws_access_key_id, aws_secret_access_key)
        self.setup_configuration()
    
    def setup_aws_clients(self, region_name: str = 'us-west-2', aws_access_key_id: str = None, 
                          aws_secret_access_key: str = None):
        """Initialize AWS service clients"""
        try:
            # Configure boto3 with longer timeouts for slow agents
            from botocore.config import Config
            
            config = Config(
                region_name=region_name,
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
            self.bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', config=config)
            self.region_name = region_name
            
        except Exception as e:
            st.error(f"Failed to initialize AWS clients: {str(e)}")
            st.stop()
    
    def setup_configuration(self):
        """Setup configuration from environment variables or Streamlit secrets"""
        try:
            # Try to get from Streamlit secrets first, then environment variables
            self.s3_bucket = st.secrets.get("S3_BUCKET", os.getenv("S3_BUCKET", ""))
            self.s3_bucket_folder = st.secrets.get("S3_BUCKET_FOLDER", os.getenv("S3_BUCKET_FOLDER", ""))
            self.knowledge_base_id = st.secrets.get("KNOWLEDGE_BASE_ID", os.getenv("KNOWLEDGE_BASE_ID", ""))
            self.agent_id = st.secrets.get("AGENT_ID", os.getenv("AGENT_ID", ""))
            self.agent_alias_id = st.secrets.get("AGENT_ALIAS_ID", os.getenv("AGENT_ALIAS_ID", "TSTALIASID"))
            
            if not all([self.s3_bucket, self.knowledge_base_id, self.agent_id]):
                st.warning("Please configure your AWS resources in the sidebar")
                
        except Exception as e:
            st.error(f"Configuration error: {str(e)}")
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents"""
        try:
            response = self.bedrock_agent_client.list_agents()
            agents = response.get('agentSummaries', [])
            return agents
        except Exception as e:
            st.error(f"Error listing agents: {str(e)}")
            return []
        
    def get_agent_details(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific agent"""
        try:
            response = self.bedrock_agent_client.get_agent(agentId=agent_id)
            return response.get('agent', {})
        except Exception as e:
            st.error(f"Error getting agent details: {str(e)}")
            return {}
        
    def list_agent_aliases(self, agent_id: str) -> List[Dict[str, Any]]:
        """List aliases for a specific agent"""
        try:
            response = self.bedrock_agent_client.list_agent_aliases(agentId=agent_id)
            return response.get('agentAliasSummaries', [])
        except Exception as e:
            st.error(f"Error listing agent aliases: {str(e)}")
            return []

    def upload_multiple_files_to_s3(self, files_list: List) -> Dict[str, Dict]:
        """Upload multiple files to S3 bucket in specified folder"""
        results = {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_files = len(files_list)
        
        for i, file_obj in enumerate(files_list):
            try:
                # Update progress
                progress = (i + 1) / total_files
                progress_bar.progress(progress)
                status_text.text(f"Uploading {file_obj.name} ({i + 1}/{total_files})")
                
                # Generate unique filename with folder structure
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                sanitized_filename = sanitize_filename(file_obj.name)
                unique_filename = f"{self.s3_bucket_folder}/{timestamp}_{sanitized_filename}"
                
                # Upload file
                self.s3_client.upload_fileobj(
                    file_obj, 
                    self.s3_bucket, 
                    unique_filename,
                    ExtraArgs={
                        'ContentType': mimetypes.guess_type(file_obj.name)[0] or 'application/octet-stream',
                        'Metadata': {
                            'original_filename': file_obj.name,
                            'upload_timestamp': timestamp,
                            'folder': self.s3_bucket_folder,
                            'file_size': str(file_obj.size) if hasattr(file_obj, 'size') else 'unknown'
                        }
                    }
                )
                
                results[file_obj.name] = {
                    'status': 'success',
                    'uploaded_name': unique_filename,
                    'message': f"Uploaded successfully as {unique_filename}"
                }
                
            except ClientError as e:
                results[file_obj.name] = {
                    'status': 'error',
                    'uploaded_name': None,
                    'message': f"Failed to upload: {str(e)}"
                }
            except Exception as e:
                results[file_obj.name] = {
                    'status': 'error',
                    'uploaded_name': None,
                    'message': f"Unexpected error: {str(e)}"
                }
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Display results summary
        successful_uploads = sum(1 for r in results.values() if r['status'] == 'success')
        failed_uploads = total_files - successful_uploads
        
        if successful_uploads > 0:
            st.success(f"✅ Successfully uploaded {successful_uploads} file(s)")
        if failed_uploads > 0:
            st.error(f"❌ Failed to upload {failed_uploads} file(s)")
        
        return results
    
    def sync_knowledge_base(self):
        """Trigger knowledge base synchronization"""
        try:
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.get_data_source_id()
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            st.info(f"🔄 Knowledge base sync started. Job ID: {job_id}")

            return job_id
            
        except ClientError as e:
            st.error(f"❌ Failed to sync knowledge base: {str(e)}")
            return None
    
    def get_data_source_id(self):
        """Get the first data source ID for the knowledge base"""
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.knowledge_base_id
            )
            
            if response['dataSourceSummaries']:
                return response['dataSourceSummaries'][0]['dataSourceId']
            else:
                st.error("No data sources found for knowledge base")
                return None
                
        except ClientError as e:
            st.error(f"Failed to get data source: {str(e)}")
            return None
    
    def query_knowledge_base(self, query: str, max_results: int = 5) -> List[Dict]:
        """Query the knowledge base directly"""
        try:
            response = self.bedrock_agent_runtime_client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results
                    }
                }
            )
            
            return response.get('retrievalResults', [])
            
        except ClientError as e:
            st.error(f"Failed to query knowledge base: {str(e)}")
            return []
    
    def invoke_agent(self, agent_id: str, agent_alias_id: str, user_input: str, session_id: str) -> str:
        """Invoke the Bedrock agent"""
        try:
            response = self.bedrock_agent_runtime_client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=user_input
            )
            
            # Process the response stream
            full_response = ""
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        full_response += chunk['bytes'].decode('utf-8')
            
            return full_response
            
        except ClientError as e:
            st.error(f"Failed to invoke agent: {str(e)}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def list_s3_files(self, folder_prefix: str = "") -> List[Dict]:
        """List files in S3 bucket with optional folder filtering"""
        try:
            params = {'Bucket': self.s3_bucket}
            if folder_prefix:
                params['Prefix'] = folder_prefix
            
            response = self.s3_client.list_objects_v2(**params)
            files = []
            
            for obj in response.get('Contents', []):
                # Skip folder markers (objects ending with /)
                if not obj['Key'].endswith('/'):
                    files.append({
                        'name': obj['Key'],
                        'size': obj['Size'],
                        'modified': obj['LastModified'],
                        'folder': '/'.join(obj['Key'].split('/')[:-1]) if '/' in obj['Key'] else 'root'
                    })
            
            return files
            
        except ClientError as e:
            st.error(f"Failed to list S3 files: {str(e)}")
            return []

    def delete_file_from_s3(self, file_key: str) -> bool:
        """Delete file from S3 bucket"""
        try:
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=file_key)
            return True
        except ClientError as e:
            return False
