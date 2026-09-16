"""
Input Validation and Sanitization for SashaInfinity LMS
Provides comprehensive input validation to prevent XSS, SQL injection, and other attacks
"""

import re
import html
import bleach
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator, EmailStr
from fastapi import HTTPException, status
from app.core.security_middleware import log_security_event, security_logger
import urllib.parse

class InputValidator:
    """Comprehensive input validation and sanitization"""

    # XSS patterns to detect and remove
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # onclick=, onload=, etc.
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<form[^>]*>',
        r'<input[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'<style[^>]*>.*?</style>',
        r'<\s*script',
        r'<\s*/\s*script\s*>',
        r'vbscript:',
        r'data:',
        r'&lt;script',
        r'&gt;script',
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bCREATE\b.*\bTABLE\b)",
        r"(\bALTER\b.*\bTABLE\b)",
        r"(--)",
        r"(/\*.*\*/)",
        r"(\bOR\b.*\b1\s*=\s*1\b)",
        r"(\bAND\b.*\b1\s*=\s*1\b)",
        r"(\bEXEC\b.*\bXP_\b)",
        r"(\bEXECUTE\b.*\bXP_\b)",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r';',
        r'&&',
        r'\|\|',
        r'\|',
        r'`',
        r'\$\(.*\)',
        r'<\?.*\?>',
        r'<<',
        r'>>',
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',
        r'%2e%2e%2f',
        r'%2e%2e\\',
        r'..\%5c',
        r'%2e%2e%5c',
        r'\.\.\\',
        r'etc/passwd',
        r'proc/version',
        r'windows/system32',
    ]

    @staticmethod
    def sanitize_html(content: str, allowed_tags: List[str] = None) -> str:
        """Sanitize HTML content using bleach"""
        if allowed_tags is None:
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']

        # First, detect if there are potentially malicious scripts
        for pattern in InputValidator.XSS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                security_logger.warning(f"XSS pattern detected: {pattern}")
                log_security_event(
                    "XSS_ATTEMPT",
                    details={"pattern": pattern, "content_preview": content[:100]}
                )
                break

        # Sanitize using bleach
        clean_content = bleach.clean(
            content,
            tags=allowed_tags,
            attributes={
                'a': ['href', 'title'],
                'img': ['src', 'alt', 'width', 'height'],
                '*': ['class']
            },
            strip=True
        )

        return clean_content

    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitize plain text input"""
        if not text:
            return ""

        # Limit length
        text = text[:max_length]

        # Remove HTML entities and decode
        text = html.unescape(text)

        # Remove null bytes and control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

        # URL encode for safety
        text = urllib.parse.quote(text)

        return text.strip()

    @staticmethod
    def detect_sql_injection(input_string: str) -> bool:
        """Detect SQL injection patterns"""
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE | re.MULTILINE):
                security_logger.warning(f"SQL injection pattern detected: {pattern}")
                log_security_event(
                    "SQL_INJECTION_ATTEMPT",
                    details={"pattern": pattern, "input_preview": input_string[:100]}
                )
                return True
        return False

    @staticmethod
    def detect_command_injection(input_string: str) -> bool:
        """Detect command injection patterns"""
        for pattern in InputValidator.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_string):
                security_logger.warning(f"Command injection pattern detected: {pattern}")
                log_security_event(
                    "COMMAND_INJECTION_ATTEMPT",
                    details={"pattern": pattern, "input_preview": input_string[:100]}
                )
                return True
        return False

    @staticmethod
    def detect_path_traversal(input_string: str) -> bool:
        """Detect path traversal patterns"""
        for pattern in InputValidator.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE):
                security_logger.warning(f"Path traversal pattern detected: {pattern}")
                log_security_event(
                    "PATH_TRAVERSAL_ATTEMPT",
                    details={"pattern": pattern, "input_preview": input_string[:100]}
                )
                return True
        return False

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format and check for suspicious patterns"""
        if not email or len(email) > 254:
            return False

        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False

        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'@.*@',  # Multiple @ symbols
            r'\.\./',  # Path traversal
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                security_logger.warning(f"Suspicious email pattern: {email}")
                return False

        return True

    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        if not phone:
            return True  # Phone is optional

        # Remove common formatting
        clean_phone = re.sub(r'[^\d+]', '', phone)

        # Check reasonable length (5-20 digits)
        if len(clean_phone) < 5 or len(clean_phone) > 20:
            return False

        # Check for valid phone number patterns
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        return re.match(phone_pattern, clean_phone) is not None

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format and check for suspicious patterns"""
        if not url:
            return True  # URL is optional

        # Basic URL validation
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url):
            return False

        # Check for suspicious patterns
        suspicious_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'<script',
            r'file://',
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                security_logger.warning(f"Suspicious URL pattern: {url}")
                return False

        return True

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal and injection"""
        if not filename:
            return "unknown_file"

        # Remove directory separators
        filename = filename.replace("..", "").replace("/", "").replace("\\", "")

        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]

        # Remove dangerous characters
        filename = re.sub(r'[<>"|:]', '', filename)

        return filename.strip()

