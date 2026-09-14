"""
Secure File Upload Handler for SashaInfinity LMS
Provides comprehensive file security including virus scanning, type validation,
and safe file storage
"""

import os
import hashlib
import magic
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from app.core.config import get_settings
from app.core.security_middleware import (
    sanitize_filename,
    log_security_event,
    security_logger
)
from app.core.database import get_db
from datetime import datetime, timedelta
import re
import uuid

settings = get_settings()

class FileSecurityValidator:
    """Comprehensive file security validation"""

    # File type whitelist with MIME types
    ALLOWED_FILE_TYPES = {
        'jpg': ['image/jpeg'],
        'jpeg': ['image/jpeg'],
        'png': ['image/png'],
        'gif': ['image/gif'],
        'pdf': ['application/pdf'],
        'doc': ['application/msword'],
        'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        'txt': ['text/plain'],
        'mp4': ['video/mp4'],
        'mov': ['video/quicktime'],
    }

    # Suspicious file patterns
    SUSPICIOUS_PATTERNS = [
        r'\.php', r'\.phtml', r'\.php3', r'\.php4', r'\.php5',
        r'\.asp', r'\.aspx', r'\.jsp', r'\.js', r'\.vbs',
        r'\.exe', r'\.bat', r'\.cmd', r'\.com', r'\.scr',
        r'\.sh', r'\.py', r'\.pl', r'\.rb'
    ]

    @staticmethod
    def validate_file_extension(filename: str) -> Tuple[bool, str]:
        """Validate file extension against whitelist"""
        # Sanitize filename first
        filename = sanitize_filename(filename)

        # Get extension
        if '.' not in filename:
            return False, "File must have an extension"

        extension = filename.lower().split('.')[-1]

        # Check against whitelist
        if extension not in settings.ALLOWED_EXTENSIONS:
            return False, f"File type .{extension} is not allowed"

        # Check against suspicious patterns
        for pattern in FileSecurityValidator.SUSPICIOUS_PATTERNS:
            if re.search(pattern, filename.lower()):
                return False, "Suspicious file pattern detected"

        return True, extension

    @staticmethod
    def validate_mime_type(file_content: bytes, extension: str) -> Tuple[bool, str]:
        """Validate file MIME type using python-magic"""
        try:
            # Detect MIME type
            mime_type = magic.from_buffer(file_content, mime=True)

            # Check if MIME type matches expected types
            expected_mimes = FileSecurityValidator.ALLOWED_FILE_TYPES.get(extension, [])

            if not expected_mimes:
                return False, "Unexpected file extension"

            if mime_type not in expected_mimes:
                return False, f"File MIME type {mime_type} doesn't match extension .{extension}"

            return True, mime_type

        except Exception as e:
            security_logger.error(f"MIME type validation failed: {e}")
            return False, "Unable to validate file type"

    @staticmethod
    def scan_for_malware(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """Scan file for potential malware signatures"""
        if not settings.SCAN_UPLOADED_FILES:
            return True, None

        try:
            # Convert bytes to string for pattern matching
            content_str = file_content.decode('utf-8', errors='ignore').lower()

            # Common malware patterns
            malware_patterns = [
                r'eval\s*\(',
                r'base64_decode\s*\(',
                r'shell_exec\s*\(',
                r'exec\s*\(',
                r'system\s*\(',
                r'passthru\s*\(',
                r'file_get_contents\s*\(',
                r'fopen\s*\(',
                r'unlink\s*\(',
                r'javascript:',
                r'<script',
                r'document\.cookie',
                r'window\.location',
                r'onclick\s*=',
                r'onload\s*=',
            ]

            for pattern in malware_patterns:
                if re.search(pattern, content_str):
                    threat = f"Potential malware pattern detected: {pattern}"
                    security_logger.warning(f"Malware scan failed for {filename}: {threat}")
                    return False, threat

            return True, None

        except Exception as e:
            security_logger.error(f"Malware scanning failed: {e}")
            # Don't block file if scanning fails, but log it
            return True, f"Scanning error: {str(e)}"

    @staticmethod
    def calculate_file_hash(file_content: bytes) -> str:
        """Calculate SHA-256 hash of file"""
        return hashlib.sha256(file_content).hexdigest()

class SecureFileManager:
    """Secure file storage and management"""

    def __init__(self):
        self.base_upload_path = Path(settings.UPLOAD_PATH)
        self.quarantine_path = self.base_upload_path / "quarantine"
        self.base_upload_path.mkdir(exist_ok=True)
        self.quarantine_path.mkdir(exist_ok=True)

    async def save_file(self, file: UploadFile, user_id: int,
                       folder: str = "general") -> Tuple[str, bool, str]:
        """Save file securely"""
        try:
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)

            # Validate file size
            if file_size > settings.MAX_FILE_SIZE:
                return "", False, f"File too large. Maximum size is {settings.MAX_FILE_SIZE} bytes"

            if file_size == 0:
                return "", False, "File is empty"

            # Validate filename
            filename = sanitize_filename(file.filename or "unknown")
            is_valid_ext, result = FileSecurityValidator.validate_file_extension(filename)
            if not is_valid_ext:
                return "", False, result

            extension = result

            # Validate MIME type
            is_valid_mime, mime_type = FileSecurityValidator.validate_mime_type(file_content, extension)
            if not is_valid_mime:
                return "", False, result

            # Scan for malware
            is_clean, threat = FileSecurityValidator.scan_for_malware(file_content, filename)
            if not is_clean and settings.QUARANTINE_INFECTED_FILES:
                # Quarantine the file
                quarantine_filename = f"{uuid.uuid4()}_{filename}"
                quarantine_path = self.quarantine_path / quarantine_filename
                with open(quarantine_path, "wb") as f:
                    f.write(file_content)

                await log_security_event(
                    "MALICIOUS_FILE_QUARANTINED",
                    user_id=user_id,
                    details={
                        "filename": filename,
                        "threat": threat,
                        "quarantine_path": str(quarantine_path)
                    }
                )
                return "", False, f"File contains malicious content: {threat}"

            # Generate unique filename
            file_hash = FileSecurityValidator.calculate_file_hash(file_content)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{filename}"

            # Create upload directory structure
            upload_dir = self.base_upload_path / folder / str(user_id)
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Save file
            file_path = upload_dir / unique_filename
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Log successful upload
            await log_security_event(
                "FILE_UPLOADED",
                user_id=user_id,
                details={
                    "filename": filename,
                    "size": file_size,
                    "mime_type": mime_type,
                    "file_hash": file_hash[:16],  # Log partial hash
                    "path": str(file_path.relative_to(self.base_upload_path))
                }
            )

            # Return relative path for API response
            relative_path = str(file_path.relative_to(self.base_upload_path))
            return relative_path, True, "File uploaded successfully"

        except Exception as e:
            security_logger.error(f"File upload failed: {e}")
            return "", False, f"Upload failed: {str(e)}"

    def delete_file(self, file_path: str, user_id: int) -> Tuple[bool, str]:
        """Delete file securely"""
        try:
            # Construct full path and validate it's within upload directory
            full_path = self.base_upload_path / file_path

            # Security check: ensure path is within upload directory
            try:
                full_path.resolve().relative_to(self.base_upload_path.resolve())
            except ValueError:
                return False, "Invalid file path"

            if not full_path.exists():
                return False, "File not found"

            # Additional security: check if file belongs to user
            # This would require database integration

            # Delete file
            full_path.unlink()

            security_logger.info(f"File deleted: {file_path} by user {user_id}")
            return True, "File deleted successfully"

        except Exception as e:
            security_logger.error(f"File deletion failed: {e}")
            return False, f"Deletion failed: {str(e)}"

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get file information"""
        try:
            # Security check: ensure path is within upload directory
            full_path = self.base_upload_path / file_path

            try:
                full_path.resolve().relative_to(self.base_upload_path.resolve())
            except ValueError:
                return None

            if not full_path.exists():
                return None

            stat = full_path.stat()

            return {
                "filename": full_path.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "mime_type": magic.from_file(str(full_path), mime=True)
            }

        except Exception as e:
            security_logger.error(f"File info retrieval failed: {e}")
            return None

class ImageProcessor:
    """Secure image processing and optimization"""

    @staticmethod
    def validate_image(file_path: str) -> Tuple[bool, str]:
        """Validate image file"""
        try:
            from PIL import Image

            # Open image
            with Image.open(file_path) as img:
                # Check image dimensions (limit to reasonable sizes)
                if img.width > 4096 or img.height > 4096:
                    return False, "Image dimensions too large (max 4096x4096)"

                # Check for suspicious metadata
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        # Log suspicious EXIF data
                        security_logger.info(f"Image EXIF data: {len(exif)} fields")

            return True, "Image is valid"

        except Exception as e:
            return False, f"Invalid image file: {str(e)}"

    @staticmethod
    def create_thumbnail(file_path: str, size: Tuple[int, int] = (300, 300)) -> Optional[str]:
        """Create thumbnail for images"""
        try:
            from PIL import Image

            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Generate thumbnail filename
                path_obj = Path(file_path)
                thumbnail_path = path_obj.parent / f"thumb_{path_obj.name}"

                # Save thumbnail
                img.save(thumbnail_path, 'JPEG', quality=85)

                return str(thumbnail_path)

        except Exception as e:
            security_logger.error(f"Thumbnail creation failed: {e}")
            return None

# Initialize secure file manager
secure_file_manager = SecureFileManager()

async def handle_secure_upload(file: UploadFile, user_id: int, folder: str = "general"):
    """Main function to handle secure file uploads"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )

    # Validate file
    file_content = await file.read()
    await file.seek(0)  # Reset file pointer

    file_size = len(file_content)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE} bytes"
        )

    # Save file securely
    file_path, success, message = await secure_file_manager.save_file(file, user_id, folder)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return {
        "file_path": file_path,
        "original_filename": file.filename,
        "size": file_size,
        "message": message
    }

def clean_old_files(days: int = 30):
    """Clean up old temporary files"""
    try:
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        for file_path in secure_file_manager.base_upload_path.rglob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    file_path.unlink()
                    security_logger.info(f"Cleaned old file: {file_path}")

    except Exception as e:
        security_logger.error(f"File cleanup failed: {e}")