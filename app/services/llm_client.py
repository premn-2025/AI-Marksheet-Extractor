import logging
import asyncio
import time
import base64
from typing import Dict, Any
from openai import OpenAI
import google.generativeai as genai
from app.config.settings import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """Unified client for different LLM providers with rate limiting"""
    
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.last_request_time = 0
        self.min_request_interval = 4  # 4 seconds between requests (15/minute = 4s interval)
        self.setup_client()
    
    def setup_client(self):
        """Initialize the appropriate LLM client"""
        if self.provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self.client = OpenAI(api_key=settings.openai_api_key)
            
        elif self.provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("Gemini API key not configured") 
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')  # Use Flash as primary
            self.pro_model = genai.GenerativeModel('gemini-1.5-pro')  # Keep Pro as fallback
            
        elif self.provider == "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError("OpenRouter API key not configured")
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    async def extract_from_image(self, base64_image: str, prompt: str) -> Dict[str, Any]:
        """Extract data from image using the configured LLM with rate limiting and retry logic"""
        # Add rate limiting
        await self._rate_limit()
        
        try:
            if self.provider == "openai":
                return await self._extract_openai(base64_image, prompt)
            elif self.provider == "gemini":
                return await self._extract_gemini(base64_image, prompt)
            elif self.provider == "openrouter":
                return await self._extract_openrouter(base64_image, prompt)
        except Exception as e:
            # If rate limited, wait and retry
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning(f"Rate limited, waiting 60 seconds...")
                await asyncio.sleep(60)
                return await self.extract_from_image(base64_image, prompt)
            logger.error(f"LLM extraction failed: {str(e)}")
            raise Exception(f"Failed to extract data: {str(e)}")
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            logger.info(f"Rate limiting: waiting {wait_time:.1f} seconds")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def _extract_openai(self, base64_image: str, prompt: str) -> Dict[str, Any]:
        """Extract using OpenAI GPT-4o with enhanced prompting"""
        try:
            # Enhanced prompt for better subject name extraction
            enhanced_prompt = f"""
{prompt}

CRITICAL: Pay special attention to extracting COMPLETE subject names from tables. 
Look for subject names in:
- First column of tables
- Header rows
- Left-side labels
- Subject titles before marks

Examples of subject names to extract:
- MATHEMATICS, ENGLISH, HINDI, SCIENCE
- Environmental Studies, Indian Writing in English
- PHYSICAL SCIENCE, LIFE SCIENCE
- British Poetry and Drama, Feminism Theory

DO NOT use "N/A" for subject names - always extract the actual subject text.
"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": enhanced_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                max_tokens=3000,
                temperature=0.05,
            )
            
            return {
                "content": response.choices[0].message.content,
                "provider": "openai",
                "model": "gpt-4o"
            }
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {str(e)}")
            raise
    
    async def _extract_gemini(self, base64_image: str, prompt: str) -> Dict[str, Any]:
        """Extract using Google Gemini with Flash as primary and Pro as fallback"""
        try:
            # Convert base64 to image data
            image_data = base64.b64decode(base64_image)
            
            # Create image part for Gemini
            image_part = {
                "mime_type": "image/jpeg",
                "data": image_data
            }
            
            # Enhanced prompt specifically for subject name extraction
            enhanced_prompt = f"""
{prompt}

ENHANCED INSTRUCTIONS FOR SUBJECT NAME EXTRACTION:

1. NEVER use "N/A" for subject names
2. Look carefully at table structures - subject names are usually in:
   - Left column of marks tables
   - Header rows above marks
   - Text labels before numerical values

3. For different marksheet formats:
   - Traditional boards: Look for subjects like "MATHEMATICS", "ENGLISH", "SCIENCE"
   - Universities: Look for course titles like "Environmental Studies", "Indian Writing in English"

4. Extract COMPLETE subject names with proper capitalization
5. If oral/written components exist, include the full description

