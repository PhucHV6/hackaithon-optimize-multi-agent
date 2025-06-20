# AWS Agent Chatbot Setup Guide

This guide will help you set up and deploy the AWS Agent Chatbot with file upload capabilities.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Python 3.8+** installed
3. **AWS CLI** configured with credentials
4. **Streamlit** familiarity (helpful but not required)

## AWS Resources Setup

### 1. Create S3 Bucket for File Storage

```bash
# Create S3 bucket (replace with your unique bucket name)
aws s3 mb s3://your-knowledge-base-bucket --region us-east-1

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
    --bucket your-knowledge-base-bucket \
    --versioning-configuration Status=Enabled
```

### 2. Create Bedrock Knowledge Base

```bash
# Create a knowledge base using AWS CLI
aws bedrock-agent create-knowledge-base \
    --name "ChatbotKnowledgeBase" \
    --description "Knowledge base for chatbot document analysis" \
    --role-arn "arn:aws:iam::YOUR_ACCOUNT:role/BedrockKnowledgeBaseRole" \
    --knowledge-base-configuration '{
        "type": "VECTOR",
        "vectorKnowledgeBaseConfiguration": {
            "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        }
    }' \
    --storage-configuration '{
        "type": "OPENSEARCH_SERVERLESS",
        "opensearchServerlessConfiguration": {
            "collectionArn": "arn:aws:aoss:us-east-1:YOUR_ACCOUNT:collection/your-collection-id",
            "vectorIndexName": "bedrock-knowledge-base-index",
            "fieldMapping": {
                "vectorField": "bedrock-knowledge-base-default-vector",
                "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
                "metadataField": "AMAZON_BEDROCK_METADATA"
            }
        }
    }'
```

### 3. Create Data Source for Knowledge Base

```bash
# Create data source pointing to your S3 bucket
aws bedrock-agent create-data-source \
    --knowledge-base-id "YOUR_KNOWLEDGE_BASE_ID" \
    --name "S3DataSource" \
    --description "S3 data source for document uploads" \
    --data-source-configuration '{
        "type": "S3",
        "s3Configuration": {
            "bucketArn": "arn:aws:s3:::your-knowledge-base-bucket",
            "inclusionPrefixes": ["documents/"]
        }
    }'
```

### 4. Create Bedrock Agent

```bash
# Create the Bedrock agent
aws bedrock-agent create-agent \
    --agent-name "DocumentChatbot" \
    --description "AI agent for document analysis and chat" \
    --foundation-model "anthropic.claude-3-sonnet-20240229-v1:0" \
    --instruction "You are a helpful AI assistant that can analyze documents and answer questions based on uploaded files. Always be thorough and cite your sources when referencing document content." \
    --idle-session-ttl-in-seconds 1800
```

### 5. Associate Knowledge Base with Agent

```bash
# Associate knowledge base with agent
aws bedrock-agent associate-agent-knowledge-base \
    --agent-id "YOUR_AGENT_ID" \
    --agent-version "DRAFT" \
    --knowledge-base-id "YOUR_KNOWLEDGE_BASE_ID" \
    --description "Knowledge base for document analysis" \
    --knowledge-base-state "ENABLED"
```

### 6. Create Agent Alias

```bash
# Prepare and create agent alias
aws bedrock-agent prepare-agent \
    --agent-id "YOUR_AGENT_ID"

aws bedrock-agent create-agent-alias \
    --agent-id "YOUR_AGENT_ID" \
    --alias-name "ChatbotAlias" \
    --agent-version "1"
```

## IAM Roles and Policies

### 1. Bedrock Knowledge Base Role

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-knowledge-base-bucket",
                "arn:aws:s3:::your-knowledge-base-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1"
        },
        {
            "Effect": "Allow",
            "Action": [
                "aoss:APIAccessAll"
            ],
            "Resource": "arn:aws:aoss:*:*:collection/*"
        }
    ]
}
```

### 2. Application User Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-knowledge-base-bucket",
                "arn:aws:s3:::your-knowledge-base-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agent:InvokeAgent",
                "bedrock-agent-runtime:InvokeAgent",
                "bedrock-agent-runtime:Retrieve"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agent:StartIngestionJob",
                "bedrock-agent:GetIngestionJob",
                "bedrock-agent:ListDataSources"
            ],
            "Resource": "*"
        }
    ]
}
```

