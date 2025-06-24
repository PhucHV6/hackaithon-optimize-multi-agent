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
                    'max_attempts': 10,
                    'mode': 'adaptive'
                },
                read_timeout=300,  # 5 minutes read timeout
                connect_timeout=60,  # 1 minute connect timeout
                max_pool_connections=50
            )
            
            # Store credentials for later use
            self.aws_access_key_id = aws_access_key_id
            self.aws_secret_access_key = aws_secret_access_key
            
            # Initialize AWS clients with proper credential handling
            if aws_access_key_id and aws_secret_access_key:
                # Use provided credentials
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region_name
                )
                self.bedrock_agent_client = boto3.client(
                    'bedrock-agent',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    config=config
                )
                self.bedrock_agent_runtime_client = boto3.client(
                    'bedrock-agent-runtime',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    config=config
                )
            else:
                # Use default credentials (environment variables, IAM roles, etc.)
                self.s3_client = boto3.client('s3', region_name=region_name)
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
    
    def test_credentials(self) -> Dict[str, Any]:
        """Test AWS credentials and return connection status"""
        try:
            # Test basic AWS access by calling STS with the same credentials
            if self.aws_access_key_id and self.aws_secret_access_key:
                # Use the same credentials as other clients
                sts_client = boto3.client(
                    'sts',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region_name
                )
            else:
                # Use default credentials
                sts_client = boto3.client('sts', region_name=self.region_name)
            
            identity = sts_client.get_caller_identity()
            
            # Test Bedrock Agent access
            agents = self.list_agents()
            
            return {
                'status': 'success',
                'user_arn': identity.get('Arn', 'Unknown'),
                'account_id': identity.get('Account', 'Unknown'),
                'user_id': identity.get('UserId', 'Unknown'),
                'agent_count': len(agents) if agents else 0,
                'region': self.region_name,
                'credential_method': 'manual' if self.aws_access_key_id else 'default'
            }
            
        except Exception as e:
            error_msg = str(e)
            # Provide more specific error information
            if "InvalidClientTokenId" in error_msg:
                error_msg = "Invalid Access Key ID - Please check your credentials"
            elif "SignatureDoesNotMatch" in error_msg:
                error_msg = "Invalid Secret Access Key - Please check your credentials"
            elif "AccessDenied" in error_msg:
                error_msg = "Access Denied - Please check your IAM permissions"
            elif "ExpiredTokenException" in error_msg:
                error_msg = "Credentials have expired - Please refresh your credentials"
            
            return {
                'status': 'error',
                'error': error_msg,
                'region': self.region_name,
                'credential_method': 'manual' if self.aws_access_key_id else 'default'
            }
    
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
    
    def invoke_agent(self, agent_id: str, agent_alias_id: str, user_input: str, session_id: str, conversation_history: List[Dict] = None) -> str:
        """Invoke the Bedrock agent with conversation history"""
        try:
            # Build conversation context
            if conversation_history:
                # Format conversation history for the agent
                context = self._build_conversation_context(conversation_history, user_input)
            else:
                context = user_input
                
            response = self.bedrock_agent_runtime_client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=context
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
    
    def _build_conversation_context(self, conversation_history: List[Dict], current_input: str) -> str:
        """Build conversation context from history"""
        context_parts = []
        
        # Add recent conversation history (last 10 exchanges to avoid token limits)
        recent_history = conversation_history[-10:]  # Last 10 messages
        
        for msg in recent_history:
            # Skip system messages and context messages as they're internal
            if msg.get("role") == "system" or msg.get("is_context", False):
                continue
                
            if msg["role"] == "user":
                context_parts.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                context_parts.append(f"Assistant: {msg['content']}")
        
        # Add current input
        context_parts.append(f"User: {current_input}")
        
        # If we have context, add a separator for clarity
        if len(context_parts) > 1:
            return "\n\n".join(context_parts)
        else:
            return current_input
    
    def get_conversation_summary(self, conversation_history: List[Dict]) -> str:
        """Get a summary of the conversation for context"""
        if not conversation_history:
            return "No previous conversation."
        
        # Count messages by type
        user_messages = [msg for msg in conversation_history if msg.get("role") == "user" and not msg.get("is_context", False)]
        assistant_messages = [msg for msg in conversation_history if msg.get("role") == "assistant"]
        
        summary = f"Conversation has {len(user_messages)} user messages and {len(assistant_messages)} assistant responses."
        
        # Add recent topics if available
        if user_messages:
            recent_topics = [msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content'] 
                           for msg in user_messages[-3:]]  # Last 3 user messages
            summary += f" Recent topics: {', '.join(recent_topics)}"
        
        return summary
    
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

    def debug_connection(self) -> Dict[str, Any]:
        """Debug connection and credential information"""
        debug_info = {
            'region': self.region_name,
            'has_access_key': bool(self.aws_access_key_id),
            'has_secret_key': bool(self.aws_secret_access_key),
            'access_key_prefix': self.aws_access_key_id[:4] + '...' if self.aws_access_key_id else 'None',
            'clients_initialized': {
                's3_client': hasattr(self, 's3_client'),
                'bedrock_agent_client': hasattr(self, 'bedrock_agent_client'),
                'bedrock_agent_runtime_client': hasattr(self, 'bedrock_agent_runtime_client')
            }
        }
        
        # Test each service individually
        try:
            if hasattr(self, 's3_client'):
                # Test S3 access
                self.s3_client.list_buckets()
                debug_info['s3_test'] = 'success'
            else:
                debug_info['s3_test'] = 'client_not_initialized'
        except Exception as e:
            debug_info['s3_test'] = f'error: {str(e)}'
        
        try:
            if hasattr(self, 'bedrock_agent_client'):
                # Test Bedrock Agent access
                self.bedrock_agent_client.list_agents()
                debug_info['bedrock_test'] = 'success'
            else:
                debug_info['bedrock_test'] = 'client_not_initialized'
        except Exception as e:
            debug_info['bedrock_test'] = f'error: {str(e)}'
        
        return debug_info
