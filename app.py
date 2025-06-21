# Universal Document Intelligence Platform
# Built on top of the proven mortgage analyzer foundation
# PRESERVES ALL EXISTING FUNCTIONALITY

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import re
import json
from datetime import datetime

# Free document processing libraries - with graceful fallback
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# ===== ORIGINAL MORTGAGE ANALYZER CODE (PRESERVED) =====
# Global storage for analysis rules and session data
analysis_rules = [
    {"pattern": "MORTGAGE|DEED OF TRUST", "type": "contains", "label": "Mortgage"},
    {"pattern": "PROMISSORY NOTE", "type": "contains", "label": "Promissory Note"},
    {"pattern": "CLOSING INSTRUCTIONS", "type": "contains", "label": "Lenders Closing Instructions Guaranty"},
    {"pattern": "ANTI.?COERCION", "type": "contains", "label": "Statement of Anti Coercion Florida"},
    {"pattern": "POWER OF ATTORNEY", "type": "contains", "label": "Correction Agreement and Limited Power of Attorney"},
    {"pattern": "ACKNOWLEDGMENT", "type": "contains", "label": "All Purpose Acknowledgment"},
    {"pattern": "FLOOD HAZARD", "type": "contains", "label": "Flood Hazard Determination"},
    {"pattern": "AUTOMATIC PAYMENT", "type": "contains", "label": "Automatic Payments Authorization"},
    {"pattern": "TAX RECORD", "type": "contains", "label": "Tax Record Information"}
]

lender_requirements = {}

# ===== NEW UNIVERSAL PLATFORM FEATURES =====