## Local Development Setup

### 1. Clone and Setup Project

```bash
# Create project directory
mkdir aws-agent-chatbot
cd aws-agent-chatbot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create `.env` file:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=your-knowledge-base-bucket
KNOWLEDGE_BASE_ID=your-knowledge-base-id
AGENT_ID=your-agent-id
AGENT_ALIAS_ID=your-agent-alias-id
```

### 3. Configure Streamlit Secrets

Create `.streamlit/secrets.toml`:

```toml
[default]
S3_BUCKET = "your-knowledge-base-bucket"
KNOWLEDGE_BASE_ID = "your-knowledge-base-id"
AGENT_ID = "your-agent-id"
AGENT_ALIAS_ID = "your-agent-alias-id"
AWS_ACCESS_KEY_ID = "your_access_key"
AWS_SECRET_ACCESS_KEY = "your_secret_key"
AWS_DEFAULT_REGION = "us-east-1"
```

### 4. Run the Application

```bash
# Run Streamlit app
streamlit run main.py

# The app will be available at http://localhost:8501
```

## Deployment Options

### 1. Streamlit Cloud Deployment

1. Push code to GitHub repository
2. Connect to Streamlit Cloud
3. Add secrets in Streamlit Cloud dashboard
4. Deploy with one click

### 2. AWS EC2 Deployment

```bash
# Install dependencies on EC2
sudo yum update -y
sudo yum install python3 python3-pip -y

# Clone repository
git clone your-repo-url
cd aws-agent-chatbot

# Install dependencies
pip3 install -r requirements.txt

# Run with nohup for background execution
nohup streamlit run main.py --server.port 8501 --server.address 0.0.0.0 &
```

### 3. Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
# Build and run Docker container
docker build -t aws-agent-chatbot .
docker run -p 8501:8501 --env-file .env aws-agent-chatbot
```

## Usage Instructions

### 1. Configure Resources
- Enter your AWS resource IDs in the sidebar
- Click "Update Configuration" to save

### 2. Upload Documents
- Use the file uploader in the sidebar
- Supported formats: PDF, TXT, DOCX, CSV, JSON, MD
- Click "Upload File" to store in S3
- Click "Sync Knowledge Base" to process documents

### 3. Chat with Agent
- Use the main chat interface to ask questions
- The agent can reference uploaded documents
- Each conversation maintains context within the session

### 4. Direct Knowledge Base Query
- Use the search section to query documents directly
- Adjust max results for more/fewer matches
- View relevance scores and metadata

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Verify AWS credentials are correctly configured
   - Check IAM permissions for your user/role

2. **Knowledge Base Sync Issues**
   - Ensure data source is properly configured
   - Check S3 bucket permissions
   - Verify file formats are supported

3. **Agent Not Responding**
   - Check agent ID and alias ID are correct
   - Verify agent is in "Available" state
   - Check agent has knowledge base associated

### Debugging Tips

1. **Enable Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check AWS Service Status**
   - Visit AWS Service Health Dashboard
   - Check region-specific issues

3. **Monitor Costs**
   - Set up billing alerts
   - Monitor Bedrock usage in AWS console

## Cost Optimization

1. **S3 Storage**
   - Use S3 Intelligent Tiering for automatic cost optimization
   - Set lifecycle policies to move old files to cheaper storage classes
   - Delete unnecessary files regularly

2. **Bedrock Usage**
   - Monitor token usage in CloudWatch
   - Use shorter context when possible
   - Implement session timeouts to prevent long-running conversations

3. **OpenSearch Serverless**
   - Monitor OCU (OpenSearch Compute Units) usage
   - Optimize vector index configuration
   - Consider scheduled scaling for predictable workloads

## Monitoring and Logging

### CloudWatch Metrics Setup

```python
# Add to your application for custom metrics
import boto3

cloudwatch = boto3.client('cloudwatch')

def log_custom_metric(metric_name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='ChatbotApp',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
        ]
    )

# Usage examples
log_custom_metric('FilesUploaded', 1)
log_custom_metric('ChatSessions', 1)
log_custom_metric('KnowledgeBaseQueries', 1)
```

### Application Logging

```python
# Enhanced logging configuration
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        return json.dumps(log_entry)

# Setup structured logging
logger = logging.getLogger('chatbot')
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

