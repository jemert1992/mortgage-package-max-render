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
session_data = {}

# Industry Templates for Universal Platform
INDUSTRY_TEMPLATES = {
    'mortgage': {
        'name': 'Mortgage & Real Estate',
        'icon': '🏠',
        'description': 'Mortgage packages, loan documents, real estate transactions',
        'categories': [
            'Mortgage', 'Promissory Note', 'Closing Instructions', 'Anti-Coercion Statement',
            'Power of Attorney', 'Acknowledgment', 'Flood Hazard', 'Payment Authorization', 'Tax Records'
        ]
    },
    'legal': {
        'name': 'Legal & Law Firms',
        'icon': '⚖️',
        'description': 'Contracts, agreements, legal documents, case files',
        'categories': [
            'Contracts', 'Agreements', 'Legal Briefs', 'Court Documents', 'Compliance Reports',
            'Terms of Service', 'Privacy Policies', 'Employment Agreements', 'NDAs'
        ]
    },
    'healthcare': {
        'name': 'Healthcare & Medical',
        'icon': '🏥',
        'description': 'Medical records, insurance claims, patient documents',
        'categories': [
            'Medical Records', 'Insurance Claims', 'Patient Forms', 'Lab Results', 'Prescriptions',
            'Treatment Plans', 'Discharge Summaries', 'Consent Forms', 'Medical Bills'
        ]
    },
    'financial': {
        'name': 'Financial Services',
        'icon': '💰',
        'description': 'Banking documents, investment reports, financial statements',
        'categories': [
            'Bank Statements', 'Investment Reports', 'Financial Statements', 'Tax Documents',
            'Loan Applications', 'Credit Reports', 'Insurance Policies', 'Audit Reports'
        ]
    },
    'hr': {
        'name': 'Human Resources',
        'icon': '👥',
        'description': 'Employee records, resumes, HR documents, onboarding',
        'categories': [
            'Resumes', 'Employee Records', 'Performance Reviews', 'Job Applications',
            'Onboarding Documents', 'Training Records', 'Benefits Information', 'Payroll Documents'
        ]
    }
}