# Industry Templates - NEW FEATURE
INDUSTRY_TEMPLATES = {
    "mortgage": {
        "name": "Mortgage & Real Estate",
        "icon": "🏠",
        "description": "Loan processing, closing documents, property records",
        "document_types": [
            "Mortgage", "Promissory Note", "Closing Instructions", "Settlement Statement",
            "Property Deed", "Title Insurance", "Appraisal Report", "Credit Report"
        ],
        "rules": analysis_rules  # Use existing mortgage rules
    },
    "legal": {
        "name": "Legal & Law Firms", 
        "icon": "⚖️",
        "description": "Contracts, agreements, case files, legal documents",
        "document_types": [
            "Contract Agreement", "Non-Disclosure Agreement", "Employment Contract",
            "Lease Agreement", "Purchase Agreement", "Legal Brief", "Court Filing",
            "Power of Attorney", "Will & Testament", "Corporate Bylaws"
        ],
        "rules": [
            {"pattern": "CONTRACT|AGREEMENT", "type": "contains", "label": "Contract Agreement"},
            {"pattern": "NON.?DISCLOSURE|NDA", "type": "contains", "label": "Non-Disclosure Agreement"},
            {"pattern": "EMPLOYMENT", "type": "contains", "label": "Employment Contract"},
            {"pattern": "LEASE", "type": "contains", "label": "Lease Agreement"},
            {"pattern": "PURCHASE", "type": "contains", "label": "Purchase Agreement"},
            {"pattern": "BRIEF", "type": "contains", "label": "Legal Brief"},
            {"pattern": "COURT|FILING", "type": "contains", "label": "Court Filing"},
            {"pattern": "POWER OF ATTORNEY", "type": "contains", "label": "Power of Attorney"},
            {"pattern": "WILL|TESTAMENT", "type": "contains", "label": "Will & Testament"},
            {"pattern": "BYLAWS", "type": "contains", "label": "Corporate Bylaws"}
        ]
    },
    "healthcare": {
        "name": "Healthcare & Medical",
        "icon": "🏥", 
        "description": "Medical records, insurance claims, patient documents",
        "document_types": [
            "Medical Record", "Insurance Claim", "Patient Consent", "Lab Report",
            "Prescription", "Treatment Plan", "Discharge Summary", "Medical History",
            "Insurance Authorization", "HIPAA Form"
        ],
        "rules": [
            {"pattern": "MEDICAL RECORD|PATIENT RECORD", "type": "contains", "label": "Medical Record"},
            {"pattern": "INSURANCE CLAIM|CLAIM FORM", "type": "contains", "label": "Insurance Claim"},
            {"pattern": "PATIENT CONSENT|INFORMED CONSENT", "type": "contains", "label": "Patient Consent"},
            {"pattern": "LAB REPORT|LABORATORY", "type": "contains", "label": "Lab Report"},
            {"pattern": "PRESCRIPTION|RX", "type": "contains", "label": "Prescription"},
            {"pattern": "TREATMENT PLAN", "type": "contains", "label": "Treatment Plan"},
            {"pattern": "DISCHARGE SUMMARY", "type": "contains", "label": "Discharge Summary"},
            {"pattern": "MEDICAL HISTORY", "type": "contains", "label": "Medical History"},
            {"pattern": "AUTHORIZATION", "type": "contains", "label": "Insurance Authorization"},
            {"pattern": "HIPAA", "type": "contains", "label": "HIPAA Form"}
        ]
    },
    "financial": {
        "name": "Financial Services",
        "icon": "💰",
        "description": "Banking, investments, insurance, financial documents", 
        "document_types": [
            "Bank Statement", "Investment Report", "Insurance Policy", "Tax Document",
            "Financial Statement", "Credit Report", "Loan Application", "Account Agreement",
            "Compliance Report", "Audit Report"
        ],
        "rules": [
            {"pattern": "BANK STATEMENT|ACCOUNT STATEMENT", "type": "contains", "label": "Bank Statement"},
            {"pattern": "INVESTMENT|PORTFOLIO", "type": "contains", "label": "Investment Report"},
            {"pattern": "INSURANCE POLICY|POLICY", "type": "contains", "label": "Insurance Policy"},
            {"pattern": "TAX|1099|W-2|1040", "type": "contains", "label": "Tax Document"},
            {"pattern": "FINANCIAL STATEMENT", "type": "contains", "label": "Financial Statement"},
            {"pattern": "CREDIT REPORT|CREDIT SCORE", "type": "contains", "label": "Credit Report"},
            {"pattern": "LOAN APPLICATION", "type": "contains", "label": "Loan Application"},
            {"pattern": "ACCOUNT AGREEMENT", "type": "contains", "label": "Account Agreement"},
            {"pattern": "COMPLIANCE", "type": "contains", "label": "Compliance Report"},
            {"pattern": "AUDIT", "type": "contains", "label": "Audit Report"}
        ]
    },
    "hr": {
        "name": "Human Resources",
        "icon": "👥",
        "description": "Employee records, resumes, HR documents",
        "document_types": [
            "Resume", "Job Application", "Employee Handbook", "Performance Review",
            "Employment Contract", "Benefits Enrollment", "Time Sheet", "Payroll Record",
            "Training Certificate", "Background Check"
        ],
        "rules": [
            {"pattern": "RESUME|CV|CURRICULUM VITAE", "type": "contains", "label": "Resume"},
            {"pattern": "JOB APPLICATION|APPLICATION", "type": "contains", "label": "Job Application"},
            {"pattern": "EMPLOYEE HANDBOOK|HANDBOOK", "type": "contains", "label": "Employee Handbook"},
            {"pattern": "PERFORMANCE REVIEW|EVALUATION", "type": "contains", "label": "Performance Review"},
            {"pattern": "EMPLOYMENT CONTRACT", "type": "contains", "label": "Employment Contract"},
            {"pattern": "BENEFITS|ENROLLMENT", "type": "contains", "label": "Benefits Enrollment"},
            {"pattern": "TIME SHEET|TIMESHEET", "type": "contains", "label": "Time Sheet"},
            {"pattern": "PAYROLL", "type": "contains", "label": "Payroll Record"},
            {"pattern": "TRAINING|CERTIFICATE", "type": "contains", "label": "Training Certificate"},
            {"pattern": "BACKGROUND CHECK", "type": "contains", "label": "Background Check"}
        ]
    }
}