## Security Best Practices

### 1. AWS Security

- **Use IAM roles instead of access keys when possible**
- **Enable MFA for AWS console access**
- **Regularly rotate access keys**
- **Use least privilege principle for IAM policies**
- **Enable CloudTrail for audit logging**

### 2. Application Security

```python
# Input validation example
import re
from typing import Optional

def validate_user_input(user_input: str) -> Optional[str]:
    """Validate and sanitize user input"""
    if not user_input or len(user_input.strip()) == 0:
        return None
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', user_input)
    
    # Limit input length
    if len(sanitized) > 5000:
        sanitized = sanitized[:5000]
    
    return sanitized.strip()

# File upload validation
def validate_uploaded_file(file_obj) -> tuple[bool, str]:
    """Validate uploaded file for security"""
    if file_obj.size > 50 * 1024 * 1024:  # 50MB limit
        return False, "File too large"
    
    allowed_types = ['.pdf', '.txt', '.docx', '.csv', '.json', '.md']
    file_ext = os.path.splitext(file_obj.name)[1].lower()
    
    if file_ext not in allowed_types:
        return False, "File type not allowed"
    
    return True, "Valid file"
```

### 3. Data Privacy

```python
# PII Detection and Masking
import re

def mask_pii(text: str) -> str:
    """Mask common PII patterns in text"""
    # Mask email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                  '[EMAIL]', text)
    
    # Mask phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    
    # Mask SSN patterns
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    
    return text
```

## Advanced Features

### 1. Batch File Processing

```python
# batch_processor.py
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor

class BatchFileProcessor:
    def __init__(self, chatbot_instance):
        self.chatbot = chatbot_instance
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def process_multiple_files(self, file_paths: list) -> dict:
        """Process multiple files concurrently"""
        results = {}
        
        async def process_single_file(file_path):
            try:
                with open(file_path, 'rb') as f:
                    success, filename = self.chatbot.upload_file_to_s3(f, file_path)
                    return file_path, success, filename
            except Exception as e:
                return file_path, False, str(e)
        
        tasks = [process_single_file(fp) for fp in file_paths]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for file_path, success, result in completed:
            results[file_path] = {'success': success, 'result': result}
        
        return results
```

### 2. Custom Agent Actions

```python
# custom_actions.py
class CustomAgentActions:
    def __init__(self, chatbot_instance):
        self.chatbot = chatbot_instance
    
    def summarize_document(self, document_key: str) -> str:
        """Custom action to summarize a specific document"""
        try:
            # Get document from S3
            response = self.chatbot.s3_client.get_object(
                Bucket=self.chatbot.s3_bucket,
                Key=document_key
            )
            
            content = response['Body'].read().decode('utf-8')[:4000]  # Limit content
            
            # Use Bedrock to summarize
            prompt = f"Please provide a concise summary of this document:\n\n{content}"
            
            response = self.chatbot.bedrock_client.invoke_model(
                modelId='anthropic.claude-3-haiku-20240307-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 500,
                    'messages': [{'role': 'user', 'content': prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            return result['content'][0]['text']
            
        except Exception as e:
            return f"Error summarizing document: {str(e)}"
    
    def extract_key_points(self, query_results: list) -> list:
        """Extract key points from knowledge base query results"""
        key_points = []
        
        for result in query_results:
            text = result['content']['text']
            
            # Simple key point extraction (you can enhance this)
            sentences = text.split('.')
            for sentence in sentences:
                if len(sentence.strip()) > 50:  # Meaningful sentences
                    key_points.append(sentence.strip())
        
        return key_points[:10]  # Return top 10 key points
```

### 3. Analytics Dashboard

