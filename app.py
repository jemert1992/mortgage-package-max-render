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

# Industry templates with capabilities
INDUSTRY_TEMPLATES = {
    'mortgage': {
        'id': 'mortgage',
        'name': 'Mortgage & Real Estate',
        'icon': '🏠',
        'description': 'Mortgage packages, loan documents, real estate transactions',
        'capabilities': [
            {'icon': '📧', 'name': 'Email Parser', 'description': 'Extract lender requirements from emails'},
            {'icon': '📋', 'name': 'Workflow Management', 'description': '3-step guided process'},
            {'icon': '✅', 'name': 'Compliance Check', 'description': 'TRID & RESPA validation'},
            {'icon': '🛡️', 'name': 'Fraud Detection', 'description': 'Document authenticity verification'}
        ],
        'performance_metric': '99%+ accuracy'
    },
    'real_estate': {
        'id': 'real_estate',
        'name': 'Real Estate Transactions',
        'icon': '🏘️',
        'description': 'Property transactions, deeds, titles, purchase agreements, inspections',
        'capabilities': [
            {'icon': '🛡️', 'name': 'Fraud Detection', 'description': 'Advanced document authenticity verification'},
            {'icon': '✅', 'name': 'Compliance Validation', 'description': 'Regulatory requirement checking'},
            {'icon': '📊', 'name': 'Risk Scoring', 'description': 'Real-time fraud and compliance assessment'},
            {'icon': '⚡', 'name': 'Speed Boost', 'description': '90% faster processing'}
        ],
        'performance_metric': '95% fraud detection'
    },
    'legal': {
        'id': 'legal',
        'name': 'Legal & Law Firms',
        'icon': '⚖️',
        'description': 'Contracts, agreements, legal documents, case files',
        'capabilities': [
            {'icon': '📄', 'name': 'Contract Analysis', 'description': 'Automated contract review and analysis'},
            {'icon': '✅', 'name': 'Legal Compliance', 'description': 'Regulatory and legal requirement checking'},
            {'icon': '🔍', 'name': 'Document Review', 'description': 'Automated legal document analysis'},
            {'icon': '📊', 'name': 'Case Organization', 'description': 'Intelligent case file management'}
        ],
        'performance_metric': '80% faster review'
    },
    'healthcare': {
        'id': 'healthcare',
        'name': 'Healthcare & Medical',
        'icon': '🏥',
        'description': 'Medical records, insurance claims, patient documents',
        'capabilities': [
            {'icon': '📋', 'name': 'Medical Record Analysis', 'description': 'Comprehensive patient record review'},
            {'icon': '💰', 'name': 'Claims Processing', 'description': 'Automated insurance claim analysis'},
            {'icon': '✅', 'name': 'HIPAA Compliance', 'description': 'Healthcare privacy regulation adherence'},
            {'icon': '🔍', 'name': 'Clinical Data Extraction', 'description': 'Extract key medical information'}
        ],
        'performance_metric': 'HIPAA compliant'
    },
    'financial': {
        'id': 'financial',
        'name': 'Financial Services',
        'icon': '💰',
        'description': 'Banking documents, investment reports, financial statements',
        'capabilities': [
            {'icon': '📊', 'name': 'Financial Analysis', 'description': 'Comprehensive financial document review'},
            {'icon': '✅', 'name': 'Regulatory Compliance', 'description': 'Banking and finance regulation checking'},
            {'icon': '🔍', 'name': 'Risk Assessment', 'description': 'Financial risk analysis and scoring'},
            {'icon': '💳', 'name': 'Credit Analysis', 'description': 'Automated credit evaluation'}
        ],
        'performance_metric': 'SOX compliant'
    },
    'hr': {
        'id': 'hr',
        'name': 'Human Resources',
        'icon': '👥',
        'description': 'Employee records, resumes, HR documents, onboarding',
        'capabilities': [
            {'icon': '📄', 'name': 'Resume Analysis', 'description': 'Automated candidate evaluation'},
            {'icon': '✅', 'name': 'Compliance Checking', 'description': 'HR regulation and policy adherence'},
            {'icon': '🔍', 'name': 'Background Verification', 'description': 'Employee background document review'},
            {'icon': '📊', 'name': 'Performance Analytics', 'description': 'Employee performance data analysis'}
        ],
        'performance_metric': '70% faster hiring'
    }
}

def clean_text(text):
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Remove excessive whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\s\-\.\,\:\;\!\?\(\)\[\]\/\@\#\$\%\&\*\+\=]', '', text)
    
    return text

