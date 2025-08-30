# Marksheet Extraction API

**AI-powered API for extracting structured data from marksheet images and PDFs using Large Language Models (LLM)**

🚀 Extract candidate details, academic results, and document metadata from marksheet scans with high accuracy using GPT-4 Vision or Google Gemini.

---

## 🚀 Features

- **Multi-format Support**: JPG, PNG, and PDF files
- **LLM-Powered Extraction**: Uses OpenAI GPT-4 Vision or Google Gemini for intelligent parsing
- **Confidence Scores**: Each extracted field includes accuracy confidence (0.0–1.0)
- **Structured Output**: Consistent JSON schema for all responses
- **Batch Processing**: Process multiple files in a single request
- **API Authentication**: Optional API key protection
- **Error Handling**: Comprehensive validation and error messages
- **Auto-documentation**: Built-in Swagger UI at `/docs`

---

## 📋 Extracted Data

The API extracts the following structured information:

### Candidate Details
- Name, Father’s/Mother’s Name  
- Roll Number, Registration Number  
- Date of Birth, Exam Year  
- Board/University, Institution  

### Academic Information
- Subject-wise marks and credits  
- Maximum marks per subject  
- Grades and remarks  
- Overall percentage or CGPA  
- Total marks and result status (PASS/FAIL)

### Document Metadata
- Issue date and place  
- Document type (e.g., Marksheet, Transcript)  
- Academic session  

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- OpenAI API Key **or** Google Gemini API Key

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd marksheet-extraction-api