FOCUS: Your primary task is extracting accurate, complete subject names along with their marks.
"""

            # Try Flash model first (higher quota)
            try:
                response = self.model.generate_content(
                    [enhanced_prompt, image_part],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.05,
                        max_output_tokens=3000,
                        candidate_count=1,
                    )
                )
                
                # Check if response was blocked
                if (response.candidates and 
                    response.candidates[0].finish_reason and
                    response.candidates[0].finish_reason.name == "SAFETY"):
                    raise Exception("Content was blocked by safety filters")
                
                if not response.text or len(response.text.strip()) < 50:
                    raise Exception("Response too short or empty from Gemini Flash")
                
                return {
                    "content": response.text,
                    "provider": "gemini",
                    "model": "gemini-1.5-flash"
                }
                
            except Exception as e:
                # If Flash model fails, try Pro model
                logger.warning(f"Gemini Flash failed, trying Pro model: {str(e)}")
                
                response = self.pro_model.generate_content(
                    [enhanced_prompt, image_part],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=3000,
                    )
                )
                
                if not response.text:
                    raise Exception("Empty response from Gemini Pro")
                
                return {
                    "content": response.text,
                    "provider": "gemini",
                    "model": "gemini-1.5-pro"
                }
                
        except Exception as e:
            logger.error(f"Gemini extraction failed: {str(e)}")
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def _extract_openrouter(self, base64_image: str, prompt: str) -> Dict[str, Any]:
        """Extract using OpenRouter with multiple model fallbacks"""
        try:
            # Enhanced prompt for OpenRouter
            enhanced_prompt = f"""
{prompt}

OPENROUTER SPECIFIC INSTRUCTIONS:
- Extract ALL subject names from the marksheet image
- Look for subject names in table headers, first columns, and labels
- Common subjects: Math, English, Science, History, Geography, Languages
- University courses: Environmental Studies, Literature, etc.
- NEVER return "N/A" for subject names - always find the actual text
"""

            # Try multiple models for best results
            models_to_try = [
                "google/gemini-2.0-flash-exp",
                "google/gemini-1.5-pro",
                "openai/gpt-4o-mini",
                "anthropic/claude-3-haiku"
            ]
            
            last_error = None
            
            for model in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        extra_headers={
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "AI Marksheet Extractor",
                        },
                        model=model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": enhanced_prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=3000,
                        temperature=0.05
                    )
                    
                    content = response.choices[0].message.content
                    if content and len(content.strip()) > 100:  # Ensure meaningful response
                        return {
                            "content": content,
                            "provider": "openrouter",
                            "model": model
                        }
                    else:
                        raise Exception(f"Response too short from {model}")
                    
                except Exception as e:
                    logger.warning(f"OpenRouter model {model} failed: {str(e)}")
                    last_error = e
                    continue
            
            # If all models failed
            raise last_error or Exception("All OpenRouter models failed")
            
        except Exception as e:
            logger.error(f"OpenRouter extraction failed: {str(e)}")
            raise
    
    def get_available_models(self) -> Dict[str, list]:
        """Get available models for each provider"""
        return {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            "gemini": ["gemini-1.5-flash", "gemini-1.5-pro"],  # Flash first
            "openrouter": [
                "google/gemini-2.0-flash-exp",
                "google/gemini-1.5-pro", 
                "openai/gpt-4o",
                "anthropic/claude-3-5-sonnet"
            ]
        }
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get current provider information"""
        return {
            "provider": self.provider,
            "configured": True,
            "model": getattr(self, 'current_model', 'auto-detect'),
            "rate_limiting": f"{self.min_request_interval}s interval"
        }
    
    def validate_api_key(self) -> bool:
        """Validate that the API key is working"""
        try:
            if self.provider == "gemini":
                # Simple test with Gemini
                test_response = genai.list_models()
                return len(list(test_response)) > 0
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False
