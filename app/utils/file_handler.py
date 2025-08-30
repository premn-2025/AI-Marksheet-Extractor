import os
import aiofiles
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import PyPDF2
from pdf2image import convert_from_bytes
import base64
from io import BytesIO
from typing import Tuple, Union, List
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

class FileHandler:
    """Handle file upload, validation, and processing with enhanced image processing"""
    
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
    
    async def process_upload(self, file) -> Tuple[str, str]:
        """
        Process uploaded file and return file type and base64 content
        
        Args:
            file: UploadFile object from FastAPI
            
        Returns:
            Tuple of (file_type, base64_encoded_image)
        """
        try:
            # Read file content
            content = await file.read()
            file_ext = Path(file.filename).suffix.lower()
            
            if file_ext == '.pdf':
                # Convert PDF to images and return base64 encoded
                images = self._pdf_to_images(content)
                # Process only the first page
                base64_data = self._image_to_base64(images[0])
                return 'pdf', base64_data
            
            elif file_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                # Process image file with enhancements
                base64_data = self._process_image_to_base64(content)
                return 'image', base64_data
            
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
                
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            raise
    
    async def process_batch_files(self, files: List) -> List[Tuple[str, str, str, bool]]:
        """
        Process multiple files for batch extraction
        
        Returns:
            List of (file_type, base64_content, filename, success)
        """
        results = []
        
        for file in files:
            try:
                file_type, base64_content = await self.process_upload(file)
                results.append((file_type, base64_content, file.filename, True))
            except Exception as e:
                logger.error(f"Failed to process {file.filename}: {str(e)}")
                results.append(('error', '', file.filename, False))
        
        return results
    
    def _pdf_to_images(self, pdf_content: bytes) -> list:
        """Convert PDF to list of PIL Images with high DPI for better text recognition"""
        try:
            images = convert_from_bytes(
                pdf_content, 
                dpi=400,  # Increased DPI for better text recognition
                first_page=1, 
                last_page=1
            )
            if not images:
                raise ValueError("No pages found in PDF")
            return images
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise ValueError("Failed to process PDF file")
    
    def _process_image_to_base64(self, image_content: bytes) -> str:
        """Process image with enhancements for better text extraction and return base64 string"""
        try:
            # Open image (PIL automatically supports WebP)
            image = Image.open(BytesIO(image_content))
            
            # Convert RGBA/LA/P to RGB (important for WebP with transparency)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                # Paste with alpha mask if available
                if image.mode in ('RGBA', 'LA'):
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # ENHANCED IMAGE PROCESSING FOR BETTER TEXT RECOGNITION
            
            # 1. Resize image if too small (upscale for better recognition)
            min_size = 1500  # Minimum width/height for good OCR
            if min(image.size) < min_size:
                scale_factor = min_size / min(image.size)
                new_size = (int(image.size[0] * scale_factor), int(image.size[1] * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 2. Enhance contrast for better text recognition
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.3)  # Boost contrast moderately
            
            # 3. Enhance sharpness to make text clearer
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.8)  # Sharpen text edges
            
            # 4. Slightly enhance brightness if image is too dark
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)  # Slight brightness boost
            
            # 5. Apply unsharp mask filter for better edge definition
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=1))
            
            # Resize if too large (after processing)
            max_size = 1024
            if max(image.size) > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to base64
            return self._image_to_base64(image)
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise ValueError("Failed to process image file")
    
    def _image_to_base64(self, image: Union[Image.Image, bytes]) -> str:
        """Convert PIL Image or bytes to base64 encoded string"""
        try:
            if isinstance(image, Image.Image):
                # Convert PIL Image to bytes with high quality
                output = BytesIO()
                image.save(output, format='JPEG', quality=95, optimize=True)  # Higher quality
                image_bytes = output.getvalue()
            else:
                image_bytes = image
            
            # Encode to base64 and return as string
            base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
            return base64_encoded
            
        except Exception as e:
            logger.error(f"Error encoding image to base64: {str(e)}")
            raise ValueError("Failed to encode image")
    
    async def save_temp_file(self, content: bytes, filename: str) -> Path:
        """Save content to temporary file"""
        try:
            file_path = self.upload_dir / filename
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            return file_path
        except Exception as e:
            logger.error(f"Error saving temp file: {str(e)}")
            raise
    
    def cleanup_temp_file(self, file_path: Path):
        """Remove temporary file"""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {str(e)}")
    
    async def get_file_info(self, file) -> dict:
        """Get enhanced file metadata"""
        # Read content to get actual size
        content = await file.read()
        # Reset file pointer
        await file.seek(0)
        
        return {
            'filename': file.filename,
            'content_type': file.content_type,
            'size': len(content),
            'size_mb': len(content) / (1024 * 1024),
            'extension': Path(file.filename).suffix.lower() if file.filename else '',
            'is_supported': Path(file.filename).suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.pdf']
        }
    
    def enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Additional method for manual image enhancement if needed"""
        try:
            # Convert to grayscale for better contrast in some cases
            gray = image.convert('L')
            
            # Apply adaptive enhancement based on image characteristics
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(1.5)
            
            # Convert back to RGB
            return enhanced.convert('RGB')
            
        except Exception as e:
            logger.warning(f"Failed to enhance image for OCR: {str(e)}")
            return image
