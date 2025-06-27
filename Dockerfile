# Multi-stage Dockerfile for AWS Agent Chatbot
# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Create non-root user for security
RUN groupadd -r streamlit && useradd -r -g streamlit streamlit

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY main.py .
COPY requirements.txt .
COPY src/ ./src/

# Create necessary directories
RUN mkdir -p .streamlit && \
    mkdir -p logs && \
    chown -R streamlit:streamlit /app

# Copy Streamlit configuration
COPY .streamlit/ .streamlit/

# Create .env file template
RUN echo "# AWS Configuration\n\
AWS_ACCESS_KEY_ID=your_access_key\n\
AWS_SECRET_ACCESS_KEY=your_secret_key\n\
AWS_DEFAULT_REGION=us-east-1\n\
\n\
# Application Configuration\n\
S3_BUCKET=your-knowledge-base-bucket\n\
KNOWLEDGE_BASE_ID=your-knowledge-base-id\n\
AGENT_ID=your-agent-id\n\
AGENT_ALIAS_ID=your-agent-alias-id\n\
\n\
# Optional: Advanced Settings\n\
LOG_LEVEL=INFO\n\
MAX_FILE_SIZE=52428800\n\
SUPPORTED_FORMATS=pdf,txt,docx,csv,json,md" > .env.template

# Set proper permissions
RUN chown -R streamlit:streamlit /app && \
    chmod +x /app/main.py

# Switch to non-root user
USER streamlit

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default command
CMD ["streamlit", "run", "main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true", \
     "--server.enableStaticServing=true", \
     "--browser.gatherUsageStats=false"]

# Labels for better maintainability
LABEL maintainer="AWS Agent Chatbot Team" \
      version="1.0.0" \
      description="AWS Agent Chatbot with file upload capabilities" \
      org.opencontainers.image.title="AWS Agent Chatbot" \
      org.opencontainers.image.description="Intelligent Document Analysis Chatbot powered by AWS Bedrock Agents" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/your-username/aws-agent-chatbot" 