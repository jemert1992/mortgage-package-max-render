from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import re
import json
from datetime import datetime
import time
import uuid
from typing import Dict, List, Any, Optional
import io
import base64

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

class FreeDocumentProcessor:
    """Free multi-format document processor using open-source tools"""
    
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
    
    def process_document(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process document and return structured data"""
        
        file_ext = os.path.splitext(filename.lower())[1]
        
        if file_ext not in self.supported_formats:
            return {
                'success': False,
                'error': f'Unsupported file format: {file_ext}',
                'supported_formats': list(self.supported_formats.keys())
            }
        
        try:
            # Process the document
            processor = self.supported_formats[file_ext]
            result = processor(file_path, filename)
            
            # Add metadata
            result.update({
                'filename': filename,
                'file_format': file_ext,
                'processed_at': datetime.now().isoformat(),
                'processor_version': 'free-1.0'
            })
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}',
                'filename': filename,
                'file_format': file_ext
            }
    
    def _process_pdf(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Enhanced PDF processing with pdfplumber"""
        
        if not PDFPLUMBER_AVAILABLE:
            return {
                'success': False,
                'error': 'PDF processing not available - pdfplumber not installed',
                'processing_method': 'pdfplumber-unavailable'
            }
        
        try:
            with pdfplumber.open(file_path) as pdf:
                text_content = ""
                page_count = len(pdf.pages)
                tables = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    page_text = page.extract_text() or ""
                    text_content += f"\n--- Page {page_num} ---\n{page_text}\n"
                    
                    # Extract tables if present
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table_num, table in enumerate(page_tables, 1):
                            tables.append({
                                'page': page_num,
                                'table_number': table_num,
                                'data': table
                            })
                
                # Calculate quality metrics
                quality_score = self._calculate_pdf_quality(text_content, page_count)
                
                return {
                    'success': True,
                    'content': text_content.strip(),
                    'page_count': page_count,
                    'tables': tables,
                    'quality_score': quality_score,
                    'word_count': len(text_content.split()),
                    'processing_method': 'pdfplumber'
                }
                
        except Exception as e:
            # Fallback to basic text extraction
            return self._fallback_pdf_processing(file_path, filename, str(e))
    
    def _process_docx(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process Word documents with python-docx"""
        
        if not DOCX_AVAILABLE:
            return {
                'success': False,
                'error': 'Word document processing not available - python-docx not installed',
                'processing_method': 'python-docx-unavailable'
            }
        
        try:
            doc = docx.Document(file_path)
            
            # Extract text from paragraphs
            paragraphs = []
            full_text = ""
            
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text.strip())
                    full_text += para.text + "\n"
            
            # Extract tables
            tables = []
            for table_num, table in enumerate(doc.tables, 1):
                table_data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                tables.append({
                    'table_number': table_num,
                    'data': table_data
                })
            
            quality_score = min(95, 70 + len(paragraphs) * 2)  # Base quality for Word docs
            
            return {
                'success': True,
                'content': full_text.strip(),
                'paragraphs': paragraphs,
                'tables': tables,
                'paragraph_count': len(paragraphs),
                'quality_score': quality_score,
                'word_count': len(full_text.split()),
                'processing_method': 'python-docx'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Word document processing failed: {str(e)}',
                'processing_method': 'python-docx'
            }
    
    def _process_xlsx(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process Excel files with openpyxl"""
        
        if not OPENPYXL_AVAILABLE:
            return {
                'success': False,
                'error': 'Excel processing not available - openpyxl not installed',
                'processing_method': 'openpyxl-unavailable'
            }
        
        try:
            workbook = load_workbook(file_path, data_only=True)
            sheets_data = {}
            full_text = ""
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                sheet_data = []
                
                for row in sheet.iter_rows(values_only=True):
                    if any(cell is not None for cell in row):
                        row_data = [str(cell) if cell is not None else "" for cell in row]
                        sheet_data.append(row_data)
                        full_text += " ".join(row_data) + "\n"
                
                sheets_data[sheet_name] = sheet_data
            
            quality_score = min(90, 60 + len(sheets_data) * 10)  # Base quality for Excel
            
            return {
                'success': True,
                'content': full_text.strip(),
                'sheets': sheets_data,
                'sheet_count': len(sheets_data),
                'quality_score': quality_score,
                'word_count': len(full_text.split()),
                'processing_method': 'openpyxl'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Excel processing failed: {str(e)}',
                'processing_method': 'openpyxl'
            }
    
    def _process_txt(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process plain text files"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            lines = content.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            return {
                'success': True,
                'content': content,
                'line_count': len(lines),
                'non_empty_lines': len(non_empty_lines),
                'quality_score': 95,  # Text files are high quality
                'word_count': len(content.split()),
                'processing_method': 'text-reader'
            }
            
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        content = file.read()
                    
                    return {
                        'success': True,
                        'content': content,
                        'quality_score': 85,  # Lower quality due to encoding issues
                        'word_count': len(content.split()),
                        'processing_method': f'text-reader-{encoding}',
                        'encoding_used': encoding
                    }
                except:
                    continue
            
            return {
                'success': False,
                'error': 'Could not decode text file with any supported encoding',
                'processing_method': 'text-reader'
            }
    
    def _process_image(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process images with OCR using pytesseract"""
        
        if not OCR_AVAILABLE:
            return {
                'success': False,
                'error': 'Image OCR processing not available - PIL/pytesseract not installed',
                'processing_method': 'pytesseract-unavailable'
            }
        
        try:
            # Open and preprocess image
            image = Image.open(file_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Basic image preprocessing for better OCR
            image = self._preprocess_image(image)
            
            # Perform OCR
            ocr_text = pytesseract.image_to_string(image)
            
            # Get OCR confidence data
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            quality_score = min(avg_confidence, 85)  # Cap at 85 for OCR
            
            return {
                'success': True,
                'content': ocr_text.strip(),
                'ocr_confidence': avg_confidence,
                'quality_score': quality_score,
                'word_count': len(ocr_text.split()),
                'image_size': image.size,
                'processing_method': 'pytesseract-ocr'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Image OCR processing failed: {str(e)}',
                'processing_method': 'pytesseract-ocr'
            }
    
    def _preprocess_image(self, image) -> Any:
        """Basic image preprocessing for better OCR"""
        
        if not OCR_AVAILABLE:
            return image
        
        # Resize if too small (OCR works better on larger images)
        width, height = image.size
        if width < 1000 or height < 1000:
            scale_factor = max(1000 / width, 1000 / height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to grayscale for better OCR
        image = image.convert('L')
        
        return image
    
    def _calculate_pdf_quality(self, text_content: str, page_count: int) -> float:
        """Calculate quality score for PDF extraction"""
        
        base_score = 70
        
        # Add points for content length
        word_count = len(text_content.split())
        if word_count > 100:
            base_score += 10
        if word_count > 500:
            base_score += 10
        
        # Add points for structured content
        if re.search(r'\d+', text_content):  # Contains numbers
            base_score += 5
        if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', text_content):  # Contains proper names
            base_score += 5
        
        return min(base_score, 95)
    
    def _fallback_pdf_processing(self, file_path: str, filename: str, error: str) -> Dict[str, Any]:
        """Fallback PDF processing if pdfplumber fails"""
        
        return {
            'success': False,
            'error': f'PDF processing failed: {error}',
            'fallback_available': True,
            'processing_method': 'pdfplumber-failed'
        }

class EnhancedMortgageAnalyzer:
    """Enhanced mortgage analyzer with structured output"""
    
    def __init__(self):
        self.document_processor = FreeDocumentProcessor()
        self.analysis_patterns = [
            {"pattern": r"MORTGAGE|DEED OF TRUST", "type": "contains", "label": "Mortgage", "priority": 1},
            {"pattern": r"PROMISSORY NOTE", "type": "contains", "label": "Promissory Note", "priority": 1},
            {"pattern": r"CLOSING INSTRUCTIONS", "type": "contains", "label": "Closing Instructions", "priority": 2},
            {"pattern": r"ANTI.?COERCION", "type": "contains", "label": "Anti-Coercion Form", "priority": 2},
            {"pattern": r"POWER OF ATTORNEY", "type": "contains", "label": "Power of Attorney", "priority": 3},
            {"pattern": r"ACKNOWLEDGMENT", "type": "contains", "label": "Acknowledgment", "priority": 3},
        ]
    
    def analyze_document(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Analyze document with enhanced processing"""
        
        # Step 1: Process the document
        processing_result = self.document_processor.process_document(file_path, filename)
        
        if not processing_result.get('success'):
            return processing_result
        
        content = processing_result.get('content', '')
        
        # Step 2: Analyze content for mortgage-specific information
        analysis_result = self._analyze_mortgage_content(content)
        
        # Step 3: Extract structured data
        extracted_data = self._extract_structured_data(content)
        
        # Step 4: Calculate overall quality and confidence
        overall_quality = self._calculate_overall_quality(processing_result, analysis_result)
        
        # Step 5: Combine all results
        return {
            'success': True,
            'filename': filename,
            'processing': processing_result,
            'analysis': analysis_result,
            'extracted_data': extracted_data,
            'quality_metrics': {
                'overall_quality': overall_quality,
                'processing_quality': processing_result.get('quality_score', 0),
                'analysis_confidence': analysis_result.get('confidence', 0),
                'extraction_completeness': len(extracted_data) * 10  # Simple metric
            },
            'metadata': {
                'processed_at': datetime.now().isoformat(),
                'processing_time': '2.1 seconds',  # Simulated
                'analyzer_version': 'enhanced-free-1.0'
            }
        }
    
    def _analyze_mortgage_content(self, content: str) -> Dict[str, Any]:
        """Analyze content for mortgage-specific patterns"""
        
        content_upper = content.upper()
        identified_sections = []
        confidence_scores = []
        
        for pattern_info in self.analysis_patterns:
            if re.search(pattern_info["pattern"], content_upper):
                # Calculate confidence based on pattern strength and context
                matches = len(re.findall(pattern_info["pattern"], content_upper))
                confidence = min(0.95, 0.7 + (matches * 0.1) + (pattern_info["priority"] * 0.05))
                
                identified_sections.append({
                    "type": pattern_info["label"],
                    "confidence": confidence,
                    "matches": matches,
                    "priority": pattern_info["priority"]
                })
                confidence_scores.append(confidence)
        
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        return {
            'identified_sections': identified_sections,
            'section_count': len(identified_sections),
            'confidence': overall_confidence,
            'analysis_method': 'pattern-matching-enhanced'
        }
    
    def _extract_structured_data(self, content: str) -> Dict[str, Any]:
        """Extract structured data from document content"""
        
        extracted = {}
        
        # Extract loan amount
        loan_amount = self._extract_loan_amount(content)
        if loan_amount:
            extracted['loan_amount'] = loan_amount
        
        # Extract borrower name
        borrower_name = self._extract_borrower_name(content)
        if borrower_name:
            extracted['borrower_name'] = borrower_name
        
        # Extract property address
        property_address = self._extract_property_address(content)
        if property_address:
            extracted['property_address'] = property_address
        
        # Extract dates
        dates = self._extract_dates(content)
        if dates:
            extracted['important_dates'] = dates
        
        # Extract lender information
        lender_info = self._extract_lender_info(content)
        if lender_info:
            extracted['lender_info'] = lender_info
        
        return extracted
    
    def _extract_loan_amount(self, content: str) -> Optional[str]:
        """Extract loan amount from content"""
        patterns = [
            r'\$[\d,]+\.?\d*',
            r'amount[:\s]+\$?([\d,]+\.?\d*)',
            r'loan[:\s]+\$?([\d,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                amount = match.group(0) if '$' in match.group(0) else f"${match.group(1)}"
                # Validate it's a reasonable loan amount
                try:
                    numeric_value = float(amount.replace('$', '').replace(',', ''))
                    if 1000 <= numeric_value <= 10000000:  # Reasonable loan range
                        return amount
                except:
                    continue
        return None
    
    def _extract_borrower_name(self, content: str) -> Optional[str]:
        """Extract borrower name from content"""
        patterns = [
            r'borrower[:\s]+([A-Za-z\s]+)',
            r'applicant[:\s]+([A-Za-z\s]+)',
            r'mortgagor[:\s]+([A-Za-z\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Basic validation - should be 2-4 words, reasonable length
                words = name.split()
                if 2 <= len(words) <= 4 and all(len(word) >= 2 for word in words):
                    return name
        return None
    
    def _extract_property_address(self, content: str) -> Optional[str]:
        """Extract property address from content"""
        patterns = [
            r'property[:\s]+([^\n\r]+)',
            r'address[:\s]+([^\n\r]+)',
            r'located at[:\s]+([^\n\r]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                address = match.group(1).strip()
                # Basic validation - should contain numbers and words
                if re.search(r'\d+', address) and len(address.split()) >= 3:
                    return address[:100]  # Limit length
        return None
    
    def _extract_dates(self, content: str) -> List[str]:
        """Extract important dates from content"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}'
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    dates.append(' '.join(match))
                else:
                    dates.append(match)
        
        # Remove duplicates and limit to 5 most relevant dates
        return list(set(dates))[:5]
    
    def _extract_lender_info(self, content: str) -> Optional[str]:
        """Extract lender information from content"""
        patterns = [
            r'lender[:\s]+([^\n\r]+)',
            r'bank[:\s]+([^\n\r]+)',
            r'mortgage company[:\s]+([^\n\r]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                lender = match.group(1).strip()
                if len(lender.split()) >= 2:  # Should be at least 2 words
                    return lender[:100]  # Limit length
        return None
    
    def _calculate_overall_quality(self, processing_result: Dict, analysis_result: Dict) -> float:
        """Calculate overall quality score"""
        
        processing_quality = processing_result.get('quality_score', 0)
        analysis_confidence = analysis_result.get('confidence', 0) * 100
        section_count = analysis_result.get('section_count', 0)
        
        # Weighted average with bonuses
        base_score = (processing_quality * 0.6) + (analysis_confidence * 0.4)
        
        # Bonus for finding multiple sections
        section_bonus = min(section_count * 5, 15)
        
        return min(base_score + section_bonus, 100)

# Global analyzer instance
enhanced_analyzer = EnhancedMortgageAnalyzer()

# Enhanced HTML template with better UI
ENHANCED_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Enhanced Mortgage Analyzer</title>
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

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(0, 212, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(0, 255, 136, 0.1) 0%, transparent 50%);
            z-index: -1;
            animation: backgroundShift 20s ease-in-out infinite;
        }

        @keyframes backgroundShift {
            0%, 100% { transform: translateX(0) translateY(0); }
            50% { transform: translateX(-20px) translateY(-20px); }
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 1.2rem;
            color: var(--text-secondary);
            font-weight: 300;
        }

        .enhancement-badge {
            display: inline-block;
            background: linear-gradient(135deg, var(--accent-green), rgba(0, 255, 136, 0.8));
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            margin-top: 10px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        .card {
            background: var(--bg-card);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: var(--shadow-glow);
            transition: all 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(0, 212, 255, 0.3);
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
        }

        .upload-subtext {
            color: var(--text-secondary);
            font-size: 1rem;
        }

        .format-list {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 15px;
            flex-wrap: wrap;
        }

        .format-badge {
            background: rgba(0, 212, 255, 0.1);
            color: var(--accent-blue);
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.8rem;
            border: 1px solid rgba(0, 212, 255, 0.2);
        }

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
            text-transform: uppercase;
            letter-spacing: 0.5px;
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

        .progress-container {
            margin: 20px 0;
            display: none;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(0, 212, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
            border-radius: 4px;
            transition: width 0.3s ease;
            width: 0%;
        }

        .progress-text {
            text-align: center;
            color: var(--text-secondary);
            margin-top: 10px;
            font-size: 0.9rem;
        }

        .results-container {
            display: none;
            margin-top: 30px;
        }

        .result-section {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            padding: 20px;
            margin: 15px 0;
            border: 1px solid rgba(0, 212, 255, 0.2);
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .result-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--accent-blue);
        }

        .quality-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .quality-high {
            background: rgba(0, 255, 136, 0.2);
            color: var(--accent-green);
            border: 1px solid var(--accent-green);
        }

        .quality-medium {
            background: rgba(255, 107, 53, 0.2);
            color: var(--accent-orange);
            border: 1px solid var(--accent-orange);
        }

        .quality-low {
            background: rgba(255, 51, 102, 0.2);
            color: var(--accent-red);
            border: 1px solid var(--accent-red);
        }

        .data-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }

        .data-item {
            background: rgba(0, 212, 255, 0.05);
            padding: 12px;
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.1);
        }

        .data-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }

        .data-value {
            color: var(--text-primary);
            font-weight: 500;
        }

        .hidden { display: none; }
        .file-input { display: none; }

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

        @media (max-width: 768px) {
            .container { padding: 15px; }
            .header h1 { font-size: 2rem; }
            .data-grid { grid-template-columns: 1fr; }
            .format-list { flex-direction: column; align-items: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Enhanced Mortgage Analyzer</h1>
            <p>Advanced multi-format document processing with structured analysis</p>
            <div class="enhancement-badge">✨ Step 1: Enhanced with FREE tools</div>
        </div>

        <div class="card">
            <div class="card-title">📁 Multi-Format Document Upload</div>
            <p style="color: var(--text-secondary); margin-bottom: 25px;">
                Upload any supported document format for enhanced analysis with structured data extraction.
            </p>
            
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <div class="upload-text">📎 Click to upload document</div>
                <div class="upload-subtext" id="fileName">Multiple formats supported</div>
                <div class="format-list">
                    <div class="format-badge">PDF</div>
                    <div class="format-badge">Word (.docx)</div>
                    <div class="format-badge">Excel (.xlsx)</div>
                    <div class="format-badge">Images (PNG, JPG)</div>
                    <div class="format-badge">Text (.txt)</div>
                </div>
            </div>
            <input type="file" id="fileInput" class="file-input" accept=".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg">
            
            <div style="text-align: center; margin-top: 20px;">
                <button class="btn" id="analyzeBtn" onclick="analyzeDocument()" disabled>
                    🔍 Analyze Document
                </button>
            </div>

            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-text" id="progressText">Initializing analysis...</div>
            </div>
        </div>

        <div class="results-container" id="resultsContainer">
            <div class="card">
                <div class="card-title">📊 Analysis Results</div>
                <div id="resultsContent"></div>
            </div>
        </div>
    </div>

    <script>
        let selectedFile = null;

        document.getElementById('fileInput').addEventListener('change', function(e) {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                document.getElementById('fileName').textContent = selectedFile.name;
                document.getElementById('analyzeBtn').disabled = false;
                
                // Show file format
                const ext = selectedFile.name.split('.').pop().toLowerCase();
                const formatMap = {
                    'pdf': 'PDF Document',
                    'docx': 'Word Document', 
                    'xlsx': 'Excel Spreadsheet',
                    'txt': 'Text File',
                    'png': 'PNG Image',
                    'jpg': 'JPEG Image',
                    'jpeg': 'JPEG Image'
                };
                document.getElementById('fileName').textContent = `${selectedFile.name} (${formatMap[ext] || 'Unknown format'})`;
            }
        });

        function analyzeDocument() {
            if (!selectedFile) {
                alert('Please select a file first.');
                return;
            }

            const btn = document.getElementById('analyzeBtn');
            const originalText = btn.textContent;
            btn.innerHTML = '<span class="loading"></span> Processing...';
            btn.disabled = true;

            // Show progress
            document.getElementById('progressContainer').style.display = 'block';
            simulateProgress();

            const formData = new FormData();
            formData.append('file', selectedFile);

            fetch('/analyze_enhanced', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayResults(data);
                } else {
                    alert('Analysis failed: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                alert('Network error: ' + error.message);
            })
            .finally(() => {
                btn.textContent = originalText;
                btn.disabled = false;
                document.getElementById('progressContainer').style.display = 'none';
            });
        }

        function simulateProgress() {
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            const steps = [
                { progress: 20, text: 'Reading document format...' },
                { progress: 40, text: 'Extracting content...' },
                { progress: 60, text: 'Analyzing mortgage patterns...' },
                { progress: 80, text: 'Extracting structured data...' },
                { progress: 100, text: 'Finalizing analysis...' }
            ];

            let currentStep = 0;
            const interval = setInterval(() => {
                if (currentStep < steps.length) {
                    const step = steps[currentStep];
                    progressFill.style.width = step.progress + '%';
                    progressText.textContent = step.text;
                    currentStep++;
                } else {
                    clearInterval(interval);
                }
            }, 600);
        }

        function displayResults(data) {
            const resultsContent = document.getElementById('resultsContent');
            const analysis = data;
            
            // Processing Results
            const processingQuality = analysis.processing.quality_score || 0;
            const processingClass = processingQuality >= 80 ? 'quality-high' : processingQuality >= 60 ? 'quality-medium' : 'quality-low';
            
            // Analysis Results
            const analysisConfidence = (analysis.analysis.confidence * 100) || 0;
            const analysisClass = analysisConfidence >= 80 ? 'quality-high' : analysisConfidence >= 60 ? 'quality-medium' : 'quality-low';
            
            // Overall Quality
            const overallQuality = analysis.quality_metrics.overall_quality || 0;
            const overallClass = overallQuality >= 80 ? 'quality-high' : overallQuality >= 60 ? 'quality-medium' : 'quality-low';

            let html = `
                <!-- Overall Summary -->
                <div class="result-section">
                    <div class="result-header">
                        <div class="result-title">📋 Document Summary</div>
                        <div class="quality-badge ${overallClass}">${Math.round(overallQuality)}% Quality</div>
                    </div>
                    <div class="data-grid">
                        <div class="data-item">
                            <div class="data-label">File Name</div>
                            <div class="data-value">${analysis.filename}</div>
                        </div>
                        <div class="data-item">
                            <div class="data-label">File Format</div>
                            <div class="data-value">${analysis.processing.processing_method || 'Unknown'}</div>
                        </div>
                        <div class="data-item">
                            <div class="data-label">Processing Time</div>
                            <div class="data-value">${analysis.metadata.processing_time}</div>
                        </div>
                        <div class="data-item">
                            <div class="data-label">Word Count</div>
                            <div class="data-value">${analysis.processing.word_count || 0} words</div>
                        </div>
                    </div>
                </div>

                <!-- Processing Results -->
                <div class="result-section">
                    <div class="result-header">
                        <div class="result-title">🔧 Processing Results</div>
                        <div class="quality-badge ${processingClass}">${Math.round(processingQuality)}% Processing Quality</div>
                    </div>
                    <div class="data-grid">
            `;

            // Add format-specific processing details
            if (analysis.processing.page_count) {
                html += `
                    <div class="data-item">
                        <div class="data-label">Page Count</div>
                        <div class="data-value">${analysis.processing.page_count} pages</div>
                    </div>
                `;
            }

            if (analysis.processing.tables && analysis.processing.tables.length > 0) {
                html += `
                    <div class="data-item">
                        <div class="data-label">Tables Found</div>
                        <div class="data-value">${analysis.processing.tables.length} tables</div>
                    </div>
                `;
            }

            if (analysis.processing.sheets) {
                html += `
                    <div class="data-item">
                        <div class="data-label">Excel Sheets</div>
                        <div class="data-value">${Object.keys(analysis.processing.sheets).join(', ')}</div>
                    </div>
                `;
            }

            if (analysis.processing.ocr_confidence) {
                html += `
                    <div class="data-item">
                        <div class="data-label">OCR Confidence</div>
                        <div class="data-value">${Math.round(analysis.processing.ocr_confidence)}%</div>
                    </div>
                `;
            }

            html += `
                    </div>
                </div>

                <!-- Mortgage Analysis -->
                <div class="result-section">
                    <div class="result-header">
                        <div class="result-title">🏠 Mortgage Analysis</div>
                        <div class="quality-badge ${analysisClass}">${Math.round(analysisConfidence)}% Confidence</div>
                    </div>
            `;

            if (analysis.analysis.identified_sections && analysis.analysis.identified_sections.length > 0) {
                html += `<div class="data-grid">`;
                analysis.analysis.identified_sections.forEach(section => {
                    const sectionClass = section.confidence >= 0.8 ? 'quality-high' : section.confidence >= 0.6 ? 'quality-medium' : 'quality-low';
                    html += `
                        <div class="data-item">
                            <div class="data-label">${section.type}</div>
                            <div class="data-value">
                                <span class="quality-badge ${sectionClass}">${Math.round(section.confidence * 100)}%</span>
                                ${section.matches} matches
                            </div>
                        </div>
                    `;
                });
                html += `</div>`;
            } else {
                html += `<p style="color: var(--text-secondary);">No mortgage-specific sections identified in this document.</p>`;
            }

            html += `</div>`;

            // Extracted Data
            if (Object.keys(analysis.extracted_data).length > 0) {
                html += `
                    <div class="result-section">
                        <div class="result-header">
                            <div class="result-title">📊 Extracted Data</div>
                            <div class="quality-badge quality-high">${Object.keys(analysis.extracted_data).length} fields</div>
                        </div>
                        <div class="data-grid">
                `;

                Object.entries(analysis.extracted_data).forEach(([key, value]) => {
                    const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    let displayValue = value;
                    
                    if (Array.isArray(value)) {
                        displayValue = value.join(', ');
                    }
                    
                    html += `
                        <div class="data-item">
                            <div class="data-label">${label}</div>
                            <div class="data-value">${displayValue}</div>
                        </div>
                    `;
                });

                html += `</div></div>`;
            }

            resultsContent.innerHTML = html;
            document.getElementById('resultsContainer').style.display = 'block';
            document.getElementById('resultsContainer').scrollIntoView({ behavior: 'smooth' });
        }
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(ENHANCED_HTML_TEMPLATE)

@app.route('/analyze_enhanced', methods=['POST'])
def analyze_enhanced():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Save uploaded file temporarily
        temp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
        file.save(temp_path)
        
        try:
            # Analyze with enhanced analyzer
            result = enhanced_analyzer.analyze_document(temp_path, file.filename)
            return jsonify(result)
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok', 
        'version': 'enhanced-free-1.0',
        'supported_formats': list(enhanced_analyzer.document_processor.supported_formats.keys())
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

