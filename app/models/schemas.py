from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ExtractedField(BaseModel):
    """Base model for extracted fields with confidence"""
    value: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    bounding_box: Optional[Dict[str, float]] = None  # {x, y, width, height}

class CandidateDetails(BaseModel):
    """Candidate information from marksheet"""
    name: ExtractedField
    father_name: Optional[ExtractedField] = None
    mother_name: Optional[ExtractedField] = None
    roll_number: Optional[ExtractedField] = None
    registration_number: Optional[ExtractedField] = None
    date_of_birth: Optional[ExtractedField] = None
    exam_year: Optional[ExtractedField] = None
    board_university: Optional[ExtractedField] = None
    institution: Optional[ExtractedField] = None

class SubjectMark(BaseModel):
    """Individual subject marks information"""
    subject_name: ExtractedField
    max_marks: Optional[ExtractedField] = None
    max_credits: Optional[ExtractedField] = None
    obtained_marks: Optional[ExtractedField] = None
    obtained_credits: Optional[ExtractedField] = None
    grade: Optional[ExtractedField] = None
    remarks: Optional[ExtractedField] = None

class OverallResult(BaseModel):
    """Overall result information"""
    total_marks: Optional[ExtractedField] = None
    total_credits: Optional[ExtractedField] = None
    percentage: Optional[ExtractedField] = None
    cgpa: Optional[ExtractedField] = None
    grade: Optional[ExtractedField] = None
    division: Optional[ExtractedField] = None
    result_status: Optional[ExtractedField] = None  # Pass/Fail/etc

class DocumentInfo(BaseModel):
    """Document metadata"""
    issue_date: Optional[ExtractedField] = None
    issue_place: Optional[ExtractedField] = None
    document_type: Optional[ExtractedField] = None
    academic_session: Optional[ExtractedField] = None

class MarksheetData(BaseModel):
    """Complete marksheet extracted data"""
    candidate_details: CandidateDetails
    subjects: List[SubjectMark] = []
    overall_result: OverallResult
    document_info: DocumentInfo

class MarksheetResponse(BaseModel):
    """API response model"""
    success: bool = True
    message: str = "Data extracted successfully"
    data: Optional[MarksheetData] = None
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BatchRequest(BaseModel):
    """Batch processing request"""
    files: List[str] = Field(..., description="List of file paths or URLs")
    
class BatchResponse(BaseModel):
    """Batch processing response"""
    success: bool = True
    results: List[MarksheetResponse] = []
    failed_files: List[Dict[str, str]] = []
    total_processed: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)