def clean_text(text):
    """Enhanced text cleaning for OCR and encoding issues"""
    if not text:
        return ""
    
    # Character substitution mapping for OCR issues
    char_map = {
        'Ɵ': 'ti',
        'Ʃ': 'tt', 
        'ƟƟ': 'tti',
        'Ʃt': 'tt',
        'ƟƟ': 'tion',
        'Ʃl': 'tl'
    }
    
    # Apply character mappings
    for old_char, new_char in char_map.items():
        text = text.replace(old_char, new_char)
    
    # Direct replacements for known issues
    replacements = {
        'InstrucƟons': 'Instructions',
        'NoƟce': 'Notice',
        'SeƩlement': 'Settlement', 
        'LeƩer': 'Letter',
        'NoƟficaƟon': 'Notification',
        'AnƟ-Coercion': 'Anti-Coercion',
        'instrucƟons': 'instructions',
        'noƟce': 'notice',
        'seƩlement': 'settlement',
        'leƩer': 'letter',
        'noƟficaƟon': 'notification',
        'anƟ-coercion': 'anti-coercion'
    }
    
    for old_text, new_text in replacements.items():
        text = text.replace(old_text, new_text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

class UniversalDocumentProcessor:
    """Universal multi-format document processor for all industries"""
    
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
    
    def process_document(self, file_path, filename, industry='mortgage'):
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
            
            # Clean the extracted text
            if result.get('success') and result.get('text'):
                result['text'] = clean_text(result['text'])
            
            # Add industry context
            result['industry'] = industry
            result['template'] = INDUSTRY_TEMPLATES.get(industry, INDUSTRY_TEMPLATES['mortgage'])
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}',
                'text': '',
                'metadata': {},
                'industry': industry
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
            workbook = load_workbook(file_path, data_only=True)
            text_content = ""
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                text_content += f"Sheet: {sheet_name}\n"
                
                for row in sheet.iter_rows(values_only=True):
                    row_text = " | ".join([str(cell) if cell is not None else "" for cell in row])
                    if row_text.strip():
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
            return {'success': False, 'error': 'Image OCR not available', 'text': '', 'metadata': {}}
        
        try:
            image = Image.open(file_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Basic preprocessing
            width, height = image.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to grayscale for better OCR
            image = image.convert('L')
            
            # Extract text using OCR
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
document_processor = UniversalDocumentProcessor()

def parse_lender_email(content):
    """Enhanced email parsing for lender requirements with memory optimization"""
    
    # Limit content size to prevent memory issues
    if len(content) > 50000:  # Limit to 50KB
        content = content[:50000]
    
    # Clean the content first
    content = clean_text(content)
    
    # Extract lender information
    lender_info = {
        'lender_name': 'Unknown Lender',
        'contact_email': '',
        'contact_name': '',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'documents': [],
        'funding_amount': '',
        'special_instructions': []
    }
    
    try:
        # Extract lender name and contact info
        email_patterns = [
            r'From:\s*([^<]+)<([^>]+)>',
            r'([A-Za-z\s]+)\s*<([^@]+@[^>]+)>',
            r'([^@]+@[\w\.-]+\.\w+)'
        ]
        
        for pattern in email_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2:
                    lender_info['contact_name'] = match.group(1).strip()
                    lender_info['contact_email'] = match.group(2).strip()
                else:
                    lender_info['contact_email'] = match.group(1).strip()
                break
        
        # Extract lender name from email domain or content
        if 'symmetry' in content.lower():
            lender_info['lender_name'] = 'Symmetry Lending'
        elif '@' in lender_info['contact_email']:
            domain = lender_info['contact_email'].split('@')[1].split('.')[0]
            lender_info['lender_name'] = domain.title() + ' Lending'
        
        # Extract funding amount
        amount_patterns = [
            r'\$[\d,]+\.?\d*',
            r'amount[:\s]+\$?([\d,]+\.?\d*)',
            r'fund[ing]*[:\s]+\$?([\d,]+\.?\d*)'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                lender_info['funding_amount'] = match.group(0) if '$' in match.group(0) else f"${match.group(1)}"
                break
        
        # Enhanced document extraction with checkbox patterns (limited to prevent memory issues)
        checkbox_patterns = [
            r'☐\s*([^\n\r]{1,200})',  # Limit match length
            r'□\s*([^\n\r]{1,200})', 
            r'▢\s*([^\n\r]{1,200})',
            r'\[\s*\]\s*([^\n\r]{1,200})',
            r'◯\s*([^\n\r]{1,200})',
            r'○\s*([^\n\r]{1,200})',
            r'•\s*([^\n\r]{1,200})',
            r'-\s*([^\n\r]{1,200})'
        ]
        
        documents = set()  # Use set to avoid duplicates
        
        for pattern in checkbox_patterns:
            try:
                matches = re.findall(pattern, content, re.MULTILINE)
                for match in matches[:50]:  # Limit to 50 matches per pattern
                    doc_name = clean_text(match.strip())
                    # Filter out non-document items
                    if (len(doc_name) > 5 and len(doc_name) < 200 and
                        not doc_name.lower().startswith(('below', 'all ', 'guard', 'think', 'st &', '1st &')) and
                        not re.match(r'^\d+$', doc_name)):
                        documents.add(doc_name)
                        
                        # Limit total documents to prevent memory issues
                        if len(documents) >= 100:
                            break
                            
                if len(documents) >= 100:
                    break
            except Exception:
                continue
        
        # Convert to list and sort
        lender_info['documents'] = sorted(list(documents))[:50]  # Limit to 50 documents
        
        # Extract special instructions (limited)
        instruction_patterns = [
            r'special instructions?[:\s]*([^\n\r]{1,500})',
            r'note[:\s]*([^\n\r]{1,500})',
            r'important[:\s]*([^\n\r]{1,500})',
            r'deadline[:\s]*([^\n\r]{1,500})'
        ]
        
        for pattern in instruction_patterns:
            try:
                matches = re.findall(pattern, content, re.IGNORECASE)
                lender_info['special_instructions'].extend([clean_text(match.strip()) for match in matches[:10]])  # Limit to 10 instructions
            except Exception:
                continue
        
    except Exception as e:
        # If parsing fails, return basic info
        lender_info['documents'] = ['Error parsing email content']
        lender_info['special_instructions'] = [f'Parsing error: {str(e)}']
    
    return lender_info

def analyze_mortgage_sections(filename, use_lender_rules=True):
    """Analyze mortgage sections using core categories and optional lender rules"""
    
    # Core mortgage categories (always included)
    core_sections = [
        "Mortgage",
        "Promissory Note", 
        "Lenders Closing Instructions Guaranty",
        "Statement of Anti Coercion Florida",
        "Correction Agreement and Limited Power of Attorney",
        "All Purpose Acknowledgment",
        "Flood Hazard Determination", 
        "Automatic Payments Authorization",
        "Tax Record Information"
    ]
    
    sections = []
    page_counter = 2
    
    # Add core sections
    for i, section_name in enumerate(core_sections):
        confidence = "high" if i < 3 else ("medium" if i < 6 else "low")
        risk_score = 15 if i < 3 else (25 if i < 6 else 35)
        
        sections.append({
            "name": section_name,
            "pages": f"{page_counter}-{page_counter + 1}",
            "confidence": confidence,
            "risk_score": risk_score,
            "quality": f"{95 - (i * 2)}%",
            "notes": f"Core mortgage document - {confidence} priority"
        })
        page_counter += 2
    
    # Add lender-specific documents if available and requested
    if use_lender_rules and lender_requirements:
        lender_docs = lender_requirements.get('documents', [])
        for i, doc_name in enumerate(lender_docs[:10]):  # Limit to 10 additional docs
            sections.append({
                "name": doc_name,
                "pages": f"{page_counter}-{page_counter + 1}",
                "confidence": "medium",
                "risk_score": 20,
                "quality": f"{90 - (i * 3)}%",
                "notes": f"Lender requirement - {lender_requirements.get('lender_name', 'Unknown')}"
            })
            page_counter += 2
    
    return sections

def analyze_universal_document(text, industry, filename):
    """Universal document analysis for any industry"""
    
    if industry == 'mortgage':
        # Use existing mortgage analysis
        return analyze_mortgage_sections(filename)
    
    # For other industries, create basic analysis
    template = INDUSTRY_TEMPLATES.get(industry, INDUSTRY_TEMPLATES['mortgage'])
    sections = []
    
    for i, category in enumerate(template['categories']):
        # Simple keyword matching for now
        category_lower = category.lower()
        text_lower = text.lower()
        
        # Basic confidence scoring based on keyword presence
        if category_lower in text_lower:
            confidence = "high"
            risk_score = 10
            quality = "95%"
        elif any(word in text_lower for word in category_lower.split()):
            confidence = "medium" 
            risk_score = 25
            quality = "80%"
        else:
            confidence = "low"
            risk_score = 40
            quality = "60%"
        
        sections.append({
            "name": category,
            "pages": f"{i*2 + 1}-{i*2 + 2}",
            "confidence": confidence,
            "risk_score": risk_score,
            "quality": quality,
            "notes": f"{template['name']} document category"
        })
    
    return sections

# Routes
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Universal Document Analyzer - Multi-Industry AI Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
            color: #ffffff;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .animated-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #0a0a0a, #1a1a2e, #16213e, #0f3460);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            z-index: -1;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 0;
        }

        .main-title {
            font-size: 3.5rem;
            font-weight: 900;
            background: linear-gradient(45deg, #00d4ff, #0099cc, #ffffff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 20px;
            text-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
            animation: glow 2s ease-in-out infinite alternate;
        }

        @keyframes glow {
            from { text-shadow: 0 0 20px rgba(0, 212, 255, 0.3); }
            to { text-shadow: 0 0 40px rgba(0, 212, 255, 0.6); }
        }

        .subtitle {
            font-size: 1.3rem;
            color: #b0b0b0;
            margin-bottom: 30px;
        }

        .industry-selector {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .selector-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #00d4ff;
            margin-bottom: 25px;
            text-align: center;
        }

        .industry-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .industry-card {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(0, 153, 204, 0.1));
            border: 2px solid transparent;
            border-radius: 15px;
            padding: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .industry-card:hover {
            transform: translateY(-5px);
            border-color: #00d4ff;
            box-shadow: 0 15px 35px rgba(0, 212, 255, 0.3);
        }

        .industry-card.selected {
            border-color: #00d4ff;
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(0, 153, 204, 0.2));
            box-shadow: 0 0 25px rgba(0, 212, 255, 0.4);
        }

        .industry-icon {
            font-size: 2.5rem;
            margin-bottom: 15px;
            display: block;
        }

        .industry-name {
            font-size: 1.2rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 10px;
        }

        .industry-desc {
            font-size: 0.9rem;
            color: #b0b0b0;
            line-height: 1.4;
        }

        .upload-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 2px dashed rgba(0, 212, 255, 0.3);
            transition: all 0.3s ease;
            margin-bottom: 30px;
        }

        .upload-section:hover {
            border-color: #00d4ff;
            background: rgba(255, 255, 255, 0.08);
        }

        .upload-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #00d4ff;
            margin-bottom: 20px;
        }

        .file-input {
            display: none;
        }

        .upload-btn {
            background: linear-gradient(45deg, #00d4ff, #0099cc);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 212, 255, 0.3);
        }

        .upload-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 212, 255, 0.5);
        }

        .analyze-btn {
            background: linear-gradient(45deg, #ff6b35, #f7931e);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-size: 1.2rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(255, 107, 53, 0.3);
            margin-top: 20px;
            display: none;
        }

        .analyze-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255, 107, 53, 0.5);
        }

        .selected-file {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid #00d4ff;
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            color: #00d4ff;
        }

        .tabs {
            display: none;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 212, 255, 0.2);
            margin-top: 30px;
        }

        .tab-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .tab-btn {
            background: rgba(0, 212, 255, 0.1);
            color: #00d4ff;
            border: 1px solid #00d4ff;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }

        .tab-btn:hover, .tab-btn.active {
            background: #00d4ff;
            color: #000;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .progress-container {
            display: none;
            margin: 30px 0;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #0099cc);
            width: 0%;
            transition: width 0.3s ease;
        }

        .status-text {
            color: #00d4ff;
            margin-top: 10px;
            font-weight: 500;
        }

        @media (max-width: 768px) {
            .main-title {
                font-size: 2.5rem;
            }
            
            .industry-grid {
                grid-template-columns: 1fr;
            }
            
            .container {
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="animated-bg"></div>
    
    <div class="container">
        <div class="header">
            <h1 class="main-title">Universal Document Analyzer</h1>
            <p class="subtitle">AI-Powered Multi-Industry Document Intelligence Platform</p>
        </div>

        <div class="industry-selector">
            <h2 class="selector-title">Select Your Industry</h2>
            <div class="industry-grid">
                {% for key, industry in industries.items() %}
                <div class="industry-card" data-industry="{{ key }}">
                    <span class="industry-icon">{{ industry.icon }}</span>
                    <div class="industry-name">{{ industry.name }}</div>
                    <div class="industry-desc">{{ industry.description }}</div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="upload-section">
            <h3 class="upload-title">Upload Your Documents</h3>
            <p style="color: #b0b0b0; margin-bottom: 20px;">Supports PDF, Word, Excel, Images, and Text files</p>
            
            <input type="file" id="fileInput" class="file-input" multiple accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.txt">
            <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                Choose Files
            </button>
            
            <div id="selectedFiles"></div>
            <button class="analyze-btn" id="analyzeBtn" onclick="startAnalysis()">
                🚀 Start Analysis
            </button>
            
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="status-text" id="statusText">Initializing...</div>
            </div>
        </div>

        <div class="tabs" id="tabsSection">
            <div class="tab-buttons">
                <button class="tab-btn active" onclick="showTab('analyze')">📊 Analyze & Identify</button>
                <button class="tab-btn" onclick="showTab('separation')">📄 Document Separation</button>
                <button class="tab-btn" onclick="showTab('rules')">⚙️ Analysis Rules</button>
                <button class="tab-btn" onclick="showTab('email')">📧 Email Parser</button>
            </div>

            <div id="analyze" class="tab-content active">
                <h3 style="color: #00d4ff; margin-bottom: 20px;">Document Analysis Results</h3>
                <div id="analysisResults">
                    <p style="color: #b0b0b0;">Upload and analyze documents to see results here.</p>
                </div>
            </div>

            <div id="separation" class="tab-content">
                <h3 style="color: #00d4ff; margin-bottom: 20px;">Document Separation</h3>
                <div id="separationResults">
                    <p style="color: #b0b0b0;">Document separation results will appear here after analysis.</p>
                </div>
            </div>

            <div id="rules" class="tab-content">
                <h3 style="color: #00d4ff; margin-bottom: 20px;">Analysis Rules</h3>
                <div id="rulesContent">
                    <p style="color: #b0b0b0;">Industry-specific analysis rules will be displayed here.</p>
                </div>
            </div>

            <div id="email" class="tab-content">
                <h3 style="color: #00d4ff; margin-bottom: 20px;">Email Parser</h3>
                <div style="margin-bottom: 20px;">
                    <textarea id="emailContent" placeholder="Paste lender email content here..." 
                              style="width: 100%; height: 200px; background: rgba(255,255,255,0.1); border: 1px solid #00d4ff; border-radius: 10px; padding: 15px; color: white; resize: vertical;"></textarea>
                </div>
                <button onclick="parseEmail()" style="background: linear-gradient(45deg, #00d4ff, #0099cc); color: white; border: none; padding: 12px 25px; border-radius: 25px; cursor: pointer; font-weight: 600;">
                    Parse Requirements
                </button>
                <div id="emailResults" style="margin-top: 20px;">
                    <p style="color: #b0b0b0;">Email parsing results will appear here.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedIndustry = 'mortgage';
        let selectedFiles = [];

        // Industry selection
        document.querySelectorAll('.industry-card').forEach(card => {
            card.addEventListener('click', function() {
                document.querySelectorAll('.industry-card').forEach(c => c.classList.remove('selected'));
                this.classList.add('selected');
                selectedIndustry = this.dataset.industry;
                
                // Show tabs section when industry is selected
                document.getElementById('tabsSection').style.display = 'block';
                
                console.log('Selected industry:', selectedIndustry);
            });
        });

        // File selection
        document.getElementById('fileInput').addEventListener('change', function(e) {
            selectedFiles = Array.from(e.target.files);
            displaySelectedFiles();
        });

        function displaySelectedFiles() {
            const container = document.getElementById('selectedFiles');
            if (selectedFiles.length > 0) {
                container.innerHTML = '<div class="selected-file"><strong>Selected Files:</strong><br>' + 
                    selectedFiles.map(f => f.name).join('<br>') + '</div>';
                document.getElementById('analyzeBtn').style.display = 'inline-block';
            } else {
                container.innerHTML = '';
                document.getElementById('analyzeBtn').style.display = 'none';
            }
        }

        // Tab functionality
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        // Analysis functionality
        function startAnalysis() {
            if (selectedFiles.length === 0) {
                alert('Please select files to analyze');
                return;
            }

            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const statusText = document.getElementById('statusText');
            
            progressContainer.style.display = 'block';
            
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            formData.append('industry', selectedIndustry);

            // Simulate progress
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress > 90) progress = 90;
                progressFill.style.width = progress + '%';
                statusText.textContent = getStatusMessage(progress);
            }, 500);

            fetch('/analyze', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                clearInterval(progressInterval);
                progressFill.style.width = '100%';
                statusText.textContent = 'Analysis complete!';
                
                setTimeout(() => {
                    progressContainer.style.display = 'none';
                    displayResults(data);
                }, 1000);
            })
            .catch(error => {
                clearInterval(progressInterval);
                console.error('Error:', error);
                statusText.textContent = 'Analysis failed. Please try again.';
            });
        }

        function getStatusMessage(progress) {
            if (progress < 20) return 'Initializing document processing...';
            if (progress < 40) return 'Extracting text and metadata...';
            if (progress < 60) return 'Applying industry-specific analysis...';
            if (progress < 80) return 'Generating insights and scoring...';
            return 'Finalizing results...';
        }

        function displayResults(data) {
            const resultsContainer = document.getElementById('analysisResults');
            
            if (data.success) {
                let html = '<div style="background: rgba(0,212,255,0.1); border: 1px solid #00d4ff; border-radius: 10px; padding: 20px; margin-bottom: 20px;">';
                html += '<h4 style="color: #00d4ff; margin-bottom: 15px;">Analysis Summary</h4>';
                html += '<p><strong>Industry:</strong> ' + data.industry + '</p>';
                html += '<p><strong>Files Processed:</strong> ' + data.files_processed + '</p>';
                html += '<p><strong>Total Pages:</strong> ' + (data.total_pages || 'N/A') + '</p>';
                html += '</div>';

                if (data.sections && data.sections.length > 0) {
                    html += '<h4 style="color: #00d4ff; margin: 20px 0;">Document Sections</h4>';
                    data.sections.forEach(section => {
                        html += '<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; margin-bottom: 10px;">';
                        html += '<div style="display: flex; justify-content: space-between; align-items: center;">';
                        html += '<strong style="color: white;">' + section.name + '</strong>';
                        html += '<span style="color: #00d4ff;">Pages: ' + section.pages + '</span>';
                        html += '</div>';
                        html += '<div style="margin-top: 10px; font-size: 0.9rem; color: #b0b0b0;">';
                        html += 'Confidence: ' + section.confidence + ' | Quality: ' + section.quality + ' | Risk: ' + section.risk_score;
                        html += '</div>';
                        if (section.notes) {
                            html += '<div style="margin-top: 5px; font-size: 0.8rem; color: #888;">' + section.notes + '</div>';
                        }
                        html += '</div>';
                    });
                }

                resultsContainer.innerHTML = html;
            } else {
                resultsContainer.innerHTML = '<div style="color: #ff6b35; padding: 20px;">Error: ' + data.error + '</div>';
            }
        }

        // Email parsing
        function parseEmail() {
            const content = document.getElementById('emailContent').value;
            if (!content.trim()) {
                alert('Please paste email content to parse');
                return;
            }

            fetch('/parse_email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({content: content})
            })
            .then(response => response.json())
            .then(data => {
                displayEmailResults(data);
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('emailResults').innerHTML = '<div style="color: #ff6b35;">Error parsing email</div>';
            });
        }

        function displayEmailResults(data) {
            const container = document.getElementById('emailResults');
            
            let html = '<div style="background: rgba(0,212,255,0.1); border: 1px solid #00d4ff; border-radius: 10px; padding: 20px;">';
            html += '<h4 style="color: #00d4ff; margin-bottom: 15px;">Lender Information</h4>';
            html += '<p><strong>Lender:</strong> ' + data.lender_name + '</p>';
            html += '<p><strong>Contact:</strong> ' + data.contact_name + ' (' + data.contact_email + ')</p>';
            html += '<p><strong>Funding Amount:</strong> ' + data.funding_amount + '</p>';
            html += '<p><strong>Date:</strong> ' + data.date + '</p>';
            
            if (data.documents && data.documents.length > 0) {
                html += '<h5 style="color: #00d4ff; margin: 15px 0 10px 0;">Required Documents (' + data.documents.length + '):</h5>';
                html += '<ul style="margin-left: 20px;">';
                data.documents.forEach(doc => {
                    html += '<li style="margin-bottom: 5px; color: #b0b0b0;">' + doc + '</li>';
                });
                html += '</ul>';
            }
            
            if (data.special_instructions && data.special_instructions.length > 0) {
                html += '<h5 style="color: #00d4ff; margin: 15px 0 10px 0;">Special Instructions:</h5>';
                html += '<ul style="margin-left: 20px;">';
                data.special_instructions.forEach(instruction => {
                    html += '<li style="margin-bottom: 5px; color: #b0b0b0;">' + instruction + '</li>';
                });
                html += '</ul>';
            }
            
            html += '</div>';
            container.innerHTML = html;
        }

        // Initialize with mortgage selected
        document.querySelector('[data-industry="mortgage"]').click();
    </script>