class SecureBaseModel(BaseModel):
    """Base model with built-in security validation"""

    class Config:
        # Validate on assignment
        validate_assignment = True

        # Use enum values
        use_enum_values = True

        # Extra fields are forbidden
        extra = "forbid"

        # Minimize JSON output
        json_encoders = {
            # Add any custom encoders if needed
        }

class UserProfileValidator(SecureBaseModel):
    """Secure user profile validation"""

    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None

    @validator('first_name')
    def validate_first_name(cls, v):
        v = InputValidator.sanitize_text(v, max_length=50)
        if not v or len(v) < 2:
            raise ValueError("First name must be at least 2 characters")
        return v

    @validator('last_name')
    def validate_last_name(cls, v):
        v = InputValidator.sanitize_text(v, max_length=50)
        if not v or len(v) < 2:
            raise ValueError("Last name must be at least 2 characters")
        return v

    @validator('phone')
    def validate_phone(cls, v):
        if v and not InputValidator.validate_phone_number(v):
            raise ValueError("Invalid phone number format")
        return v

    @validator('bio')
    def validate_bio(cls, v):
        if v:
            v = InputValidator.sanitize_html(v, allowed_tags=['p', 'br', 'strong', 'em'])
            if len(v) > 500:
                raise ValueError("Bio must be less than 500 characters")
        return v

    @validator('website')
    def validate_website(cls, v):
        if v and not InputValidator.validate_url(v):
            raise ValueError("Invalid website URL")
        return v

class CourseContentValidator(SecureBaseModel):
    """Secure course content validation"""

    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    prerequisites: Optional[str] = None

    @validator('title')
    def validate_title(cls, v):
        v = InputValidator.sanitize_text(v, max_length=200)
        if not v or len(v) < 3:
            raise ValueError("Title must be at least 3 characters")
        return v

    @validator('description')
    def validate_description(cls, v):
        if v:
            v = InputValidator.sanitize_html(v, allowed_tags=['p', 'br', 'strong', 'em', 'ul', 'ol', 'li'])
            if len(v) > 1000:
                raise ValueError("Description must be less than 1000 characters")
        return v

    @validator('content')
    def validate_content(cls, v):
        if v:
            v = InputValidator.sanitize_html(v, allowed_tags=[
                'p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'blockquote', 'code', 'pre'
            ])
            if len(v) > 50000:  # 50KB limit
                raise ValueError("Content is too large")
        return v

class SearchQueryValidator(SecureBaseModel):
    """Secure search query validation"""

    query: str
    limit: int = 10
    offset: int = 0

    @validator('query')
    def validate_query(cls, v):
        # Sanitize search query
        v = InputValidator.sanitize_text(v, max_length=100)

        # Check for injection attempts
        if InputValidator.detect_sql_injection(v):
            raise ValueError("Invalid search query")
        if InputValidator.detect_command_injection(v):
            raise ValueError("Invalid search query")

        return v

    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Limit must be between 1 and 100")
        return v

    @validator('offset')
    def validate_offset(cls, v):
        if v < 0 or v > 1000:
            raise ValueError("Offset must be between 0 and 1000")
        return v

def validate_api_input(data: Any, validator_class: type) -> Any:
    """Generic API input validation"""
    try:
        if isinstance(data, dict):
            return validator_class(**data)
        elif isinstance(data, list):
            return [validator_class(**item) for item in data]
        else:
            return validator_class.parse_obj(data)
    except Exception as e:
        security_logger.warning(f"Input validation failed: {str(e)}")
        log_security_event(
            "INPUT_VALIDATION_FAILED",
            details={"error": str(e), "data_type": type(data).__name__}
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid input: {str(e)}"
        )

# Security decorators
def secure_input(validator_class: type):
    """Decorator for secure input validation"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Find request data in kwargs and validate
            for key, value in kwargs.items():
                if key.endswith('_data') and isinstance(value, dict):
                    kwargs[key] = validate_api_input(value, validator_class)

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def sanitize_response(response_data: Any) -> Any:
    """Sanitize API response data"""
    if isinstance(response_data, str):
        return InputValidator.sanitize_text(response_data)
    elif isinstance(response_data, dict):
        return {k: sanitize_response(v) for k, v in response_data.items()}
    elif isinstance(response_data, list):
        return [sanitize_response(item) for item in response_data]
    else:
        return response_data

# Global XSS filter middleware
def filter_xss(data: Any) -> Any:
    """Filter XSS from data recursively"""
    if isinstance(data, str):
        for pattern in InputValidator.XSS_PATTERNS:
            data = re.sub(pattern, '', data, flags=re.IGNORECASE | re.DOTALL)
        return html.escape(data)
    elif isinstance(data, dict):
        return {k: filter_xss(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [filter_xss(item) for item in data]
    else:
        return data