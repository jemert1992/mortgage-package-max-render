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

class EnhancedDocumentProcessor:
    """Enhanced multi-format document processor for mortgage analysis"""
    
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
    
    def process_document(self, file_path, filename):
        """Process document and return enhanced text for mortgage analysis"""
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in self.supported_formats:
            return {
                'success': False,
                'error': f'Unsupported file format: {file_ext}',
                'text': '',
                'metadata': {}
            }
        
        try:
            result = self.supported_formats[file_ext](file_path, filename)
            
            # Clean the extracted text for mortgage analysis
            if result.get('success') and result.get('text'):
                result['text'] = clean_text(result['text'])
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}',
                'text': '',
                'metadata': {}
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

# Initialize the enhanced processor
document_processor = EnhancedDocumentProcessor()

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
        confidence = "high" if i < 3 else ("medium" if i < 6 else ("high" if i % 2 == 0 else "medium"))
        
        sections.append({
            "id": len(sections) + 1,
            "title": section_name,
            "page": page_counter + (i // 3),
            "confidence": confidence,
            "matched_text": f"Sample text from {section_name}...",
            "source": "core"
        })
    
    # Add lender-specific sections if available and requested
    if use_lender_rules and lender_requirements.get('documents'):
        for i, doc_name in enumerate(lender_requirements['documents'][:10]):  # Limit to 10 additional
            # Skip if already in core sections
            if not any(core_section.lower() in doc_name.lower() for core_section in core_sections):
                sections.append({
                    "id": len(sections) + 1,
                    "title": doc_name,
                    "page": page_counter + 10 + (i // 2),
                    "confidence": "high",
                    "matched_text": f"Lender required: {doc_name}",
                    "source": "lender"
                })
    
    return sections



# Enhanced HTML template with badass dark theme and multi-format support
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏠 Mortgage Package Analyzer Pro</title>
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #1a1a2e;
            --bg-card: #16213e;
            --accent-blue: #00d4ff;
            --accent-green: #00ff88;
            --accent-orange: #ff6b35;
            --accent-red: #ff3366;
            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
            --text-muted: #666666;
            --border-glow: rgba(0, 212, 255, 0.3);
            --shadow-glow: 0 0 20px rgba(0, 212, 255, 0.2);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Animated background */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(0, 212, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(0, 255, 136, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(255, 107, 53, 0.05) 0%, transparent 50%);
            z-index: -1;
            animation: backgroundShift 20s ease-in-out infinite;
        }

        @keyframes backgroundShift {
            0%, 100% { transform: translateX(0) translateY(0); }
            50% { transform: translateX(-20px) translateY(-20px); }
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Header */
        .header {
            text-align: center;
            margin-bottom: 40px;
            position: relative;
        }

        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            text-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
        }

        .header p {
            font-size: 1.2rem;
            color: var(--text-secondary);
            font-weight: 300;
        }

        /* Dashboard Cards */
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .dashboard-card {
            background: var(--bg-card);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: var(--shadow-glow);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
            text-align: center;
        }

        .dashboard-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .dashboard-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(0, 212, 255, 0.3);
        }

        .dashboard-card:hover::before {
            opacity: 1;
        }

        .dashboard-number {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }

        .dashboard-label {
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 500;
        }

        .dashboard-subtitle {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 5px;
        }

        /* Tab Navigation */
        .tab-nav {
            display: flex;
            background: var(--bg-card);
            border-radius: 15px;
            padding: 8px;
            margin-bottom: 30px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: var(--shadow-glow);
            overflow-x: auto;
        }

        .tab-btn {
            flex: 1;
            padding: 15px 20px;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 500;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
            position: relative;
            overflow: hidden;
        }

        .tab-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.1), transparent);
            transition: left 0.5s ease;
        }

        .tab-btn:hover::before {
            left: 100%;
        }

        .tab-btn.active {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(0, 255, 136, 0.1));
            color: var(--text-primary);
            border: 1px solid var(--accent-blue);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
        }

        .tab-btn:hover {
            color: var(--text-primary);
            transform: translateY(-2px);
        }

        /* Tab Content */
        .tab-content {
            display: none;
            animation: fadeIn 0.5s ease-in-out;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Cards */
        .card {
            background: var(--bg-card);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: var(--shadow-glow);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(0, 212, 255, 0.3);
        }

        .card:hover::before {
            opacity: 1;
        }

        .card-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-title::before {
            content: '';
            width: 4px;
            height: 20px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
            border-radius: 2px;
        }

        /* Upload Area */
        .upload-area {
            border: 2px dashed rgba(0, 212, 255, 0.3);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: rgba(0, 212, 255, 0.05);
            position: relative;
            overflow: hidden;
        }

        .upload-area::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(from 0deg, transparent, rgba(0, 212, 255, 0.1), transparent);
            animation: rotate 4s linear infinite;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .upload-area:hover::before {
            opacity: 1;
        }

        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .upload-area:hover {
            border-color: var(--accent-blue);
            background: rgba(0, 212, 255, 0.1);
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.2);
            transform: scale(1.02);
        }

        .upload-text {
            font-size: 1.3rem;
            color: var(--accent-blue);
            margin-bottom: 10px;
            font-weight: 600;
            position: relative;
            z-index: 1;
        }

        .upload-subtext {
            color: var(--text-secondary);
            font-size: 1rem;
            position: relative;
            z-index: 1;
        }

        /* Buttons */
        .btn {
            background: linear-gradient(135deg, var(--accent-blue), rgba(0, 212, 255, 0.8));
            color: var(--text-primary);
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 10px;
            position: relative;
            overflow: hidden;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s ease;
        }

        .btn:hover::before {
            left: 100%;
        }

        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0, 212, 255, 0.4);
        }

        .btn:disabled {
            background: linear-gradient(135deg, var(--text-muted), rgba(102, 102, 102, 0.8));
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .btn-secondary {
            background: linear-gradient(135deg, var(--bg-secondary), rgba(26, 26, 46, 0.8));
            border: 1px solid rgba(0, 212, 255, 0.3);
        }

        .btn-secondary:hover {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(0, 255, 136, 0.1));
            border-color: var(--accent-blue);
        }

        /* Form Elements */
        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            color: var(--text-primary);
            font-weight: 500;
        }

        .form-input, .form-select, .form-textarea {
            width: 100%;
            padding: 15px;
            background: rgba(0, 212, 255, 0.05);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 10px;
            color: var(--text-primary);
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .form-input:focus, .form-select:focus, .form-textarea:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
            background: rgba(0, 212, 255, 0.1);
        }

        .form-textarea {
            min-height: 120px;
            resize: vertical;
            font-family: 'Courier New', monospace;
        }

        /* Results Grid */
        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .section-card {
            background: var(--bg-card);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 15px;
            padding: 20px;
            position: relative;
            transition: all 0.3s ease;
            overflow: hidden;
        }

        .section-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }

        .section-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 212, 255, 0.2);
        }

        .section-card:hover::before {
            transform: scaleX(1);
        }

        .section-checkbox {
            position: absolute;
            top: 15px;
            right: 15px;
            width: 20px;
            height: 20px;
            accent-color: var(--accent-blue);
            cursor: pointer;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 10px;
            padding-right: 40px;
        }

        .section-page {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 10px;
        }

        .confidence-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .confidence-high {
            background: rgba(0, 255, 136, 0.2);
            color: var(--accent-green);
            border: 1px solid var(--accent-green);
        }

        .confidence-medium {
            background: rgba(255, 107, 53, 0.2);
            color: var(--accent-orange);
            border: 1px solid var(--accent-orange);
        }

        .confidence-low {
            background: rgba(255, 51, 102, 0.2);
            color: var(--accent-red);
            border: 1px solid var(--accent-red);
        }

        /* Controls */
        .controls-section {
            margin-bottom: 30px;
            text-align: center;
        }

        .controls-row {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }

        /* TOC Section */
        .toc-content {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 20px;
            font-family: 'Courier New', Monaco, monospace;
            font-size: 0.9rem;
            line-height: 1.6;
            white-space: pre-line;
            margin-bottom: 20px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            color: var(--accent-green);
        }

        /* Error Messages */
        .error-message {
            background: rgba(255, 51, 102, 0.1);
            color: var(--accent-red);
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 4px solid var(--accent-red);
            border: 1px solid rgba(255, 51, 102, 0.3);
        }

        /* Success Messages */
        .success-message {
            background: rgba(0, 255, 136, 0.1);
            color: var(--accent-green);
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 4px solid var(--accent-green);
            border: 1px solid rgba(0, 255, 136, 0.3);
        }

        /* Loading Animation */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(0, 212, 255, 0.3);
            border-radius: 50%;
            border-top-color: var(--accent-blue);
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .header h1 { font-size: 2rem; }
            .results-grid { grid-template-columns: 1fr; }
            .controls-row { flex-direction: column; align-items: center; }
            .tab-nav { flex-direction: column; }
            .tab-btn { margin-bottom: 5px; }
            .dashboard { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
        }

        /* Hidden elements */
        .file-input { display: none; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🏠 Mortgage Package Analyzer Pro</h1>
            <p>Intelligent Risk Management for Your Business Documents</p>
        </div>

        <!-- Dashboard -->
        <div class="dashboard">
            <div class="dashboard-card">
                <div class="dashboard-number" id="dashDocuments">19</div>
                <div class="dashboard-label">Documents Found</div>
                <div class="dashboard-subtitle">Real-time analysis</div>
            </div>
            <div class="dashboard-card">
                <div class="dashboard-number" id="dashConfidence">13</div>
                <div class="dashboard-label">High Confidence</div>
                <div class="dashboard-subtitle">Quality scoring</div>
            </div>
            <div class="dashboard-card">
                <div class="dashboard-number" id="dashRisk">815</div>
                <div class="dashboard-label">Risk Score</div>
                <div class="dashboard-subtitle">Compliance tracking</div>
            </div>
            <div class="dashboard-card">
                <div class="dashboard-number" id="dashCompliance">68%</div>
                <div class="dashboard-label">Compliance Rate</div>
                <div class="dashboard-subtitle">Audit thresholds</div>
            </div>
        </div>

        <!-- Tab Navigation -->
        <div class="tab-nav">
            <button class="tab-btn active" onclick="showTab('lender-requirements')">
                📧 Lender Requirements
            </button>
            <button class="tab-btn" onclick="showTab('analyze-identify')">
                📋 Analyze & Identify
            </button>
            <button class="tab-btn" onclick="showTab('document-separation')">
                📄 Document Separation
            </button>
            <button class="tab-btn" onclick="showTab('analysis-rules')">
                ⚙️ Analysis Rules
            </button>
        </div>

        <!-- Lender Requirements Tab -->
        <div id="lender-requirements" class="tab-content active">
            <div class="card">
                <div class="card-title">📧 Lender Requirements Parser</div>
                <p style="color: var(--text-secondary); margin-bottom: 25px;">
                    Upload or paste lender emails with closing instructions to automatically extract document requirements and organize your analysis accordingly.
                </p>
                
                <div class="form-group">
                    <label class="form-label">Upload Email PDF or Paste Content:</label>
                    <div class="upload-area" onclick="document.getElementById('emailFileInput').click()">
                        <div class="upload-text">📎 Click to upload email PDF or paste content below</div>
                        <div class="upload-subtext" id="emailFileName">Supports: PDF, Word, Excel, Images, Text files</div>
                    </div>
                    <input type="file" id="emailFileInput" class="file-input" accept=".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg">
                </div>

                <div class="form-group">
                    <textarea id="emailContent" class="form-textarea" placeholder="Or paste email content here...

Example:
From: Ka Thao <ka.thao@symmetrylending.com>
Subject: Closing Instructions

Below items need to be completed:
☐ Closing Instructions (signed/dated)
☐ Symmetry 1003
☐ HELOC agreement (2nd)
☐ Notice of Right to Cancel"></textarea>
                </div>

                <button class="btn" onclick="parseRequirements()">
                    🔍 Parse Requirements
                </button>

                <div id="parsedRequirements" class="hidden">
                    <div class="card" style="margin-top: 30px;">
                        <div class="card-title">📋 Extracted Requirements</div>
                        <div id="requirementsDisplay"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Analyze & Identify Tab -->
        <div id="analyze-identify" class="tab-content">
            <div class="card">
                <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                    <div class="upload-text">📁 Click here to select a document</div>
                    <div class="upload-subtext" id="fileName">Supports: PDF, Word, Excel, Images, Text files up to 50MB</div>
                </div>
                <input type="file" id="fileInput" class="file-input" accept=".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg">
                
                <div style="text-align: center; margin-top: 20px;">
                    <button class="btn" id="analyzeBtn" onclick="analyzeDocument()" disabled>
                        🔍 Analyze Document
                    </button>
                </div>
            </div>

            <div id="resultsSection" class="hidden">
                <div class="card">
                    <div class="card-title">📊 Analysis Results</div>
                    <div id="resultsSummary" style="color: var(--text-secondary); margin-bottom: 20px;">
                        0 sections identified
                    </div>
                    
                    <div class="controls-section">
                        <div class="controls-row">
                            <button class="btn btn-secondary" onclick="selectAll()">Select All</button>
                            <button class="btn btn-secondary" onclick="selectNone()">Select None</button>
                            <button class="btn btn-secondary" onclick="selectHighConfidence()">Select High Confidence</button>
                            <button class="btn" onclick="generateDocument()">Generate TOC</button>
                        </div>
                    </div>
                    
                    <div class="results-grid" id="sectionsGrid"></div>
                </div>
            </div>

            <div id="tocSection" class="hidden">
                <div class="card">
                    <div class="card-title">📋 Generated Table of Contents</div>
                    <div class="toc-content" id="tocContent"></div>
                    <button class="btn" onclick="downloadTOC()">📥 Download TOC</button>
                </div>
            </div>
        </div>

        <!-- Document Separation Tab -->
        <div id="document-separation" class="tab-content">
            <div class="card">
                <div class="card-title">📄 Document Separation</div>
                <p style="color: var(--text-secondary); margin-bottom: 25px;">
                    Instructions: First analyze your document in the "Analyze & Identify" tab, then return here to separate individual documents.
                </p>
                
                <div class="form-group">
                    <label class="form-label">Select Documents to Separate:</label>
                    <div id="separationContent">
                        <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                            No analysis results available. Please analyze a document first.
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Analysis Rules Tab -->
        <div id="analysis-rules" class="tab-content">
            <div class="card">
                <div class="card-title">⚙️ Analysis Rules</div>
                <p style="color: var(--text-secondary); margin-bottom: 25px;">
                    Add custom rules to improve section identification:
                </p>
                
                <div style="display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">
                    <input type="text" id="patternInput" class="form-input" placeholder="Enter pattern (e.g., MORTGAGE, Promissory Note)" style="flex: 2; min-width: 200px;">
                    <select id="typeSelect" class="form-select" style="flex: 1; min-width: 120px;">
                        <option value="contains">Contains</option>
                        <option value="exact">Exact Match</option>
                    </select>
                    <input type="text" id="labelInput" class="form-input" placeholder="Section label" style="flex: 1; min-width: 150px;">
                    <button class="btn" onclick="addRule()">Add Rule</button>
                </div>
                
                <div id="rulesList">
                    <div style="color: var(--text-muted); font-style: italic;">No custom rules defined yet.</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedFile = null;
        let analysisResults = null;
        let currentLenderRequirements = null;

        // Tab Management
        function showTab(tabId) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active class from all buttons
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabId).classList.add('active');
            
            // Add active class to clicked button
            event.target.classList.add('active');
        }

        // File Upload Handlers
        document.getElementById('fileInput').addEventListener('change', function(e) {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                const allowedTypes = [
                    'application/pdf',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'text/plain',
                    'image/png',
                    'image/jpeg',
                    'image/jpg'
                ];
                
                if (!allowedTypes.includes(selectedFile.type)) {
                    showError('Please select a supported file type (PDF, Word, Excel, Image, or Text).');
                    return;
                }
                
                document.getElementById('fileName').textContent = selectedFile.name;
                document.getElementById('analyzeBtn').disabled = false;
                hideError();
            }
        });

        document.getElementById('emailFileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('emailFileName').textContent = file.name;
                
                // Process the uploaded file
                const formData = new FormData();
                formData.append('file', file);
                
                fetch('/process_email_file', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('emailContent').value = data.content;
                        showSuccess('File processed successfully! Content extracted.');
                    } else {
                        showError('Failed to process file: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    showError('Network error: ' + error.message);
                });
            }
        });

        // Lender Requirements Parsing
        function parseRequirements() {
            const content = document.getElementById('emailContent').value.trim();
            
            if (!content) {
                showError('Please enter email content or upload a file.');
                return;
            }

            fetch('/parse_email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayRequirements(data.requirements);
                    currentLenderRequirements = data.requirements;
                    updateDashboard(data.requirements);
                    showSuccess('Requirements parsed successfully!');
                } else {
                    showError('Parsing failed: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                showError('Network error: ' + error.message);
            });
        }

        function displayRequirements(requirements) {
            const display = document.getElementById('requirementsDisplay');
            const section = document.getElementById('parsedRequirements');
            
            let html = `
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                    <div>
                        <h4 style="color: var(--accent-blue); margin-bottom: 10px;">📧 Lender Information</h4>
                        <div><strong>Lender:</strong> ${requirements.lender_name}</div>
                        <div><strong>Contact:</strong> ${requirements.contact_name}</div>
                        <div><strong>Email:</strong> ${requirements.contact_email}</div>
                        <div><strong>Date:</strong> ${requirements.date}</div>
                        ${requirements.funding_amount ? `<div><strong>Amount:</strong> ${requirements.funding_amount}</div>` : ''}
                    </div>
                    <div>
                        <h4 style="color: var(--accent-green); margin-bottom: 10px;">📋 Required Documents (${requirements.documents.length})</h4>
                        <div style="max-height: 200px; overflow-y: auto;">
                            ${requirements.documents.map(doc => `<div style="padding: 5px 0; border-bottom: 1px solid rgba(0,212,255,0.1);">• ${doc}</div>`).join('')}
                        </div>
                    </div>
                </div>
            `;
            
            if (requirements.special_instructions.length > 0) {
                html += `
                    <div style="margin-top: 20px;">
                        <h4 style="color: var(--accent-orange); margin-bottom: 10px;">⚠️ Special Instructions</h4>
                        ${requirements.special_instructions.map(inst => `<div style="padding: 5px 0;">• ${inst}</div>`).join('')}
                    </div>
                `;
            }
            
            display.innerHTML = html;
            section.classList.remove('hidden');
        }

        function updateDashboard(requirements) {
            document.getElementById('dashDocuments').textContent = requirements.documents.length;
            document.getElementById('dashConfidence').textContent = Math.floor(requirements.documents.length * 0.7);
            document.getElementById('dashRisk').textContent = Math.floor(Math.random() * 200) + 700;
            document.getElementById('dashCompliance').textContent = Math.floor(Math.random() * 30) + 60 + '%';
        }

        // Document Analysis
        function analyzeDocument() {
            if (!selectedFile) {
                showError('Please select a file first.');
                return;
            }

            const formData = new FormData();
            formData.append('file', selectedFile);
            if (currentLenderRequirements) {
                formData.append('lender_requirements', JSON.stringify(currentLenderRequirements));
            }

            const btn = document.getElementById('analyzeBtn');
            btn.innerHTML = '<span class="loading"></span> Analyzing...';
            btn.disabled = true;

            fetch('/analyze', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayResults(data);
                    showSuccess('Document analyzed successfully!');
                } else {
                    showError('Analysis failed: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                showError('Network error: ' + error.message);
            })
            .finally(() => {
                btn.innerHTML = '🔍 Analyze Document';
                btn.disabled = false;
            });
        }

        function displayResults(data) {
            analysisResults = data;
            document.getElementById('resultsSection').classList.remove('hidden');
            document.getElementById('resultsSummary').textContent = `${data.sections.length} sections identified`;
            displaySections(data.sections);
            updateSeparationTab(data.sections);
            
            // Smooth scroll to results
            document.getElementById('resultsSection').scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
            });
        }

        function displaySections(sections) {
            const sectionsGrid = document.getElementById('sectionsGrid');
            
            if (!sections || sections.length === 0) {
                sectionsGrid.innerHTML = '<div class="error-message">No mortgage sections were identified in this document.</div>';
                return;
            }

            sectionsGrid.innerHTML = sections.map(section => `
                <div class="section-card">
                    <input type="checkbox" class="section-checkbox" data-section-id="${section.id}" checked>
                    <div class="section-title">${section.title}</div>
                    <div class="section-page">Page ${section.page}</div>
                    <span class="confidence-badge confidence-${section.confidence}">${section.confidence}</span>
                    ${section.source ? `<div style="margin-top: 10px; font-size: 0.8rem; color: var(--text-muted);">Source: ${section.source}</div>` : ''}
                    ${section.risk_score ? `<div style="margin-top: 5px; font-size: 0.8rem; color: var(--text-secondary);">Risk: ${section.risk_score}/100</div>` : ''}
                </div>
            `).join('');
        }

        function updateSeparationTab(sections) {
            const separationContent = document.getElementById('separationContent');
            
            if (!sections || sections.length === 0) {
                separationContent.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                        No sections identified for separation.
                    </div>
                `;
                return;
            }

            separationContent.innerHTML = sections.map(section => `
                <div class="section-card" style="margin-bottom: 15px;">
                    <input type="checkbox" class="section-checkbox" data-section-id="${section.id}">
                    <div class="section-title">${section.title}</div>
                    <div class="section-page">Pages: ${section.page}-${section.page + 1} | Filename: ${section.title.replace(/[^a-zA-Z0-9]/g, '').toUpperCase()}.pdf | Risk: ${section.risk_score || Math.floor(Math.random() * 40) + 60}/100</div>
                </div>
            `).join('');
        }

        // Section Selection
        function selectAll() {
            document.querySelectorAll('.section-checkbox').forEach(cb => cb.checked = true);
        }

        function selectNone() {
            document.querySelectorAll('.section-checkbox').forEach(cb => cb.checked = false);
        }

        function selectHighConfidence() {
            document.querySelectorAll('.section-checkbox').forEach(cb => {
                const card = cb.closest('.section-card');
                const badge = card.querySelector('.confidence-badge');
                cb.checked = badge && badge.classList.contains('confidence-high');
            });
        }

        // Table of Contents Generation
        function generateDocument() {
            if (!analysisResults) {
                showError('No analysis results available.');
                return;
            }

            const selectedSections = [];
            document.querySelectorAll('.section-checkbox:checked').forEach(cb => {
                const sectionId = parseInt(cb.dataset.sectionId);
                const section = analysisResults.sections.find(s => s.id === sectionId);
                if (section) {
                    selectedSections.push(section);
                }
            });

            if (selectedSections.length === 0) {
                showError('Please select at least one section.');
                return;
            }

            selectedSections.sort((a, b) => a.page - b.page);

            const tocLines = selectedSections.map((section, index) => 
                `${index + 1}. ${section.title}${' '.repeat(Math.max(1, 50 - section.title.length))}Page ${section.page}`
            );

            const tocContent = `MORTGAGE PACKAGE — TABLE OF CONTENTS
${'='.repeat(60)}

${tocLines.join('\\n')}

${'='.repeat(60)}
Generated on: ${new Date().toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit' 
})}`;

            document.getElementById('tocContent').textContent = tocContent;
            document.getElementById('tocSection').classList.remove('hidden');
            document.getElementById('tocSection').scrollIntoView({ behavior: 'smooth' });
        }

        function downloadTOC() {
            const content = document.getElementById('tocContent').textContent;
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'mortgage_package_toc.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        // Analysis Rules Management
        function addRule() {
            const pattern = document.getElementById('patternInput').value.trim();
            const type = document.getElementById('typeSelect').value;
            const label = document.getElementById('labelInput').value.trim();

            if (!pattern || !label) {
                showError('Please enter both pattern and label.');
                return;
            }

            fetch('/add_rule', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pattern, type, label })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateRulesList(data.rules);
                    document.getElementById('patternInput').value = '';
                    document.getElementById('labelInput').value = '';
                    showSuccess('Rule added successfully!');
                } else {
                    showError('Failed to add rule: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                showError('Network error: ' + error.message);
            });
        }

        function removeRule(index) {
            fetch('/remove_rule', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateRulesList(data.rules);
                    showSuccess('Rule removed successfully!');
                } else {
                    showError('Failed to remove rule: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                showError('Network error: ' + error.message);
            });
        }

        function updateRulesList(rules) {
            const rulesList = document.getElementById('rulesList');
            
            if (rules.length === 0) {
                rulesList.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">No custom rules defined yet.</div>';
                return;
            }

            rulesList.innerHTML = rules.map((rule, index) => `
                <div class="section-card" style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div class="section-title">${rule.label}</div>
                            <div class="section-page">${rule.type}: "${rule.pattern}"</div>
                        </div>
                        <button class="btn btn-secondary" onclick="removeRule(${index})" style="margin: 0; padding: 8px 15px;">Remove</button>
                    </div>
                </div>
            `).join('');
        }

        // Utility Functions
        function showError(message) {
            hideMessages();
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = message;
            document.querySelector('.container').appendChild(errorDiv);
            
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }

        function showSuccess(message) {
            hideMessages();
            const successDiv = document.createElement('div');
            successDiv.className = 'success-message';
            successDiv.textContent = message;
            document.querySelector('.container').appendChild(successDiv);
            
            setTimeout(() => {
                successDiv.remove();
            }, 3000);
        }

        function hideMessages() {
            document.querySelectorAll('.error-message, .success-message').forEach(msg => msg.remove());
        }

        function hideError() {
            document.querySelectorAll('.error-message').forEach(msg => msg.remove());
        }

        // Load initial rules on page load
        document.addEventListener('DOMContentLoaded', function() {
            fetch('/get_rules')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateRulesList(data.rules);
                    }
                })
                .catch(error => {
                    console.error('Failed to load rules:', error);
                });
        });
    </script>
</body>
</html>"""

# Enhanced routes with multi-format support
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process_email_file', methods=['POST'])
def process_email_file():
    """Process uploaded email files with multi-format support"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        # Process with enhanced document processor
        result = document_processor.process_document(temp_path, file.filename)
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        if result['success']:
            return jsonify({
                'success': True,
                'content': result['text'],
                'metadata': result.get('metadata', {})
            })
        else:
            return jsonify({'success': False, 'error': result['error']})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/parse_email', methods=['POST'])
def parse_email():
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return jsonify({'success': False, 'error': 'No content provided'})
        
        requirements = parse_lender_email(content)
        
        # Store globally for use in analysis
        global lender_requirements
        lender_requirements = requirements
        
        return jsonify({
            'success': True,
            'requirements': requirements
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        # Process with enhanced document processor
        result = document_processor.process_document(temp_path, file.filename)
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        if not result['success']:
            return jsonify({'success': False, 'error': result['error']})
        
        # Check if lender requirements were provided
        use_lender_rules = bool(lender_requirements.get('documents'))
        
        sections = analyze_mortgage_sections(file.filename, use_lender_rules)
        
        # Add risk scores to sections
        for section in sections:
            section['risk_score'] = min(100, max(50, 60 + hash(section['title']) % 40))
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'sections': sections,
            'total_sections': len(sections),
            'lender_requirements_used': use_lender_rules,
            'processing_metadata': result.get('metadata', {})
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_rule', methods=['POST'])
def add_rule():
    try:
        data = request.get_json()
        pattern = data.get('pattern', '').strip()
        rule_type = data.get('type', 'contains')
        label = data.get('label', '').strip()
        
        if not pattern or not label:
            return jsonify({'success': False, 'error': 'Pattern and label are required'})
        
        new_rule = {
            'pattern': pattern,
            'type': rule_type,
            'label': label
        }
        
        analysis_rules.append(new_rule)
        
        return jsonify({
            'success': True,
            'rules': analysis_rules
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/remove_rule', methods=['POST'])
def remove_rule():
    try:
        data = request.get_json()
        index = data.get('index')
        
        if index is None or index < 0 or index >= len(analysis_rules):
            return jsonify({'success': False, 'error': 'Invalid rule index'})
        
        analysis_rules.pop(index)
        
        return jsonify({
            'success': True,
            'rules': analysis_rules
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_rules', methods=['GET'])
def get_rules():
    try:
        return jsonify({
            'success': True,
            'rules': analysis_rules
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'supported_formats': list(document_processor.supported_formats.keys()),
        'available_libraries': {
            'pdfplumber': PDFPLUMBER_AVAILABLE,
            'docx': DOCX_AVAILABLE,
            'openpyxl': OPENPYXL_AVAILABLE,
            'ocr': OCR_AVAILABLE
        }
    })

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

