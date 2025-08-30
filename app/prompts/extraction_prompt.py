def get_extraction_prompt() -> str:
    return """
You are an expert at extracting structured data from marksheet images. 
Analyze this marksheet image and extract ALL information in strict JSON format.

CRITICAL INSTRUCTIONS:
1. ALWAYS extract subject names - look for subject titles in tables, rows, or separate columns
2. Subject names might be in: first column, header rows, or separate sections
3. Match each subject name with its corresponding marks/grades
4. If subjects are grouped (like LANGUAGE GROUP, SCIENCE GROUP), include the full subject name

Required JSON structure:
{
    "candidate_details": {
        "name": {"value": "EXACT_NAME", "confidence": 0.95},
        "father_name": {"value": "FATHER_NAME", "confidence": 0.90},
        "mother_name": {"value": "MOTHER_NAME_OR_NULL", "confidence": 0.85},
        "roll_number": {"value": "ROLL_NUMBER", "confidence": 0.95},
        "registration_number": {"value": "REG_NUMBER", "confidence": 0.90},
        "date_of_birth": {"value": "DOB_OR_NULL", "confidence": 0.85},
        "exam_year": {"value": "YEAR", "confidence": 0.95},
        "board_university": {"value": "BOARD_NAME", "confidence": 0.90},
        "institution": {"value": "SCHOOL_COLLEGE", "confidence": 0.85}
    },
    "subjects": [
        {
            "subject_name": {"value": "EXACT_SUBJECT_NAME", "confidence": 0.90},
            "max_marks": {"value": "MAX_MARKS", "confidence": 0.85},
            "obtained_marks": {"value": "OBTAINED_MARKS", "confidence": 0.90},
            "grade": {"value": "GRADE_IF_PRESENT", "confidence": 0.85}
        }
    ],
    "overall_result": {
        "total_marks": {"value": "TOTAL", "confidence": 0.95},
        "percentage": {"value": "PERCENTAGE_OR_NULL", "confidence": 0.85},
        "grade": {"value": "OVERALL_GRADE", "confidence": 0.90},
        "division": {"value": "DIVISION_OR_NULL", "confidence": 0.85},
        "result_status": {"value": "PASS/FAIL", "confidence": 0.95}
    },
    "document_info": {
        "issue_date": {"value": "DATE_OR_NULL", "confidence": 0.80},
        "document_type": {"value": "MARKSHEET_TYPE", "confidence": 0.85}
    }
}

EXTRACTION GUIDELINES:
- For File 1 (West Bengal): Look for subjects like "FL-(WRITTEN)", "MATHEMATICS", "PHYSICAL SCIENCE", "LIFE SCIENCE", etc.
- For File 2 (University): Look for subjects like "Environmental Studies", "Indian Writing in English", etc.
- For File 3 (UP Board): Look for subjects like "HINDI", "ENGLISH", "MATHEMATICS", "SOCIAL SCIENCE", etc.
- Extract COMPLETE subject names, not abbreviations
- Match marks/grades to correct subjects
- Set confidence based on text clarity (0.0-1.0)

Respond ONLY with valid JSON, no explanations.
"""