# Universal Document Processor - NEW FEATURE
class UniversalDocumentProcessor:
    def __init__(self):
        self.supported_formats = {}
        
        # Add supported formats based on available libraries
        if PDFPLUMBER_AVAILABLE:
            self.supported_formats['.pdf'] = self._process_pdf
        if DOCX_AVAILABLE:
            self.supported_formats['.docx'] = self._process_docx
        if OPENPYXL_AVAILABLE:
            self.supported_formats['.xlsx'] = self._process_xlsx
        if OCR_AVAILABLE:
            self.supported_formats['.png'] = self._process_image
            self.supported_formats['.jpg'] = self._process_image
            self.supported_formats['.jpeg'] = self._process_image
        
        # Text files are always supported
        self.supported_formats['.txt'] = self._process_txt
    
    def process_document(self, file_path, filename, industry="mortgage"):
        """Process document with industry-specific analysis"""
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in self.supported_formats:
            return {
                'success': False,
                'error': f'Unsupported file format: {file_ext}',
                'text': '',
                'metadata': {},
                'industry': industry
            }
        
        try:
            result = self.supported_formats[file_ext](file_path, filename)
            
            # Add industry-specific analysis
            if result.get('success') and result.get('text'):
                result['text'] = clean_text(result['text'])
                result['industry'] = industry
                result['industry_analysis'] = self._analyze_for_industry(result['text'], industry)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}',
                'text': '',
                'metadata': {},
                'industry': industry
            }
    
    def _analyze_for_industry(self, text, industry):
        """Analyze document using industry-specific rules"""
        if industry not in INDUSTRY_TEMPLATES:
            industry = "mortgage"  # Default fallback
        
        template = INDUSTRY_TEMPLATES[industry]
        rules = template.get('rules', [])
        
        identified_sections = []
        
        for rule in rules:
            pattern = rule['pattern']
            label = rule['label']
            
            if rule['type'] == 'contains':
                if re.search(pattern, text, re.IGNORECASE):
                    confidence = len(re.findall(pattern, text, re.IGNORECASE)) * 10
                    confidence = min(confidence, 95)  # Cap at 95%
                    
                    identified_sections.append({
                        'section': label,
                        'confidence': confidence,
                        'pattern_matched': pattern
                    })
        
        return {
            'industry': industry,
            'template': template['name'],
            'sections_found': len(identified_sections),
            'sections': identified_sections
        }
    
    def _process_pdf(self, file_path, filename):
        """Enhanced PDF processing with pdfplumber"""
        if not PDFPLUMBER_AVAILABLE:
            return {'success': False, 'error': 'PDF processing not available', 'text': '', 'metadata': {}}
        
        try:
            with pdfplumber.open(file_path) as pdf:
                text_content = ""
                page_count = len(pdf.pages)
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                
                return {
                    'success': True,
                    'text': text_content,
                    'metadata': {
                        'page_count': page_count,
                        'file_size': os.path.getsize(file_path),
                        'processing_method': 'pdfplumber'
                    }
                }
        except Exception as e:
            return {'success': False, 'error': str(e), 'text': '', 'metadata': {}}
    
    def _process_docx(self, file_path, filename):
        """Process Word documents"""
        if not DOCX_AVAILABLE:
            return {'success': False, 'error': 'Word processing not available', 'text': '', 'metadata': {}}
        
        try:
            doc = docx.Document(file_path)
            text_content = ""
            
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            return {
                'success': True,
                'text': text_content,
                'metadata': {
                    'paragraph_count': len(doc.paragraphs),
                    'file_size': os.path.getsize(file_path),
                    'processing_method': 'python-docx'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'text': '', 'metadata': {}}
    
    def _process_xlsx(self, file_path, filename):
        """Process Excel files"""
        if not OPENPYXL_AVAILABLE:
            return {'success': False, 'error': 'Excel processing not available', 'text': '', 'metadata': {}}
        
        try:
            workbook = load_workbook(file_path)
            text_content = ""
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                text_content += f"Sheet: {sheet_name}\n"
                
                for row in sheet.iter_rows(values_only=True):
                    row_text = "\t".join([str(cell) if cell is not None else "" for cell in row])
                    text_content += row_text + "\n"
                
                text_content += "\n"
            
            return {
                'success': True,
                'text': text_content,
                'metadata': {
                    'sheet_count': len(workbook.sheetnames),
                    'file_size': os.path.getsize(file_path),
                    'processing_method': 'openpyxl'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'text': '', 'metadata': {}}
    
    def _process_image(self, file_path, filename):
        """Process images with OCR"""
        if not OCR_AVAILABLE:
            return {'success': False, 'error': 'OCR processing not available', 'text': '', 'metadata': {}}
        
        try:
            image = Image.open(file_path)
            width, height = image.size
            
            # Preprocess image for better OCR
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            text_content = pytesseract.image_to_string(image)
            
            return {
                'success': True,
                'text': text_content,
                'metadata': {
                    'image_size': f"{width}x{height}",
                    'file_size': os.path.getsize(file_path),
                    'processing_method': 'pytesseract-ocr'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'text': '', 'metadata': {}}
    
    def _process_txt(self, file_path, filename):
        """Process text files"""
        try:
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        text_content = file.read()
                    
                    return {
                        'success': True,
                        'text': text_content,
                        'metadata': {
                            'encoding': encoding,
                            'file_size': os.path.getsize(file_path),
                            'processing_method': 'text-reader'
                        }
                    }
                except UnicodeDecodeError:
                    continue
            
            return {'success': False, 'error': 'Could not decode text file', 'text': '', 'metadata': {}}
        except Exception as e:
            return {'success': False, 'error': str(e), 'text': '', 'metadata': {}}

# Initialize the universal processor
universal_processor = UniversalDocumentProcessor()

# ===== ORIGINAL MORTGAGE FUNCTIONS (PRESERVED) =====