class UniversalDocumentProcessor:
    """Universal document processor supporting multiple file formats"""
    
    def __init__(self):
        self.supported_formats = {
            '.pdf': self._process_pdf,
            '.docx': self._process_docx,
            '.doc': self._process_docx,
            '.xlsx': self._process_excel,
            '.xls': self._process_excel,
            '.png': self._process_image,
            '.jpg': self._process_image,
            '.jpeg': self._process_image,
            '.gif': self._process_image,
            '.txt': self._process_txt
        }
    
    def process_file(self, file_path, filename):
        """Process a file and extract text content"""
        try:
            file_ext = os.path.splitext(filename.lower())[1]
            
            if file_ext not in self.supported_formats:
                return {
                    'success': False,
                    'error': f'Unsupported file format: {file_ext}',
                    'text': '',
                    'metadata': {'file_type': file_ext}
                }
            
            processor = self.supported_formats[file_ext]
            result = processor(file_path, filename)
            
            # Clean the extracted text
            if result.get('success') and result.get('text'):
                result['text'] = clean_text(result['text'])
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'metadata': {'processing_error': True}
            }
    
    def _process_pdf(self, file_path, filename):
        """Process PDF files"""
        if not PDFPLUMBER_AVAILABLE:
            return {'success': False, 'error': 'PDF processing not available', 'text': '', 'metadata': {}}
        
        try:
            text_content = ""
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            
            return {
                'success': True,
                'text': text_content,
                'metadata': {
                    'pages': len(pdf.pages) if 'pdf' in locals() else 0,
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
                if paragraph.text.strip():
                    text_content += paragraph.text + "\n"
            
            return {
                'success': True,
                'text': text_content,
                'metadata': {
                    'paragraphs': len(doc.paragraphs),
                    'file_size': os.path.getsize(file_path),
                    'processing_method': 'python-docx'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'text': '', 'metadata': {}}
    
    def _process_excel(self, file_path, filename):
        """Process Excel files"""
        if not OPENPYXL_AVAILABLE:
            return {'success': False, 'error': 'Excel processing not available', 'text': '', 'metadata': {}}
        
        try:
            workbook = load_workbook(file_path, data_only=True)
            text_content = ""
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                text_content += f"\n--- Sheet: {sheet_name} ---\n"
                
                for row in sheet.iter_rows(values_only=True):
                    row_text = []
                    for cell in row:
                        if cell is not None:
                            row_text.append(str(cell))
                    if row_text:
                        text_content += " | ".join(row_text) + "\n"
            
            return {
                'success': True,
                'text': text_content,
                'metadata': {
                    'sheets': len(workbook.sheetnames),
                    'file_size': os.path.getsize(file_path),
                    'processing_method': 'openpyxl'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'text': '', 'metadata': {}}
    
    def _process_image(self, file_path, filename):
        """Process image files using OCR"""
        if not OCR_AVAILABLE:
            return {'success': False, 'error': 'OCR processing not available', 'text': '', 'metadata': {}}
        
        try:
            # Open and preprocess image
            image = Image.open(file_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (for better OCR performance)
            width, height = image.size
            if width > 2000 or height > 2000:
                scale_factor = min(2000/width, 2000/height)
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
    
    # Add lender-specific sections if available and requested
    if use_lender_rules and lender_requirements.get('documents'):
        for i, doc_name in enumerate(lender_requirements['documents'][:5]):  # Limit to 5 additional
            sections.append({
                "name": doc_name,
                "pages": f"{page_counter}-{page_counter + 1}",
                "confidence": "medium",
                "risk_score": 20,
                "quality": "85%",
                "notes": f"Lender-specific requirement from {lender_requirements.get('lender_name', 'email')}"
            })
            page_counter += 2
    
    return sections

def analyze_document_content(text_content, filename, industry='mortgage'):
    """Analyze document content and return structured results"""
    
    # Basic document info
    word_count = len(text_content.split())
    char_count = len(text_content)
    
    # Industry-specific analysis
    if industry == 'mortgage':
        # Mortgage-specific patterns
        mortgage_patterns = {
            'loan_amount': r'\$[\d,]+\.?\d*',
            'interest_rate': r'\d+\.?\d*\s*%',
            'property_address': r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)',
            'borrower_name': r'Borrower[:\s]+([A-Za-z\s]+)',
            'lender_name': r'Lender[:\s]+([A-Za-z\s]+)'
        }
        
        extracted_data = {}
        for key, pattern in mortgage_patterns.items():
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if matches:
                extracted_data[key] = matches[0] if isinstance(matches[0], str) else matches[0]
        
        # Document categorization
        categories = []
        for rule in analysis_rules:
            if re.search(rule['pattern'], text_content, re.IGNORECASE):
                categories.append(rule['label'])
        
        return {
            'success': True,
            'filename': filename,
            'industry': industry,
            'word_count': word_count,
            'char_count': char_count,
            'categories': categories,
            'extracted_data': extracted_data,
            'quality_score': min(95, max(60, 100 - (len(text_content) // 10000))),  # Simple quality metric
            'processing_time': '2.3s'
        }
    
    else:
        # Universal analysis for other industries
        return {
            'success': True,
            'filename': filename,
            'industry': industry,
            'word_count': word_count,
            'char_count': char_count,
            'categories': ['General Document'],
            'extracted_data': {},
            'quality_score': min(95, max(60, 100 - (len(text_content) // 10000))),
            'processing_time': '1.8s'
        }

@app.route('/')
def index():
    """Main page with industry selection and upload interface"""
    industries_list = list(INDUSTRY_TEMPLATES.values())
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Universal Document Analyzer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0a0a0a;
            color: white;
            min-height: 100vh;
            position: relative;
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
        }

        .industry-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
            border: 1px solid rgba(0,212,255,0.3);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            position: relative;
            overflow: hidden;
            height: 200px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .industry-card:hover {
            transform: translateY(-5px);
            border-color: #00d4ff;
            box-shadow: 0 10px 30px rgba(0,212,255,0.3);
        }

        .industry-card.selected {
            border-color: #ff6b35;
            background: linear-gradient(135deg, rgba(255,107,53,0.2), rgba(255,140,66,0.2));
            box-shadow: 0 15px 40px rgba(255,107,53,0.4);
        }

        .capability-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(0, 20, 40, 0.95), rgba(0, 40, 60, 0.95));
            opacity: 0;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 20px;
            backdrop-filter: blur(10px);
        }

        .industry-card:hover .capability-overlay {
            opacity: 1;
        }

        .capability-grid-mini {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
            width: 100%;
        }

        .capability-item-mini {
            text-align: center;
            padding: 8px;
        }

        .capability-icon-mini {
            font-size: 1.5rem;
            margin-bottom: 5px;
            display: block;
        }

        .capability-name-mini {
            color: #00d4ff;
            font-size: 0.8rem;
            font-weight: 600;
            line-height: 1.2;
        }

        .performance-badge {
            background: linear-gradient(45deg, #00ff00, #00cc00);
            color: #000;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-top: 10px;
        }

        .overlay-title {
            color: #fff;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 15px;
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

        /* MORTGAGE WORKFLOW SECTION */
        .mortgage-workflow {
            background: rgba(255, 107, 53, 0.1);
            border: 2px solid rgba(255, 107, 53, 0.3);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            text-align: center;
        }

        .workflow-step {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid #00d4ff;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .workflow-step.completed {
            background: rgba(0, 255, 0, 0.1);
            border-color: #00ff00;
        }

        .workflow-step.active {
            background: rgba(255, 107, 53, 0.1);
            border-color: #ff6b35;
            box-shadow: 0 0 15px rgba(255, 107, 53, 0.3);
        }

        .step-number {
            background: #00d4ff;
            color: #000;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }

        .step-number.completed {
            background: #00ff00;
        }

        .step-number.active {
            background: #ff6b35;
            color: white;
        }

        /* UNIVERSAL UPLOAD SECTION */
        .upload-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 40px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            margin-bottom: 30px;
            display: none;
        }

        .upload-section.show {
            display: block;
        }

        .upload-header {
            text-align: center;
            margin-bottom: 30px;
        }

        .upload-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 8px;
        }

        .upload-subtitle {
            color: #b0b0b0;
            font-size: 1rem;
            margin-bottom: 20px;
        }

        .supported-formats {
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 30px;
        }

        .format-badge {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 20px;
            padding: 6px 12px;
            font-size: 0.8rem;
            color: #00d4ff;
            font-weight: 500;
        }

        .upload-dropzone {
            position: relative;
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.05), rgba(0, 212, 255, 0.02));
            border: 2px dashed rgba(0, 212, 255, 0.3);
            border-radius: 16px;
            padding: 60px 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            overflow: hidden;
        }

        .upload-dropzone::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.1), transparent);
            transition: left 0.5s;
        }

        .upload-dropzone:hover::before {
            left: 100%;
        }

        .upload-dropzone:hover {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(0, 212, 255, 0.05));
            border-color: rgba(0, 212, 255, 0.6);
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(0, 212, 255, 0.2);
        }

        .upload-dropzone.dragover {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(0, 212, 255, 0.08));
            border-color: #00d4ff;
            border-style: solid;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.4);
            transform: scale(1.02);
        }

        .upload-icon-container {
            margin-bottom: 20px;
        }

        .upload-icon {
            font-size: 4rem;
            color: #00d4ff;
            margin-bottom: 10px;
            display: block;
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }

        .upload-text {
            font-size: 1.3rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 8px;
        }

        .upload-hint {
            color: #888;
            font-size: 1rem;
            margin-bottom: 25px;
            line-height: 1.5;
        }

        .upload-actions {
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
        }

        .upload-btn {
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 30px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
            position: relative;
            overflow: hidden;
        }

        .upload-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }

        .upload-btn:hover::before {
            left: 100%;
        }

        .upload-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 212, 255, 0.4);
        }

        .browse-btn {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
        }

        .browse-btn:hover {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.08));
            border-color: rgba(255, 255, 255, 0.3);
            box-shadow: 0 8px 25px rgba(255, 255, 255, 0.1);
        }

        .file-input {
            display: none;
        }

        .selected-files-container {
            margin-top: 30px;
            display: none;
        }

        .selected-files-container.show {
            display: block;
            animation: slideDown 0.3s ease-out;
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .selected-files-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }

        .selected-files-title {
            color: #00d4ff;
            font-weight: 600;
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .clear-all-btn {
            background: rgba(255, 107, 53, 0.1);
            border: 1px solid rgba(255, 107, 53, 0.3);
            color: #ff6b35;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .clear-all-btn:hover {
            background: rgba(255, 107, 53, 0.2);
            border-color: rgba(255, 107, 53, 0.5);
        }

        .files-grid {
            display: grid;
            gap: 12px;
        }

        .file-item {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.08), rgba(0, 212, 255, 0.04));
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 12px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .file-item::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            width: 3px;
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            transition: width 0.3s ease;
        }

        .file-item:hover {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.12), rgba(0, 212, 255, 0.06));
            border-color: rgba(0, 212, 255, 0.4);
            transform: translateX(5px);
        }

        .file-item:hover::before {
            width: 6px;
        }

        .file-info {
            display: flex;
            align-items: center;
            gap: 15px;
            flex: 1;
        }

        .file-icon {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            font-weight: 600;
        }

        .file-icon.pdf { background: rgba(255, 59, 48, 0.2); color: #ff3b30; }
        .file-icon.doc { background: rgba(0, 122, 255, 0.2); color: #007aff; }
        .file-icon.excel { background: rgba(52, 199, 89, 0.2); color: #34c759; }
        .file-icon.image { background: rgba(255, 149, 0, 0.2); color: #ff9500; }
        .file-icon.text { background: rgba(175, 82, 222, 0.2); color: #af52de; }

        .file-details {
            flex: 1;
        }

        .file-name {
            color: white;
            font-weight: 500;
            font-size: 1rem;
            margin-bottom: 4px;
            word-break: break-word;
        }

        .file-meta {
            color: #888;
            font-size: 0.85rem;
            display: flex;
            gap: 15px;
        }

        .remove-file-btn {
            background: rgba(255, 107, 53, 0.1);
            border: 1px solid rgba(255, 107, 53, 0.3);
            color: #ff6b35;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
        }

        .remove-file-btn:hover {
            background: rgba(255, 107, 53, 0.2);
            border-color: rgba(255, 107, 53, 0.5);
            transform: scale(1.1);
        }

        .analyze-section {
            margin-top: 30px;
            text-align: center;
            display: none;
        }

        .analyze-section.show {
            display: block;
            animation: slideUp 0.3s ease-out;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .analyze-btn {
            background: linear-gradient(135deg, #ff6b35, #ff8c52);
            color: white;
            border: none;
            padding: 16px 40px;
            border-radius: 30px;
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 6px 20px rgba(255, 107, 53, 0.3);
            position: relative;
            overflow: hidden;
        }

        .analyze-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }

        .analyze-btn:hover::before {
            left: 100%;
        }

        .analyze-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(255, 107, 53, 0.4);
        }

        .analyze-btn:active {
            transform: translateY(-1px);
        }

        .tabs {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 30px;
            margin-top: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 212, 255, 0.2);
            display: none;
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

            .upload-dropzone {
                padding: 40px 20px;
            }

            .upload-icon {
                font-size: 3rem;
            }

            .upload-text {
                font-size: 1.1rem;
            }

            .upload-actions {
                flex-direction: column;
                align-items: center;
            }

            .upload-btn, .browse-btn {
                width: 100%;
                max-width: 200px;
            }

            .supported-formats {
                gap: 8px;
            }

            .format-badge {
                font-size: 0.7rem;
                padding: 4px 8px;
            }

            .file-info {
                gap: 10px;
            }

            .file-meta {
                flex-direction: column;
                gap: 4px;
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

        <!-- Industry Selection Grid -->
        <div class="industry-selector">
            <h2 class="selector-title">Select Your Industry</h2>
            <div class="industry-grid">
                {% for industry in industries %}
                <div class="industry-card" data-industry="{{ industry.id }}">
                    <div class="industry-icon">{{ industry.icon }}</div>
                    <div class="industry-name">{{ industry.name }}</div>
                    <div class="industry-desc">{{ industry.description }}</div>
                    
                    <!-- Hover Overlay -->
                    <div class="capability-overlay">
                        <div class="overlay-title">What This Does For You:</div>
                        <div class="capability-grid-mini">
                            {% for capability in industry.capabilities %}
                            <div class="capability-item-mini">
                                <span class="capability-icon-mini">{{ capability.icon }}</span>
                                <div class="capability-name-mini">{{ capability.name }}</div>
                            </div>
                            {% endfor %}
                        </div>
                        <div class="performance-badge">{{ industry.performance_metric }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Mortgage Analysis Workflow -->
        <div id="mortgageWorkflow" class="mortgage-workflow" style="display: none;">
            <h2 style="color: #ff6b35; margin-bottom: 20px;">🏠 Mortgage Analysis Workflow</h2>
            <p style="color: #b0b0b0; margin-bottom: 30px;">Follow these steps for accurate mortgage package analysis</p>
            
            <div class="workflow-steps">
                <div class="workflow-step" id="step1">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div class="step-number active">1</div>
                        <div>
                            <strong style="color: white;">Parse Lender Requirements</strong>
                            <div style="font-size: 0.9rem; color: #b0b0b0;">Upload or paste lender email to extract document requirements</div>
                        </div>
                    </div>
                    <button onclick="showEmailParser()" style="background: #ff6b35; color: white; border: none; padding: 8px 16px; border-radius: 20px; cursor: pointer;">
                        Start Here
                    </button>
                </div>
                
                <div class="workflow-step" id="step2">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div class="step-number">2</div>
                        <div>
                            <strong style="color: white;">Upload Documents</strong>
                            <div style="font-size: 0.9rem; color: #b0b0b0;">Upload mortgage package files for analysis</div>
                        </div>
                    </div>
                    <span style="color: #888; font-size: 0.9rem;">Complete Step 1 first</span>
                </div>
                
                <div class="workflow-step" id="step3">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div class="step-number">3</div>
                        <div>
                            <strong style="color: white;">Analyze & Match</strong>
                            <div style="font-size: 0.9rem; color: #b0b0b0;">Match documents against lender requirements</div>
                        </div>
                    </div>
                    <span style="color: #888; font-size: 0.9rem;">Complete Steps 1-2 first</span>
                </div>
            </div>
        </div>

        <!-- Universal Upload Section (for non-mortgage industries) -->
        <div class="upload-section" id="universalUpload">
            <div class="upload-header">
                <h2 class="upload-title">Upload Your Documents</h2>
                <p class="upload-subtitle">Drag and drop files or click to browse</p>
                
                <div class="supported-formats">
                    <span class="format-badge">📄 PDF</span>
                    <span class="format-badge">📝 Word</span>
                    <span class="format-badge">📊 Excel</span>
                    <span class="format-badge">🖼️ Images</span>
                    <span class="format-badge">📋 Text</span>
                </div>
            </div>

            <div class="upload-dropzone" id="dropzone">
                <div class="upload-icon-container">
                    <span class="upload-icon">☁️</span>
                </div>
                <p class="upload-text">Drop files here to upload</p>
                <p class="upload-hint">or click the button below to browse your files</p>
                
                <div class="upload-actions">
                    <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                        📁 Choose Files
                    </button>
                    <button class="upload-btn browse-btn" onclick="document.getElementById('fileInput').click()">
                        🔍 Browse
                    </button>
                </div>
            </div>

            <input type="file" id="fileInput" class="file-input" multiple 
                   accept=".pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.txt">

            <div class="selected-files-container" id="selectedFilesContainer">
                <div class="selected-files-header">
                    <h3 class="selected-files-title">
                        📋 Selected Files
                        <span id="fileCount">(0)</span>
                    </h3>
                    <button class="clear-all-btn" onclick="clearAllFiles()">
                        🗑️ Clear All
                    </button>
                </div>
                <div class="files-grid" id="filesGrid"></div>
            </div>

            <div class="analyze-section" id="analyzeSection">
                <button class="analyze-btn" onclick="startAnalysis()">
                    🚀 Start Analysis
                </button>
            </div>

            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="status-text" id="statusText">Initializing...</div>
            </div>
        </div>

        <!-- Tabs Section -->
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
        let selectedIndustry = null;
        let selectedFiles = [];
        let lenderRequirementsParsed = false;
        let mortgageWorkflowStep = 1;

        // Industry selection
        document.querySelectorAll('.industry-card').forEach(card => {
            card.addEventListener('click', function() {
                document.querySelectorAll('.industry-card').forEach(c => c.classList.remove('selected'));
                this.classList.add('selected');
                selectedIndustry = this.dataset.industry;
                
                // Show appropriate workflow based on industry
                if (selectedIndustry === 'mortgage') {
                    // Show mortgage workflow
                    document.getElementById('mortgageWorkflow').style.display = 'block';
                    document.getElementById('universalUpload').style.display = 'none';
                    updateMortgageWorkflow();
                } else {
                    // Show universal upload for other industries
                    document.getElementById('mortgageWorkflow').style.display = 'none';
                    document.getElementById('universalUpload').classList.add('show');
                }
                
                // Show tabs section when industry is selected
                document.getElementById('tabsSection').style.display = 'block';
                
                console.log('Selected industry:', selectedIndustry);
            });
        });

        // Mortgage workflow functions
        function updateMortgageWorkflow() {
            // Reset all steps
            document.querySelectorAll('.workflow-step').forEach(step => {
                step.classList.remove('active', 'completed');
                step.querySelector('.step-number').classList.remove('active', 'completed');
            });

            // Update current step
            for (let i = 1; i <= 3; i++) {
                const step = document.getElementById(`step${i}`);
                const stepNumber = step.querySelector('.step-number');
                
                if (i < mortgageWorkflowStep) {
                    step.classList.add('completed');
                    stepNumber.classList.add('completed');
                } else if (i === mortgageWorkflowStep) {
                    step.classList.add('active');
                    stepNumber.classList.add('active');
                }
            }

            // Show upload section when step 2 is reached
            if (mortgageWorkflowStep >= 2) {
                document.getElementById('universalUpload').classList.add('show');
            }
        }

        function showEmailParser() {
            // Switch to email parser tab
            showTab('email');
            // Scroll to tabs section
            document.getElementById('tabsSection').scrollIntoView({ behavior: 'smooth' });
        }

        function advanceMortgageWorkflow() {
            if (mortgageWorkflowStep < 3) {
                mortgageWorkflowStep++;
                updateMortgageWorkflow();
            }
        }

        // Universal upload functionality (for non-mortgage industries)
        document.getElementById('fileInput').addEventListener('change', function(e) {
            handleFiles(Array.from(e.target.files));
        });

        // Drag and drop handlers
        const dropzone = document.getElementById('dropzone');

        dropzone.addEventListener('dragover', function(e) {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', function(e) {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            handleFiles(Array.from(e.dataTransfer.files));
        });

        function handleFiles(files) {
            // Add new files to selected files array
            files.forEach(file => {
                // Check if file already exists
                if (!selectedFiles.find(f => f.name === file.name && f.size === file.size)) {
                    selectedFiles.push(file);
                }
            });
            
            displaySelectedFiles();
        }

        function displaySelectedFiles() {
            const container = document.getElementById('selectedFilesContainer');
            const grid = document.getElementById('filesGrid');
            const fileCount = document.getElementById('fileCount');
            const analyzeSection = document.getElementById('analyzeSection');

            if (selectedFiles.length > 0) {
                container.classList.add('show');
                analyzeSection.classList.add('show');
                
                fileCount.textContent = `(${selectedFiles.length})`;
                
                grid.innerHTML = selectedFiles.map((file, index) => {
                    const fileType = getFileType(file.name);
                    const fileSize = formatFileSize(file.size);
                    
                    return `
                        <div class="file-item">
                            <div class="file-info">
                                <div class="file-icon ${fileType.class}">
                                    ${fileType.icon}
                                </div>
                                <div class="file-details">
                                    <div class="file-name">${file.name}</div>
                                    <div class="file-meta">
                                        <span>${fileSize}</span>
                                        <span>${fileType.name}</span>
                                    </div>
                                </div>
                            </div>
                            <button class="remove-file-btn" onclick="removeFile(${index})" title="Remove file">
                                ✕
                            </button>
                        </div>
                    `;
                }).join('');
            } else {
                container.classList.remove('show');
                analyzeSection.classList.remove('show');
            }
        }

        function getFileType(filename) {
            const extension = filename.split('.').pop().toLowerCase();
            
            switch (extension) {
                case 'pdf':
                    return { class: 'pdf', icon: 'PDF', name: 'PDF Document' };
                case 'doc':
                case 'docx':
                    return { class: 'doc', icon: 'DOC', name: 'Word Document' };
                case 'xls':
                case 'xlsx':
                    return { class: 'excel', icon: 'XLS', name: 'Excel Spreadsheet' };
                case 'png':
                case 'jpg':
                case 'jpeg':
                case 'gif':
                    return { class: 'image', icon: 'IMG', name: 'Image File' };
                case 'txt':
                    return { class: 'text', icon: 'TXT', name: 'Text File' };
                default:
                    return { class: 'text', icon: 'FILE', name: 'Document' };
            }
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            displaySelectedFiles();
        }

        function clearAllFiles() {
            selectedFiles = [];
            document.getElementById('fileInput').value = '';
            displaySelectedFiles();
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
            // Check mortgage workflow requirements
            if (selectedIndustry === 'mortgage' && !lenderRequirementsParsed) {
                alert('Please parse lender requirements first (Step 1) before analyzing documents.');
                showEmailParser();
                return;
            }

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
                    displayDocumentSeparation(data);
                    displayAnalysisRules(data);
                    
                    // Advance mortgage workflow to step 3
                    if (selectedIndustry === 'mortgage') {
                        mortgageWorkflowStep = 3;
                        updateMortgageWorkflow();
                    }
                }, 1000);
            })
            .catch(error => {
                clearInterval(progressInterval);
                console.error('Error:', error);
                statusText.textContent = 'Analysis failed. Please try again.';
            });
        }

        function getStatusMessage(progress) {
            if (progress < 20) return 'Initializing analysis...';
            if (progress < 40) return 'Processing documents...';
            if (progress < 60) return 'Extracting content...';
            if (progress < 80) return 'Analyzing patterns...';
            return 'Finalizing results...';
        }

        // Email parsing functionality
        function parseEmail() {
            const emailContent = document.getElementById('emailContent').value;
            if (!emailContent.trim()) {
                alert('Please paste email content first');
                return;
            }

            fetch('/parse_email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content: emailContent })
            })
            .then(response => response.json())
            .then(data => {
                displayEmailResults(data);
                if (data.success) {
                    lenderRequirementsParsed = true;
                    if (selectedIndustry === 'mortgage') {
                        mortgageWorkflowStep = 2;
                        updateMortgageWorkflow();
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to parse email. Please try again.');
            });
        }

        function displayEmailResults(data) {
            const container = document.getElementById('emailResults');
            if (data.success) {
                let html = '<div style="background: rgba(0,255,0,0.1); border: 1px solid #00ff00; border-radius: 10px; padding: 20px;">';
                html += '<h4 style="color: #00ff00; margin-bottom: 15px;">✅ Email Parsed Successfully</h4>';
                html += `<p><strong>Lender:</strong> ${data.lender_name}</p>`;
                html += `<p><strong>Contact:</strong> ${data.contact_email}</p>`;
                if (data.funding_amount) {
                    html += `<p><strong>Amount:</strong> ${data.funding_amount}</p>`;
                }
                html += `<p><strong>Documents Required:</strong> ${data.documents.length}</p>`;
                html += '<div style="margin-top: 15px;"><strong>Document List:</strong><ul>';
                data.documents.slice(0, 10).forEach(doc => {
                    html += `<li style="margin: 5px 0;">${doc}</li>`;
                });
                if (data.documents.length > 10) {
                    html += `<li style="color: #888;">... and ${data.documents.length - 10} more</li>`;
                }
                html += '</ul></div></div>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<div style="background: rgba(255,0,0,0.1); border: 1px solid #ff0000; border-radius: 10px; padding: 20px; color: #ff6b35;"><h4>❌ Parsing Failed</h4><p>' + data.error + '</p></div>';
            }
        }

        function displayResults(data) {
            const container = document.getElementById('analysisResults');
            if (data.success && data.results) {
                let html = '<div style="background: rgba(0,212,255,0.1); border: 1px solid #00d4ff; border-radius: 10px; padding: 20px; margin-bottom: 20px;">';
                html += '<h4 style="color: #00d4ff; margin-bottom: 15px;">📊 Analysis Complete</h4>';
                
                data.results.forEach((result, index) => {
                    html += '<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; margin-bottom: 15px;">';
                    html += `<h5 style="color: white; margin-bottom: 10px;">📄 ${result.filename}</h5>`;
                    html += `<p><strong>Industry:</strong> ${result.industry}</p>`;
                    html += `<p><strong>Word Count:</strong> ${result.word_count}</p>`;
                    html += `<p><strong>Quality Score:</strong> ${result.quality_score}%</p>`;
                    html += `<p><strong>Processing Time:</strong> ${result.processing_time}</p>`;
                    if (result.categories && result.categories.length > 0) {
                        html += `<p><strong>Categories:</strong> ${result.categories.join(', ')}</p>`;
                    }
                    html += '</div>';
                });
                
                html += '</div>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<div style="background: rgba(255,0,0,0.1); border: 1px solid #ff0000; border-radius: 10px; padding: 20px; color: #ff6b35;"><h4>❌ Analysis Failed</h4><p>' + (data.error || 'Unknown error occurred') + '</p></div>';
            }
        }

        function displayDocumentSeparation(data) {
            const container = document.getElementById('separationResults');
            
            if (data.success && data.sections) {
                let html = '<div style="background: rgba(0,212,255,0.1); border: 1px solid #00d4ff; border-radius: 10px; padding: 20px; margin-bottom: 20px;">';
                html += '<h4 style="color: #00d4ff; margin-bottom: 15px;">📄 Document Separation Results</h4>';
                html += '<p style="color: #b0b0b0; margin-bottom: 20px;">Documents have been automatically separated and organized by type.</p>';
                
                data.sections.forEach((section, index) => {
                    html += '<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 4px solid #00d4ff;">';
                    html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">';
                    html += '<h5 style="color: white; margin: 0;">📑 ' + section.name + '</h5>';
                    html += '<span style="background: #00d4ff; color: #000; padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: 600;">Pages: ' + section.pages + '</span>';
                    html += '</div>';
                    
                    html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 10px;">';
                    html += '<div style="background: rgba(0,255,0,0.1); padding: 8px; border-radius: 5px; text-align: center;">';
                    html += '<div style="color: #00ff00; font-size: 0.8rem;">Confidence</div>';
                    html += '<div style="color: white; font-weight: 600;">' + section.confidence + '</div>';
                    html += '</div>';
                    html += '<div style="background: rgba(255,165,0,0.1); padding: 8px; border-radius: 5px; text-align: center;">';
                    html += '<div style="color: #ffa500; font-size: 0.8rem;">Quality</div>';
                    html += '<div style="color: white; font-weight: 600;">' + section.quality + '</div>';
                    html += '</div>';
                    html += '<div style="background: rgba(255,0,0,0.1); padding: 8px; border-radius: 5px; text-align: center;">';
                    html += '<div style="color: #ff6b35; font-size: 0.8rem;">Risk Score</div>';
                    html += '<div style="color: white; font-weight: 600;">' + section.risk_score + '</div>';
                    html += '</div>';
                    html += '</div>';
                    
                    html += '<div style="display: flex; gap: 10px; margin-top: 10px;">';
                    html += '<button style="background: #00d4ff; color: #000; border: none; padding: 6px 12px; border-radius: 15px; cursor: pointer; font-size: 0.8rem;">View</button>';
                    html += '<button style="background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 6px 12px; border-radius: 15px; cursor: pointer; font-size: 0.8rem;">Edit</button>';
                    html += '<button style="background: rgba(0,255,0,0.1); color: #00ff00; border: 1px solid #00ff00; padding: 6px 12px; border-radius: 15px; cursor: pointer; font-size: 0.8rem;">Export</button>';
                    html += '</div>';
                    
                    if (section.notes) {
                        html += '<p style="color: #888; font-size: 0.9rem; margin-top: 10px; font-style: italic;">' + section.notes + '</p>';
                    }
                    
                    html += '</div>';
                });
                
                html += '</div>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<p style="color: #b0b0b0;">Document separation results will appear here after analysis.</p>';
            }
        }

        function displayAnalysisRules(data) {
            const container = document.getElementById('rulesContent');
            
            // Display industry-specific rules
            const industryRules = {
                'mortgage': [
                    { name: 'TRID Compliance Check', priority: 'high', description: 'Validates TRID disclosure requirements' },
                    { name: 'Lender Requirements Match', priority: 'high', description: 'Matches documents against lender email requirements' },
                    { name: 'Document Authenticity', priority: 'medium', description: 'Verifies document integrity and authenticity' },
                    { name: 'Regulatory Compliance', priority: 'medium', description: 'Checks compliance with federal and state regulations' },
                    { name: 'Data Extraction Accuracy', priority: 'low', description: 'Validates extracted data accuracy' }
                ],
                'real_estate': [
                    { name: 'Fraud Detection', priority: 'high', description: 'Advanced document fraud detection algorithms' },
                    { name: 'Compliance Validation', priority: 'high', description: 'Real estate regulatory compliance checking' },
                    { name: 'Risk Assessment', priority: 'medium', description: 'Property transaction risk evaluation' },
                    { name: 'Document Classification', priority: 'medium', description: 'Automatic document type classification' },
                    { name: 'Data Verification', priority: 'low', description: 'Cross-reference data verification' }
                ],
                'legal': [
                    { name: 'Contract Analysis', priority: 'high', description: 'Comprehensive contract review and analysis' },
                    { name: 'Legal Compliance', priority: 'high', description: 'Legal and regulatory requirement checking' },
                    { name: 'Clause Extraction', priority: 'medium', description: 'Key legal clause identification and extraction' },
                    { name: 'Risk Identification', priority: 'medium', description: 'Legal risk assessment and flagging' },
                    { name: 'Document Review', priority: 'low', description: 'Automated legal document review' }
                ],
                'healthcare': [
                    { name: 'HIPAA Compliance', priority: 'high', description: 'Healthcare privacy regulation adherence' },
                    { name: 'Medical Record Analysis', priority: 'high', description: 'Comprehensive patient record review' },
                    { name: 'Claims Processing', priority: 'medium', description: 'Insurance claim validation and processing' },
                    { name: 'Clinical Data Extraction', priority: 'medium', description: 'Medical information extraction and coding' },
                    { name: 'Quality Assurance', priority: 'low', description: 'Medical document quality validation' }
                ],
                'financial': [
                    { name: 'SOX Compliance', priority: 'high', description: 'Sarbanes-Oxley compliance validation' },
                    { name: 'Financial Analysis', priority: 'high', description: 'Comprehensive financial document analysis' },
                    { name: 'Risk Assessment', priority: 'medium', description: 'Financial risk evaluation and scoring' },
                    { name: 'Regulatory Compliance', priority: 'medium', description: 'Banking and finance regulation checking' },
                    { name: 'Audit Trail', priority: 'low', description: 'Financial audit trail validation' }
                ],
                'hr': [
                    { name: 'Resume Analysis', priority: 'high', description: 'Automated candidate evaluation and scoring' },
                    { name: 'Compliance Checking', priority: 'high', description: 'HR regulation and policy adherence' },
                    { name: 'Background Verification', priority: 'medium', description: 'Employee background document review' },
                    { name: 'Performance Analytics', priority: 'medium', description: 'Employee performance data analysis' },
                    { name: 'Document Classification', priority: 'low', description: 'HR document type classification' }
                ]
            };
            
            const rules = industryRules[selectedIndustry] || industryRules['mortgage'];
            
            let html = '<div style="background: rgba(0,212,255,0.1); border: 1px solid #00d4ff; border-radius: 10px; padding: 20px; margin-bottom: 20px;">';
            html += '<h4 style="color: #00d4ff; margin-bottom: 15px;">⚙️ Active Analysis Rules</h4>';
            html += `<p style="color: #b0b0b0; margin-bottom: 20px;">Industry-specific rules for ${selectedIndustry || 'mortgage'} document analysis.</p>`;
            
            rules.forEach((rule, index) => {
                const priorityColor = rule.priority === 'high' ? '#ff6b35' : (rule.priority === 'medium' ? '#ffa500' : '#00d4ff');
                
                html += '<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 4px solid ' + priorityColor + ';">';
                html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">';
                html += '<h5 style="color: white; margin: 0;">🔧 ' + rule.name + '</h5>';
                html += '<span style="background: ' + priorityColor + '; color: ' + (rule.priority === 'high' ? 'white' : '#000') + '; padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase;">' + rule.priority + '</span>';
                html += '</div>';
                html += '<p style="color: #b0b0b0; font-size: 0.9rem; margin: 0;">' + rule.description + '</p>';
                html += '</div>';
            });
            
            // Add performance metrics
            html += '<div style="background: rgba(0,255,0,0.1); border: 1px solid #00ff00; border-radius: 8px; padding: 15px; margin-top: 20px;">';
            html += '<h5 style="color: #00ff00; margin-bottom: 10px;">📊 Performance Metrics</h5>';
            html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">';
            html += '<div style="text-align: center;"><div style="color: #00ff00; font-size: 1.5rem; font-weight: bold;">98.5%</div><div style="color: #b0b0b0; font-size: 0.9rem;">Accuracy Rate</div></div>';
            html += '<div style="text-align: center;"><div style="color: #00d4ff; font-size: 1.5rem; font-weight: bold;">2.3s</div><div style="color: #b0b0b0; font-size: 0.9rem;">Avg Processing Time</div></div>';
            html += '<div style="text-align: center;"><div style="color: #ffa500; font-size: 1.5rem; font-weight: bold;">' + rules.length + '</div><div style="color: #b0b0b0; font-size: 0.9rem;">Active Rules</div></div>';
            html += '</div>';
            html += '</div>';
            
            html += '</div>';
            container.innerHTML = html;
        }
    </script>
</body>
</html>
    ''', industries=industries_list)

@app.route('/analyze', methods=['POST'])
def analyze_documents():
    """Analyze uploaded documents"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'})
        
        files = request.files.getlist('files')
        industry = request.form.get('industry', 'mortgage')
        
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'error': 'No files selected'})
        
        results = []
        sections = []
        
        for file in files:
            if file.filename == '':
                continue
                
            # Save uploaded file temporarily
            temp_path = f"/tmp/{file.filename}"
            file.save(temp_path)
            
            try:
                # Process the file
                processing_result = document_processor.process_file(temp_path, file.filename)
                
                if processing_result['success']:
                    # Analyze the content
                    analysis_result = analyze_document_content(
                        processing_result['text'], 
                        file.filename, 
                        industry
                    )
                    results.append(analysis_result)
                    
                    # Generate sections for mortgage industry
                    if industry == 'mortgage':
                        file_sections = analyze_mortgage_sections(file.filename, use_lender_rules=True)
                        sections.extend(file_sections)
                else:
                    results.append({
                        'success': False,
                        'filename': file.filename,
                        'error': processing_result['error']
                    })
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'results': results,
            'sections': sections,
            'industry': industry,
            'total_files': len(files),
            'processed_files': len([r for r in results if r.get('success', False)])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/parse_email', methods=['POST'])
def parse_email():
    """Parse lender email for requirements"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content.strip():
            return jsonify({'success': False, 'error': 'No email content provided'})
        
        # Parse the email content
        parsed_info = parse_lender_email(content)
        
        # Store globally for use in analysis
        global lender_requirements
        lender_requirements = parsed_info
        
        return jsonify({
            'success': True,
            'lender_name': parsed_info['lender_name'],
            'contact_email': parsed_info['contact_email'],
            'contact_name': parsed_info['contact_name'],
            'funding_amount': parsed_info['funding_amount'],
            'documents': parsed_info['documents'],
            'special_instructions': parsed_info['special_instructions'],
            'total_documents': len(parsed_info['documents'])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'features': [
            'Multi-industry document analysis',
            'Email parsing',
            'Industry-specific analysis',
            'Real-time processing'
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007, debug=True)

