# 🤖 AWS Agent Chatbot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![AWS](https://img.shields.io/badge/AWS-Bedrock-orange.svg)](https://aws.amazon.com/bedrock/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Intelligent Document Analysis Chatbot** powered by AWS Bedrock Agents with file upload capabilities, knowledge base integration, and conversational AI.

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [📋 Prerequisites](#-prerequisites)
- [⚙️ Setup Guide](#️-setup-guide)
- [🔧 Configuration](#-configuration)
- [🚀 Deployment](#-deployment)
- [📖 Usage Guide](#-usage-guide)
- [🔍 Troubleshooting](#-troubleshooting)
- [💰 Cost Optimization](#-cost-optimization)
- [🔒 Security](#-security)
- [📊 Monitoring](#-monitoring)
- [🛠️ Advanced Features](#️-advanced-features)
- [📈 Scaling](#-scaling)
- [🤝 Support](#-support)

## 🚀 Quick Start

Get up and running in **5 minutes**:

```bash
# 1. Clone the repository
git clone https://github.com/your-username/aws-agent-chatbot.git
cd aws-agent-chatbot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your AWS credentials

# 4. Run the application
streamlit run main.py
```

**🎯 Next Steps**: Follow the [Complete Setup Guide](#️-setup-guide) to configure AWS resources.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI-Powered Chat** | Conversational AI using AWS Bedrock Agents |
| 📄 **Document Upload** | Support for PDF, TXT, DOCX, CSV, JSON, MD |
| 🔍 **Knowledge Base** | Vector-based document search and retrieval |
| 💬 **Context-Aware** | Maintains conversation context across sessions |
| 🔒 **Secure** | AWS IAM integration and input validation |
| 📊 **Analytics** | Usage tracking and performance monitoring |
| 🚀 **Scalable** | Serverless architecture with auto-scaling |
| 🎨 **Modern UI** | Beautiful Streamlit interface |

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   AWS Bedrock   │    │   S3 Storage    │
│                 │◄──►│     Agent       │◄──►│                 │
│  - File Upload  │    │  - Knowledge    │    │  - Metadata     │
│  - Chat Interface│    │    Base         │    │                 │
│  - Analytics    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ OpenSearch      │
                       │ Serverless      │
                       │                 │
                       │ - Vector Index  │
                       │ - Search Engine │
                       └─────────────────┘
```

## 📋 Prerequisites

### Required
- ✅ **AWS Account** with appropriate permissions
- ✅ **Python 3.8+** installed
- ✅ **AWS CLI** configured with credentials

### Recommended
- 📚 **Streamlit** familiarity (helpful but not required)
- 🔧 **Docker** (for containerized deployment)

## ⚙️ Setup Guide

### Step 1: AWS Resources Setup

#### 1.1 Create S3 Bucket

```bash
# Create S3 bucket for document storage
aws s3 mb s3://your-knowledge-base-bucket --region us-east-1

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
    --bucket your-knowledge-base-bucket \
    --versioning-configuration Status=Enabled
```

#### 1.2 Create OpenSearch Serverless Collection

```bash
# Create OpenSearch Serverless collection
aws opensearchserverless create-collection \
    --name bedrock-knowledge-base \
    --type VECTORSEARCH \
    --description "Vector search collection for knowledge base"
```

#### 1.3 Create Bedrock Knowledge Base

```bash
# Create knowledge base
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
            "collectionArn": "arn:aws:aoss:us-east-1:YOUR_ACCOUNT:collection/bedrock-knowledge-base",
            "vectorIndexName": "bedrock-knowledge-base-index",
            "fieldMapping": {
                "vectorField": "bedrock-knowledge-base-default-vector",
                "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
                "metadataField": "AMAZON_BEDROCK_METADATA"
            }
        }
    }'
```

#### 1.4 Create Data Source

```bash
# Create data source pointing to S3 bucket
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

#### 1.5 Create Bedrock Agent

```bash
# Create the Bedrock agent
aws bedrock-agent create-agent \
    --agent-name "DocumentChatbot" \
    --description "AI agent for document analysis and chat" \
    --foundation-model "anthropic.claude-3-sonnet-20240229-v1:0" \
    --instruction "You are a helpful AI assistant that can analyze documents and answer questions based on uploaded files. Always be thorough and cite your sources when referencing document content." \
    --idle-session-ttl-in-seconds 1800
```

#### 1.6 Associate Knowledge Base with Agent

```bash
# Associate knowledge base with agent
aws bedrock-agent associate-agent-knowledge-base \
    --agent-id "YOUR_AGENT_ID" \
    --agent-version "DRAFT" \
    --knowledge-base-id "YOUR_KNOWLEDGE_BASE_ID" \
    --description "Knowledge base for document analysis" \
    --knowledge-base-state "ENABLED"
```

#### 1.7 Create Agent Alias

```bash
# Prepare and create agent alias
aws bedrock-agent prepare-agent --agent-id "YOUR_AGENT_ID"

aws bedrock-agent create-agent-alias \
    --agent-id "YOUR_AGENT_ID" \
    --alias-name "ChatbotAlias" \
    --agent-version "1"
```

### Step 2: IAM Configuration

#### 2.1 Bedrock Knowledge Base Role

Create IAM role with the following policy:

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

#### 2.2 Application User Policy

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

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Application Configuration
S3_BUCKET=your-knowledge-base-bucket
KNOWLEDGE_BASE_ID=your-knowledge-base-id
AGENT_ID=your-agent-id
AGENT_ALIAS_ID=your-agent-alias-id

# Optional: Advanced Settings
LOG_LEVEL=INFO
MAX_FILE_SIZE=52428800  # 50MB in bytes
SUPPORTED_FORMATS=pdf,txt,docx,csv,json,md
```

### Streamlit Secrets

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

## 🚀 Deployment

### Option 1: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
streamlit run main.py
```

### Option 2: Streamlit Cloud

1. Push code to GitHub repository
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Add secrets in Streamlit Cloud dashboard
4. Deploy with one click

### Option 3: Docker Deployment

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
# Build and run
docker build -t aws-agent-chatbot .
docker run -p 8501:8501 --env-file .env aws-agent-chatbot
```

### Option 4: AWS EC2

```bash
# Install dependencies
sudo yum update -y
sudo yum install python3 python3-pip -y

# Clone and setup
git clone your-repo-url
cd aws-agent-chatbot
pip3 install -r requirements.txt

# Run with nohup
nohup streamlit run main.py --server.port 8501 --server.address 0.0.0.0 &
```

## 📖 Usage Guide

### 1. Configure Resources
- Enter your AWS resource IDs in the sidebar
- Click "Update Configuration" to save settings

### 2. Upload Documents
- Use the file uploader in the sidebar
- **Supported formats**: PDF, TXT, DOCX, CSV, JSON, MD
- Click "Upload File" to store in S3
- Click "Sync Knowledge Base" to process documents

### 3. Chat with Agent
- Use the main chat interface to ask questions
- The agent references uploaded documents
- Each conversation maintains context within the session

### 4. Direct Knowledge Base Query
- Use the search section to query documents directly
- Adjust max results for more/fewer matches
- View relevance scores and metadata

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **AWS Credentials Error** | Verify AWS credentials and IAM permissions |
| **Knowledge Base Sync Issues** | Check data source configuration and S3 permissions |
| **Agent Not Responding** | Verify agent ID, alias ID, and agent status |
| **File Upload Fails** | Check file size limits and supported formats |
| **High Latency** | Monitor Bedrock service status and region selection |

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

```bash
# Check AWS services
aws bedrock-agent list-agents
aws s3 ls s3://your-knowledge-base-bucket
aws opensearchserverless list-collections
```

## 💰 Cost Optimization

### S3 Storage
- Use **S3 Intelligent Tiering** for automatic cost optimization
- Set **lifecycle policies** to move old files to cheaper storage
- **Delete unnecessary files** regularly

### Bedrock Usage
- Monitor **token usage** in CloudWatch
- Use **shorter context** when possible
- Implement **session timeouts** to prevent long-running conversations

### OpenSearch Serverless
- Monitor **OCU (OpenSearch Compute Units)** usage
- Optimize **vector index configuration**
- Consider **scheduled scaling** for predictable workloads

## 🔒 Security

### AWS Security Best Practices
- ✅ Use **IAM roles** instead of access keys when possible
- ✅ Enable **MFA** for AWS console access
- ✅ Regularly **rotate access keys**
- ✅ Use **least privilege principle** for IAM policies
- ✅ Enable **CloudTrail** for audit logging

### Application Security
- ✅ **Input validation** and sanitization
- ✅ **File type validation** and size limits
- ✅ **PII detection** and masking
- ✅ **Rate limiting** for API calls

### Data Privacy
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

## 📊 Monitoring

### CloudWatch Metrics

```python
import boto3
from datetime import datetime

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

## 🛠️ Advanced Features

### Batch File Processing

```python
import asyncio
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

### Custom Agent Actions

```python
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
            
            content = response['Body'].read().decode('utf-8')[:4000]
            
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
```

### Analytics Dashboard

```python
import plotly.express as px
from datetime import datetime

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
        
        event_counts = {k: len(v) for k, v in self.metrics.items()}
        
        fig = px.bar(
            x=list(event_counts.keys()),
            y=list(event_counts.values()),
            title="Chatbot Usage Analytics"
        )
        
        return fig
```

## 📈 Scaling

### Horizontal Scaling

```python
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
            result = self.process_with_agent(selected_agent, request_data)
            return result
        finally:
            self.current_loads[selected_agent['id']] -= 1
```

### Caching Strategy

```python
import json
import hashlib
import redis
from typing import Optional, Any

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

## 🤝 Support

### Getting Help

| Resource | Description |
|----------|-------------|
| 🐛 **GitHub Issues** | Report bugs and request features |
| 📚 **AWS Documentation** | [Bedrock Agents](https://docs.aws.amazon.com/bedrock/) |
| 💬 **Streamlit Community** | [Community Forum](https://discuss.streamlit.io/) |
| 🆘 **AWS Support** | [AWS Support Center](https://aws.amazon.com/support/) |

### Maintenance Schedule

| Frequency | Tasks |
|-----------|-------|
| **Weekly** | Review logs, check costs, backup configs |
| **Monthly** | Update dependencies, rotate keys, analyze usage |
| **Quarterly** | Security audit, performance review, disaster recovery |

### Production Checklist

#### Pre-Deployment
- [ ] All AWS resources created and configured
- [ ] IAM roles and policies tested
- [ ] Environment variables secured
- [ ] Application tested with sample documents
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Security validations in place

#### Deployment
- [ ] Choose deployment method
- [ ] Configure production environment variables
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategies
- [ ] Load testing completed
- [ ] Security scanning completed

#### Post-Deployment
- [ ] Monitor application performance
- [ ] Check AWS costs and usage
- [ ] Verify all features working
- [ ] Set up regular backups
- [ ] Document operational procedures
- [ ] Train users on the application

---

## 🎯 Key Benefits

- **🚀 Serverless and Scalable** AWS architecture
- **🎨 User-Friendly** Streamlit interface
- **🔒 Secure** file handling and processing
- **🔧 Extensible** for additional features
- **💰 Cost-Effective** with proper configuration

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [AWS Bedrock](https://aws.amazon.com/bedrock/) for AI capabilities
- [Streamlit](https://streamlit.io/) for the web interface
- [OpenSearch](https://opensearch.org/) for vector search

---

**⭐ Star this repository if you find it helpful!**