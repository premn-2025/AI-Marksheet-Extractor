import logging
from typing import Dict, Any, List
import json
import re
from app.services.llm_client import LLMClient
from app.models.schemas import (
    MarksheetData, CandidateDetails, SubjectMark, 
    OverallResult, DocumentInfo, ExtractedField
)
from app.prompts.extraction_prompt import get_extraction_prompt
from app.utils.confidence import ConfidenceCalculator

logger = logging.getLogger(__name__)

class MarksheetExtractor:
    """Core extraction service using LLM with enhanced subject name extraction"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.confidence_calc = ConfidenceCalculator()
        
        # Common subject patterns for validation and inference
        self.common_subjects = [
            "MATHEMATICS", "ENGLISH", "HINDI", "SCIENCE", "SOCIAL SCIENCE",
            "PHYSICS", "CHEMISTRY", "BIOLOGY", "HISTORY", "GEOGRAPHY",
            "FIRST LANGUAGE", "SECOND LANGUAGE", "PHYSICAL SCIENCE", "LIFE SCIENCE",
            "Environmental Studies", "Indian Writing in English", "British Poetry",
            "Feminism Theory", "DRAWING", "COMPUTER SCIENCE", "ECONOMICS"
        ]
    
    async def extract_data(self, base64_image: str, filename: str) -> MarksheetData:
        """
        Extract marksheet data using LLM with enhanced subject name processing
        
        Args:
            base64_image: Base64 encoded image data (string, not bytes)
            filename: Original filename for context
            
        Returns:
            MarksheetData object with extracted information
        """
        try:
            # Get enhanced extraction prompt
            prompt = get_extraction_prompt()
            
            # Extract data using LLM
            logger.info(f"Starting extraction for file: {filename}")
            
            # Extract from image using LLM client
            llm_response = await self.llm_client.extract_from_image(base64_image, prompt)
            
            # Parse JSON response from LLM
            raw_data = self._parse_llm_response(llm_response)
            
            # Validate and fix subject names
            raw_data = self._validate_and_fix_subjects(raw_data)
            
            # Structure the data
            structured_data = self._structure_extracted_data(raw_data)
            
            # Apply confidence post-processing
            structured_data = self._post_process_confidence(structured_data)
            
            logger.info(f"Extraction completed for file: {filename}")
            return structured_data
            
        except Exception as e:
            logger.error(f"Extraction failed for {filename}: {str(e)}")
            raise
    
    def _parse_llm_response(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate LLM response with better JSON extraction"""
        try:
            # Extract content from LLM response
            content = llm_response.get('content', '')
            
            if not content:
                raise ValueError("Empty response from LLM")
            
            logger.debug(f"LLM Response content: {content[:500]}...")  # Log first 500 chars
            
            # Multiple strategies to extract JSON
            json_data = None
            
            # Strategy 1: Direct JSON parsing
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError:
                pass
            
            # Strategy 2: Extract JSON block from response
            if not json_data:
                try:
                    # Find JSON boundaries
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    
                    if json_start != -1 and json_end > json_start:
                        json_content = content[json_start:json_end]
                        json_data = json.loads(json_content)
                except json.JSONDecodeError:
                    pass
            
            # Strategy 3: Clean and retry
            if not json_data:
                try:
                    # Remove markdown code blocks and extra text
                    cleaned_content = re.sub(r'```  json\s*', '', content)
                    cleaned_content = re.sub(r'```\s*', '', cleaned_content)
                    cleaned_content = cleaned_content.strip()
                    
                    # Try to find JSON again
                    json_start = cleaned_content.find('{')
                    json_end = cleaned_content.rfind('}') + 1
                    
                    if json_start != -1 and json_end > json_start:
                        json_content = cleaned_content[json_start:json_end]
                        json_data = json.loads(json_content)
                except json.JSONDecodeError:
                    pass
            
            # If all strategies failed, create fallback structure
            if not json_data:
                logger.warning("Failed to parse JSON from LLM response, using fallback structure")
                return self._create_fallback_structure(content)
            
            return json_data
                
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            raise ValueError(f"Failed to parse LLM response: {str(e)}")
    
    def _validate_and_fix_subjects(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and attempt to fix missing subject names"""
        try:
            subjects = raw_data.get('subjects', [])
            
            if not isinstance(subjects, list):
                logger.warning("Subjects data is not a list, skipping validation")
                return raw_data
            
            fixed_subjects = []
            
            for i, subject in enumerate(subjects):
                if not isinstance(subject, dict):
                    continue
                
                # Get subject name
                subject_name_data = subject.get('subject_name', {})
                
                # Extract value from different formats
                if isinstance(subject_name_data, dict):
                    subject_name = subject_name_data.get('value', '')
                elif isinstance(subject_name_data, str):
                    subject_name = subject_name_data
                else:
                    subject_name = str(subject_name_data) if subject_name_data else ''
                
                # Check if subject name is missing or invalid
                if not subject_name or subject_name.lower() in ['n/a', 'null', 'none', '']:
                    # Try to infer subject name from context
                    inferred_name = self._infer_subject_name(subject, i)
                    
                    if inferred_name:
                        subject['subject_name'] = {
                            "value": inferred_name,
                            "confidence": 0.6  # Lower confidence for inferred names
                        }
                        logger.info(f"Inferred subject name: {inferred_name}")
                    else:
                        # Use fallback naming
                        fallback_name = f"Subject {i+1}"
                        subject['subject_name'] = {
                            "value": fallback_name,
                            "confidence": 0.3
                        }
                        logger.warning(f"Using fallback subject name: {fallback_name}")
                else:
                    # Validate and clean existing subject name
                    cleaned_name = self._clean_subject_name(subject_name)
                    if cleaned_name != subject_name:
                        if isinstance(subject_name_data, dict):
                            subject['subject_name']['value'] = cleaned_name
                        else:
                            subject['subject_name'] = {
                                "value": cleaned_name,
                                "confidence": 0.8
                            }
                
                fixed_subjects.append(subject)
            
            raw_data['subjects'] = fixed_subjects
            return raw_data
            
        except Exception as e:
            logger.error(f"Error validating subjects: {str(e)}")
            return raw_data
    
    def _infer_subject_name(self, subject_data: Dict[str, Any], index: int) -> str:
        """Attempt to infer subject name from marks patterns and context"""
        try:
            # Try to get marks information for inference
            obtained_marks = self._extract_value(subject_data.get('obtained_marks'))
            max_marks = self._extract_value(subject_data.get('max_marks'))
            grade = self._extract_value(subject_data.get('grade'))
            
            # Pattern-based inference
            if max_marks:
                try:
                    max_marks_int = int(float(max_marks))
                    
                    # Common patterns for different subjects
                    if max_marks_int == 200:
                        return "FIRST LANGUAGE"
                    elif max_marks_int == 100:
                        # Use position-based inference for 100-mark subjects
                        common_100_subjects = [
                            "MATHEMATICS", "ENGLISH", "SCIENCE", "SOCIAL SCIENCE",
                            "PHYSICS", "CHEMISTRY", "BIOLOGY", "HISTORY", "GEOGRAPHY"
                        ]
                        if index < len(common_100_subjects):
                            return common_100_subjects[index]
                    elif max_marks_int == 90:
                        return f"WRITTEN COMPONENT {index+1}"
                    elif max_marks_int in [10, 20]:
                        return f"ORAL COMPONENT {index+1}"
                        
                except (ValueError, TypeError):
                    pass
            
            # Grade-based inference
            if grade:
                grade_str = str(grade).upper()
                if grade_str in ['A1', 'A2', 'B1', 'B2']:
                    # Likely CBSE pattern
                    cbse_subjects = ["HINDI", "ENGLISH", "MATHEMATICS", "SCIENCE", "SOCIAL SCIENCE"]
                    if index < len(cbse_subjects):
                        return cbse_subjects[index]
                elif grade_str in ['A+', 'A', 'B+', 'B']:
                    # Likely university pattern
                    uni_subjects = ["Environmental Studies", "Literature", "Core Subject", "Elective"]
                    if index < len(uni_subjects):
                        return uni_subjects[index]
            
            # Position-based fallback
            if index < len(self.common_subjects):
                return self.common_subjects[index]
            
            return None
            
        except Exception as e:
            logger.warning(f"Error inferring subject name: {str(e)}")
            return None
    
    def _clean_subject_name(self, subject_name: str) -> str:
        """Clean and standardize subject names"""
        if not subject_name:
            return subject_name
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', subject_name.strip())
        
        # Common abbreviation expansions
        expansions = {
            'MATH': 'MATHEMATICS',
            'ENG': 'ENGLISH',
            'SCI': 'SCIENCE',
            'SOC': 'SOCIAL SCIENCE',
            'PHYS': 'PHYSICS',
            'CHEM': 'CHEMISTRY',
            'BIO': 'BIOLOGY',
            'HIST': 'HISTORY',
            'GEO': 'GEOGRAPHY',
            'FL': 'FIRST LANGUAGE',
            'SL': 'SECOND LANGUAGE'
        }
        
        # Apply expansions
        for abbrev, full_name in expansions.items():
            if cleaned.upper().startswith(abbrev):
                cleaned = cleaned.upper().replace(abbrev, full_name, 1)
        
        return cleaned
    
    def _extract_value(self, field_data: Any) -> str:
        """Extract value from field data regardless of format"""
        if isinstance(field_data, dict):
            return str(field_data.get('value', ''))
        elif field_data is not None:
            return str(field_data)
        return ''
    
    def _create_fallback_structure(self, content: str) -> Dict[str, Any]:
        """Create fallback structure when JSON parsing fails"""
        logger.warning("Creating fallback structure due to JSON parsing failure")
        
        # Try to extract basic information using regex
        fallback_data = {
            "candidate_details": {},
            "subjects": [],
            "overall_result": {},
            "document_info": {},
            "raw_content": content
        }
        
        # Simple regex patterns to extract basic info
        try:
            # Extract names
            name_patterns = [
                r'[Nn]ame[:\s]+([A-Z][A-Z\s]+)',
                r'Name[:\s]+([A-Z][A-Z\s]+)',
                r'Student[:\s]+([A-Z][A-Z\s]+)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, content)
                if match:
                    fallback_data["candidate_details"]["name"] = {
                        "value": match.group(1).strip(),
                        "confidence": 0.5
                    }
                    break
        except Exception as e:
            logger.debug(f"Error in fallback parsing: {str(e)}")
        
        return fallback_data
    
    def _structure_extracted_data(self, raw_data: Dict[str, Any]) -> MarksheetData:
        """Convert raw LLM response to structured MarksheetData"""
        try:
            # Extract candidate details
            candidate_raw = raw_data.get('candidate_details', {})
            candidate_details = CandidateDetails(
                name=self._create_extracted_field(candidate_raw.get('name')),
                father_name=self._create_extracted_field(candidate_raw.get('father_name')),
                mother_name=self._create_extracted_field(candidate_raw.get('mother_name')),
                roll_number=self._create_extracted_field(candidate_raw.get('roll_number')),
                registration_number=self._create_extracted_field(candidate_raw.get('registration_number')),
                date_of_birth=self._create_extracted_field(candidate_raw.get('date_of_birth')),
                exam_year=self._create_extracted_field(candidate_raw.get('exam_year')),
                board_university=self._create_extracted_field(candidate_raw.get('board_university')),
                institution=self._create_extracted_field(candidate_raw.get('institution'))
            )
            
            # Extract subjects with validation
            subjects_raw = raw_data.get('subjects', [])
            subjects = []
            
            if isinstance(subjects_raw, list):
                for subject_raw in subjects_raw:
                    if isinstance(subject_raw, dict):
                        subject = SubjectMark(
                            subject_name=self._create_extracted_field(subject_raw.get('subject_name')),
                            max_marks=self._create_extracted_field(subject_raw.get('max_marks')),
                            max_credits=self._create_extracted_field(subject_raw.get('max_credits')),
                            obtained_marks=self._create_extracted_field(subject_raw.get('obtained_marks')),
                            obtained_credits=self._create_extracted_field(subject_raw.get('obtained_credits')),
                            grade=self._create_extracted_field(subject_raw.get('grade')),
                            remarks=self._create_extracted_field(subject_raw.get('remarks'))
                        )
                        subjects.append(subject)
            
            # Extract overall result
            result_raw = raw_data.get('overall_result', {})
            overall_result = OverallResult(
                total_marks=self._create_extracted_field(result_raw.get('total_marks')),
                total_credits=self._create_extracted_field(result_raw.get('total_credits')),
                percentage=self._create_extracted_field(result_raw.get('percentage')),
                cgpa=self._create_extracted_field(result_raw.get('cgpa')),
                grade=self._create_extracted_field(result_raw.get('grade')),
                division=self._create_extracted_field(result_raw.get('division')),
                result_status=self._create_extracted_field(result_raw.get('result_status'))
            )
            
            # Extract document info
            doc_raw = raw_data.get('document_info', {})
            document_info = DocumentInfo(
                issue_date=self._create_extracted_field(doc_raw.get('issue_date')),
                issue_place=self._create_extracted_field(doc_raw.get('issue_place')),
                document_type=self._create_extracted_field(doc_raw.get('document_type')),
                academic_session=self._create_extracted_field(doc_raw.get('academic_session'))
            )
            
            return MarksheetData(
                candidate_details=candidate_details,
                subjects=subjects,
                overall_result=overall_result,
                document_info=document_info
            )
            
        except Exception as e:
            logger.error(f"Error structuring extracted data: {str(e)}")
            raise ValueError(f"Failed to structure extracted data: {str(e)}")
    
    def _create_extracted_field(self, field_data: Any) -> ExtractedField:
        """Create ExtractedField from raw field data with enhanced validation"""
        if not field_data:
            return ExtractedField(value=None, confidence=0.0)
        
        # Handle different input formats
        if isinstance(field_data, dict):
            value = field_data.get('value')
            confidence = field_data.get('confidence', 0.0)
            bounding_box = field_data.get('bounding_box')
        elif isinstance(field_data, str):
            # Simple string value
            value = field_data
            confidence = 0.8  # Default confidence for string values
            bounding_box = None
        else:
            # Other types (int, float, etc.)
            value = str(field_data)
            confidence = 0.8
            bounding_box = None
        
        # Clean value
        if value:
            value = str(value).strip()
            if value.lower() in ['n/a', 'null', 'none', '']:
                value = None
                confidence = 0.0
        
        # Ensure confidence is within valid range
        try:
            confidence = max(0.0, min(1.0, float(confidence) if confidence is not None else 0.0))
        except (ValueError, TypeError):
            confidence = 0.0
        
        return ExtractedField(
            value=value,
            confidence=confidence,
            bounding_box=bounding_box
        )
    
    def _post_process_confidence(self, data: MarksheetData) -> MarksheetData:
        """Apply post-processing confidence adjustments"""
        try:
            # Apply confidence calibration
            data = self.confidence_calc.calibrate_confidence(data)
            
            # Apply consistency checks
            data = self.confidence_calc.apply_consistency_checks(data)
            
            return data
            
        except Exception as e:
            logger.warning(f"Confidence post-processing failed: {str(e)}")
            return data  # Return original data if post-processing fails
    
    def get_extraction_metadata(self, filename: str) -> Dict[str, Any]:
        """Get enhanced metadata about the extraction process"""
        try:
            provider_info = self.llm_client.get_provider_info()
        except AttributeError:
            # Fallback if method doesn't exist
            provider_info = {
                "provider": getattr(self.llm_client, 'provider', 'unknown'),
                "configured": True
            }
        
        try:
            confidence_info = self.confidence_calc.get_method_info()
        except AttributeError:
            # Fallback if method doesn't exist
            confidence_info = {"method": "multi-factor", "version": "1.0"}
        
        return {
            "filename": filename,
            "llm_provider": provider_info.get("provider", "unknown"),
            "model_info": provider_info,
            "extraction_version": "1.1.0",  # Updated version
            "confidence_method": confidence_info,
            "features": [
                "subject_name_validation",
                "intelligent_inference",
                "fallback_parsing",
                "enhanced_cleaning"
            ]
        }
    
    async def extract_batch_data(self, batch_data: List[tuple]) -> List[Dict[str, Any]]:
        """Extract data from multiple files with enhanced error handling"""
        results = []
        
        for base64_image, filename in batch_data:
            try:
                extracted_data = await self.extract_data(base64_image, filename)
                results.append({
                    "filename": filename,
                    "success": True,
                    "data": extracted_data.model_dump(),  # Updated for Pydantic v2
                    "metadata": self.get_extraction_metadata(filename)
                })
            except Exception as e:
                logger.error(f"Batch extraction failed for {filename}: {str(e)}")
                results.append({
                    "filename": filename,
                    "success": False,
                    "error": str(e),
                    "data": None
                })
        
        return results
    
    def validate_extraction_quality(self, data: MarksheetData) -> Dict[str, Any]:
        """Validate the quality of extracted data"""
        quality_metrics = {
            "subject_names_extracted": 0,
            "marks_extracted": 0,
            "candidate_info_completeness": 0,
            "overall_quality_score": 0.0
        }
        
        try:
            # Count valid subject names
            valid_subjects = 0
            valid_marks = 0
            
            for subject in data.subjects:
                if subject.subject_name.value and subject.subject_name.value != "N/A":
                    valid_subjects += 1
                if subject.obtained_marks.value:
                    valid_marks += 1
            
            quality_metrics["subject_names_extracted"] = valid_subjects
            quality_metrics["marks_extracted"] = valid_marks
            
            # Calculate candidate info completeness
            candidate_fields = [
                data.candidate_details.name.value,
                data.candidate_details.roll_number.value,
                data.candidate_details.exam_year.value
            ]
            completed_fields = sum(1 for field in candidate_fields if field)
            quality_metrics["candidate_info_completeness"] = completed_fields / len(candidate_fields)
            
            # Overall quality score
            if len(data.subjects) > 0:
                subject_quality = valid_subjects / len(data.subjects)
                marks_quality = valid_marks / len(data.subjects)
                quality_metrics["overall_quality_score"] = (
                    subject_quality * 0.4 + 
                    marks_quality * 0.4 + 
                    quality_metrics["candidate_info_completeness"] * 0.2
                )
            
        except Exception as e:
            logger.warning(f"Error calculating quality metrics: {str(e)}")
        
        return quality_metrics
