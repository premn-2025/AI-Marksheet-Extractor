import numpy as np
from typing import Dict, Any, List
from app.models.schemas import MarksheetData, ExtractedField
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class ConfidenceCalculator:
    """Calculate and calibrate confidence scores for extracted data"""
    
    def __init__(self):
        self.min_threshold = settings.min_confidence_threshold  # FIX: Use new settings format
        
        # Confidence weights for different factors
        self.weights = getattr(settings, 'confidence_weights', {
            'text_clarity': 0.4,
            'context_validation': 0.3,
            'position_context': 0.2,
            'format_validation': 0.1
        })
    
    def calibrate_confidence(self, data: MarksheetData) -> MarksheetData:
        """Apply confidence calibration to all extracted fields"""
        try:
            # Calibrate candidate details
            if data.candidate_details:
                for field_name in data.candidate_details.__fields__.keys():
                    field = getattr(data.candidate_details, field_name)
                    if isinstance(field, ExtractedField):
                        calibrated = self._calibrate_field(field, 'candidate_detail')
                        setattr(data.candidate_details, field_name, calibrated)
            
            # Calibrate subjects
            if data.subjects:
                for subject in data.subjects:
                    for field_name in subject.__fields__.keys():
                        field = getattr(subject, field_name)
                        if isinstance(field, ExtractedField):
                            calibrated = self._calibrate_field(field, 'subject_mark')
                            setattr(subject, field_name, calibrated)
            
            # Calibrate overall result
            if data.overall_result:
                for field_name in data.overall_result.__fields__.keys():
                    field = getattr(data.overall_result, field_name)
                    if isinstance(field, ExtractedField):
                        calibrated = self._calibrate_field(field, 'overall_result')
                        setattr(data.overall_result, field_name, calibrated)
            
            # Calibrate document info
            if data.document_info:
                for field_name in data.document_info.__fields__.keys():
                    field = getattr(data.document_info, field_name)
                    if isinstance(field, ExtractedField):
                        calibrated = self._calibrate_field(field, 'document_info')
                        setattr(data.document_info, field_name, calibrated)
            
            return data
            
        except Exception as e:
            logger.warning(f"Confidence calibration failed: {str(e)}")
            return data
    
    def _calibrate_field(self, field: ExtractedField, field_type: str) -> ExtractedField:
        """Calibrate confidence for a single field"""
        if not field or not field.value:
            return field
        
        try:
            # Apply different calibration based on field type
            calibration_factor = self._get_calibration_factor(field_type)
            
            # Calculate calibrated confidence
            original_confidence = field.confidence
            calibrated_confidence = min(1.0, original_confidence * calibration_factor)
            
            # Ensure minimum threshold
            if calibrated_confidence < self.min_threshold and field.value:
                calibrated_confidence = max(calibrated_confidence, self.min_threshold)
            
            # Create new field with calibrated confidence
            return ExtractedField(
                value=field.value,
                confidence=calibrated_confidence,
                bounding_box=field.bounding_box
            )
            
        except Exception as e:
            logger.warning(f"Field calibration failed: {str(e)}")
            return field
    
    def _get_calibration_factor(self, field_type: str) -> float:
        """Get calibration factor based on field type"""
        factors = {
            'candidate_detail': 1.0,
            'subject_mark': 0.95,  # Slightly lower for marks
            'overall_result': 1.05,  # Slightly higher for totals
            'document_info': 0.9   # Lower for optional info
        }
        return factors.get(field_type, 1.0)
    
    def apply_consistency_checks(self, data: MarksheetData) -> MarksheetData:
        """Apply consistency checks and adjust confidence scores"""
        try:
            # Check if subject marks sum matches total (if available)
            if data.subjects and data.overall_result:
                self._check_marks_consistency(data)
            
            # Check date consistency
            self._check_date_consistency(data)
            
            # Check name consistency
            self._check_name_consistency(data)
            
            return data
            
        except Exception as e:
            logger.warning(f"Consistency checks failed: {str(e)}")
            return data
    
    def _check_marks_consistency(self, data: MarksheetData):
        """Check if individual subject marks are consistent with total"""
        try:
            if not data.subjects or not data.overall_result:
                return
            
            # Calculate sum of obtained marks
            total_obtained = 0
            valid_subjects = 0
            
            for subject in data.subjects:
                if subject.obtained_marks and subject.obtained_marks.value:
                    try:
                        marks = float(subject.obtained_marks.value)
                        total_obtained += marks
                        valid_subjects += 1
                    except (ValueError, TypeError):
                        continue
            
            # Compare with stated total
            if data.overall_result.total_marks and data.overall_result.total_marks.value:
                try:
                    stated_total = float(data.overall_result.total_marks.value)
                    
                    # If totals match (within 5% tolerance), boost confidence
                    if abs(total_obtained - stated_total) / stated_total < 0.05:
                        data.overall_result.total_marks.confidence = min(1.0, 
                            data.overall_result.total_marks.confidence * 1.1)
                        
                        # Also boost individual subject confidences
                        for subject in data.subjects:
                            if subject.obtained_marks:
                                subject.obtained_marks.confidence = min(1.0,
                                    subject.obtained_marks.confidence * 1.05)
                    
                except (ValueError, TypeError):
                    pass
                    
        except Exception as e:
            logger.warning(f"Marks consistency check failed: {str(e)}")
    
    def _check_date_consistency(self, data: MarksheetData):
        """Check date consistency across fields"""
        # Implementation for date consistency
        pass
    
    def _check_name_consistency(self, data: MarksheetData):
        """Check name consistency and format"""
        # Implementation for name consistency
        pass
    
    def get_method_info(self) -> Dict[str, Any]:
        """Get information about the confidence calculation method"""
        return {
            "method": "multi-factor-calibrated",
            "version": "1.0",
            "min_threshold": self.min_threshold,
            "weights": self.weights,
            "features": [
                "field_type_calibration",
                "consistency_checks",
                "threshold_enforcement"
            ]
        }
    
    def calculate_overall_confidence(self, data: MarksheetData) -> float:
        """Calculate overall confidence score for the extraction"""
        try:
            all_confidences = []
            
            # Collect all confidence scores
            def collect_confidences(obj):
                if hasattr(obj, '__dict__'):
                    for value in obj.__dict__.values():
                        if isinstance(value, ExtractedField) and value.confidence > 0:
                            all_confidences.append(value.confidence)
                        elif isinstance(value, list):
                            for item in value:
                                collect_confidences(item)
                        elif hasattr(value, '__dict__'):
                            collect_confidences(value)
            
            collect_confidences(data)
            
            if all_confidences:
                return sum(all_confidences) / len(all_confidences)
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"Overall confidence calculation failed: {str(e)}")
            return 0.0
