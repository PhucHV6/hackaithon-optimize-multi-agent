import re
import json
import uuid
import mimetypes
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Optional

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def get_file_type_icon(filename: str) -> str:
    """Get emoji icon for file type"""
    mime_type, _ = mimetypes.guess_type(filename)
    
    if mime_type:
        if mime_type.startswith('image/'):
            return '🖼️'
        elif mime_type.startswith('video/'):
            return '🎥'
        elif mime_type.startswith('audio/'):
            return '🎵'
        elif 'pdf' in mime_type:
            return '📄'
        elif 'word' in mime_type or 'document' in mime_type:
            return '📝'
        elif 'spreadsheet' in mime_type or 'excel' in mime_type:
            return '📊'
        elif 'presentation' in mime_type or 'powerpoint' in mime_type:
            return '📺'
        elif 'text' in mime_type:
            return '📄'
    
    return '📎'

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """Validate if file type is allowed"""
    file_extension = filename.lower().split('.')[-1]
    return file_extension in [t.lower() for t in allowed_types]

def extract_text_preview(text: str, max_length: int = 200) -> str:
    """Extract preview text with ellipsis if too long"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for S3 storage"""
    import re
    # Remove or replace invalid characters for S3
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove any leading/trailing whitespace and dots
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = f"unnamed_file_{uuid.uuid4().hex[:8]}"
    
    return filename

def display_content_with_formatting(content_str: str):
    """Display content with intelligent formatting"""
    if not content_str or content_str.strip() == "":
        st.info("No content returned")
        return
    
    # Pre-process the content string
    # Replace \n with actual newlines
    content_str = content_str.replace('\\n', '\n')
    # Replace \t with actual tabs
    content_str = content_str.replace('\\t', '\t')
    # Handle other special characters
    content_str = content_str.replace('\\r', '\r')
    
    # Try to parse as JSON first
    try:
        content_json = json.loads(content_str)
        if isinstance(content_json, (dict, list)):
            st.json(content_json)
        else:
            st.markdown(str(content_json))
    except (json.JSONDecodeError, TypeError):
        # If not JSON, check if it looks like structured text
        if any(marker in content_str for marker in ['#', '##', '###', '*', '-', '1.', '\n-', '\n1.']):
            # Clean up markdown formatting
            # Fix numbered lists that might have escaped newlines
            content_str = re.sub(r'\\n(\d+\.)', r'\n\1', content_str)
            # Fix bullet points that might have escaped newlines
            content_str = re.sub(r'\\n-', r'\n-', content_str)
            # Ensure proper spacing for headers
            content_str = re.sub(r'\\n(#+)', r'\n\1 ', content_str)
            # Looks like markdown
            st.markdown(content_str, unsafe_allow_html=False)
        elif content_str.startswith('{') or content_str.startswith('['):
            # Might be malformed JSON, show in code block
            st.code(content_str, language='json')
        else:
            # Plain text with proper newline handling
            st.text(content_str)