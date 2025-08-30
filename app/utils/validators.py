import os
from pathlib import Path
from fastapi import HTTPException, UploadFile
from typing import Tuple, List
from app.config.settings import settings

class FileValidator:
    """Validate uploaded files"""
    
    def __init__(self):
        self.max_size = settings.max_file_size  # FIX: Use new settings format
        # Use settings or fallback to hardcoded values
        self.allowed_extensions = getattr(settings, 'allowed_extensions', {'.jpg', '.jpeg', '.png', '.pdf', '.webp'})
        
    def validate_file(self, file: UploadFile) -> bool:
        """
        Validate uploaded file
        
        Args:
            file: UploadFile object from FastAPI
            
        Returns:
            bool: True if valid
            
        Raises:
            HTTPException: If validation fails
        """
        # Check if file is provided
        if not file or not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file provided"
            )
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not supported. Allowed types: {', '.join(self.allowed_extensions)}"
            )
        
        # Check file size (if available)
        if hasattr(file, 'size') and file.size:
            if file.size > self.max_size:
                max_mb = self.max_size / (1024 * 1024)
                raise HTTPException(
                    status_code=413,
                    detail=f"File size exceeds maximum allowed size of {max_mb:.1f}MB"
                )
        
        # Validate content type
        if not self.validate_content_type(file.content_type or '', file_ext):
            raise HTTPException(
                status_code=400,
                detail=f"Content type {file.content_type} doesn't match file extension {file_ext}"
            )
        
        return True
    
    def validate_content_type(self, content_type: str, file_ext: str) -> bool:
        """Validate content type matches file extension"""
        content_type_mapping = {
            '.jpg': ['image/jpeg'],
            '.jpeg': ['image/jpeg'], 
            '.png': ['image/png'],
            '.webp': ['image/webp'],
            '.pdf': ['application/pdf']
        }
        
        expected_types = content_type_mapping.get(file_ext.lower(), [])
        if not expected_types:
            return False
        
        return content_type.lower() in [t.lower() for t in expected_types]
    
    def validate_batch_files(self, files: List[UploadFile]) -> bool:
        """Validate multiple files for batch processing"""
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided"
            )
        
        # Use settings or default to 10
        max_batch_files = getattr(settings, 'max_batch_files', 10)
        if len(files) > max_batch_files:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. Maximum {max_batch_files} files allowed per batch"
            )
        
        # Validate each file
        for i, file in enumerate(files):
            try:
                self.validate_file(file)
            except HTTPException as e:
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"File {i+1} ({file.filename}): {e.detail}"
                )
        
        return True
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        if not settings.enable_auth:  # FIX: Use new settings format
            return True
            
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key is required"
            )
            
        if api_key != settings.api_key:  # FIX: Use new settings format
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
            
        return True

    @classmethod
    def get_allowed_extensions(cls) -> set:
        """Get set of allowed file extensions"""
        return {'.jpg', '.jpeg', '.png', '.pdf', '.webp'}
    
    @classmethod
    def get_allowed_mime_types(cls) -> set:
        """Get set of allowed MIME types"""
        return {
            'image/jpeg',
            'image/png', 
            'image/webp',
            'application/pdf'
        }
    
    def get_file_size_mb(self, size_bytes: int) -> float:
        """Convert bytes to MB"""
        return size_bytes / (1024 * 1024)
    
    def get_max_file_size_mb(self) -> float:
        """Get maximum file size in MB"""
        return self.max_size / (1024 * 1024)
    
    def is_image_file(self, file_ext: str) -> bool:
        """Check if file extension is an image type"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        return file_ext.lower() in image_extensions
    
    def is_pdf_file(self, file_ext: str) -> bool:
        """Check if file extension is PDF"""
        return file_ext.lower() == '.pdf'