```python
# analytics.py
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

class ChatbotAnalytics:
    def __init__(self):
        self.metrics = {}
    
    def track_usage(self, event_type: str, metadata: dict = None):
        """Track usage events"""
        timestamp = datetime.now()
        
        if event_type not in self.metrics:
            self.metrics[event_type] = []
        
        self.metrics[event_type].append({
            'timestamp': timestamp,
            'metadata': metadata or {}
        })
    
    def generate_usage_chart(self):
        """Generate usage analytics chart"""
        if not self.metrics:
            return None
        
        # Count events by type
        event_counts = {k: len(v) for k, v in self.metrics.items()}
        
        fig = px.bar(
            x=list(event_counts.keys()),
            y=list(event_counts.values()),
            title="Chatbot Usage Analytics"
        )
        
        return fig
    
    def get_session_stats(self) -> dict:
        """Get session statistics"""
        total_sessions = len(self.metrics.get('chat_session', []))
        total_uploads = len(self.metrics.get('file_upload', []))
        total_queries = len(self.metrics.get('knowledge_base_query', []))
        
        return {
            'total_sessions': total_sessions,
            'total_uploads': total_uploads,
            'total_queries': total_queries,
            'avg_queries_per_session': total_queries / max(total_sessions, 1)
        }
```

## Production Deployment Checklist

### Pre-Deployment

- [ ] All AWS resources created and configured
- [ ] IAM roles and policies tested
- [ ] Environment variables secured
- [ ] Application tested with sample documents
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Security validations in place

### Deployment

- [ ] Choose deployment method (Streamlit Cloud, EC2, ECS, etc.)
- [ ] Configure production environment variables
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategies
- [ ] Set up CI/CD pipeline (optional)
- [ ] Load testing completed
- [ ] Security scanning completed

### Post-Deployment

- [ ] Monitor application performance
- [ ] Check AWS costs and usage
- [ ] Verify all features working
- [ ] Set up regular backups
- [ ] Document operational procedures
- [ ] Train users on the application

## Scaling Considerations

### Horizontal Scaling

```python
# load_balancer.py
import random
from typing import List

class AgentLoadBalancer:
    def __init__(self, agent_configs: List[dict]):
        self.agents = agent_configs
        self.current_loads = {agent['id']: 0 for agent in agent_configs}
    
    def get_least_loaded_agent(self) -> dict:
        """Get agent with least current load"""
        min_load_agent = min(self.agents, 
                           key=lambda x: self.current_loads[x['id']])
        return min_load_agent
    
    def route_request(self, request_data: dict) -> dict:
        """Route request to best available agent"""
        selected_agent = self.get_least_loaded_agent()
        self.current_loads[selected_agent['id']] += 1
        
        try:
            # Process request with selected agent
            result = self.process_with_agent(selected_agent, request_data)
            return result
        finally:
            self.current_loads[selected_agent['id']] -= 1
```

### Caching Strategy

```python
# cache_manager.py
import json
import hashlib
from typing import Optional, Any
import redis

class ResponseCache:
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.default_ttl = 3600  # 1 hour
    
    def _generate_key(self, query: str, context: dict = None) -> str:
        """Generate cache key from query and context"""
        data = {'query': query, 'context': context or {}}
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.md5(serialized.encode()).hexdigest()
    
    def get(self, query: str, context: dict = None) -> Optional[Any]:
        """Get cached response"""
        key = self._generate_key(query, context)
        cached = self.redis_client.get(key)
        
        if cached:
            return json.loads(cached)
        return None
    
    def set(self, query: str, response: Any, context: dict = None, ttl: int = None):
        """Cache response"""
        key = self._generate_key(query, context)
        ttl = ttl or self.default_ttl
        
        self.redis_client.setex(
            key, 
            ttl, 
            json.dumps(response, default=str)
        )
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**
   - Review application logs for errors
   - Check AWS costs and usage patterns
   - Backup critical configurations

2. **Monthly**
   - Update dependencies
   - Review and rotate access keys
   - Analyze usage patterns for optimization

3. **Quarterly**
   - Security audit and vulnerability assessment
   - Performance optimization review
   - Disaster recovery testing

### Getting Help

- **AWS Support**: Use AWS Support Center for service-specific issues
- **Streamlit Community**: Join Streamlit community forum for UI issues
- **GitHub Issues**: Create issues in your project repository
- **Documentation**: Refer to AWS Bedrock and Streamlit documentation

## Conclusion

This setup provides a complete, production-ready conversational AI chatbot with document analysis capabilities. The modular architecture allows for easy customization and scaling based on your specific requirements.

Key benefits of this implementation:
- **Serverless and scalable** AWS architecture
- **User-friendly** Streamlit interface
- **Secure** file handling and processing
- **Extensible** for additional features
- **Cost-effective** with proper configuration

For additional features or customizations, refer to the AWS Bedrock Agent documentation and Streamlit API reference.