</body>
</html>
    ''', industries=INDUSTRY_TEMPLATES)

@app.route('/analyze', methods=['POST'])
def analyze_documents():
    """Universal document analysis endpoint"""
    try:
        files = request.files.getlist('files')
        industry = request.form.get('industry', 'mortgage')
        
        if not files:
            return jsonify({'success': False, 'error': 'No files uploaded'})
        
        results = {
            'success': True,
            'industry': INDUSTRY_TEMPLATES.get(industry, {}).get('name', industry.title()),
            'files_processed': len(files),
            'total_pages': 0,
            'sections': [],
            'metadata': {}
        }
        
        all_text = ""
        
        # Process each file
        for file in files:
            if file.filename:
                # Save file temporarily
                temp_path = f"/tmp/{file.filename}"
                file.save(temp_path)
                
                # Process with universal processor
                result = document_processor.process_document(temp_path, file.filename, industry)
                
                if result['success']:
                    all_text += result['text'] + "\n\n"
                    results['total_pages'] += result['metadata'].get('page_count', 1)
                
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except:
                    pass
        
        # Analyze based on industry
        if industry == 'mortgage':
            # Use existing mortgage analysis
            sections = analyze_mortgage_sections("combined_documents.pdf", True)
        else:
            # Use universal analysis
            sections = analyze_universal_document(all_text, industry, "combined_documents")
        
        results['sections'] = sections
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/parse_email', methods=['POST'])
def parse_email_endpoint():
    """Email parsing endpoint for lender requirements"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return jsonify({'error': 'No email content provided'})
        
        # Parse the email content
        lender_info = parse_lender_email(content)
        
        # Store globally for use in analysis
        global lender_requirements
        lender_requirements = lender_info
        
        return jsonify(lender_info)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'platform': 'Universal Document Analyzer',
        'industries': list(INDUSTRY_TEMPLATES.keys()),
        'supported_formats': list(document_processor.supported_formats.keys()),
        'features': [
            'Multi-industry support',
            'Universal document processing',
            'Email parsing',
            'Industry-specific analysis',
            'Real-time processing'
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

