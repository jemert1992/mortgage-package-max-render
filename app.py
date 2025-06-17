#!/usr/bin/env python3
"""
Complete Mortgage Package Analyzer with Maximum OCR Features
Optimized for Render.com deployment
"""

import os
import io
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import traceback
import re
import threading
import time

# Flask imports
from flask import Flask, request, jsonify, render_template_string, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

# PDF processing imports
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mortgage-analyzer-secret-key-2024')
CORS(app)

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_TIMEOUT = 300  # 5 minutes

# Global progress tracking
progress_store = {}
progress_lock = threading.Lock()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_progress(session_id: str, current: int, total: int, message: str = ""):
    """Update progress for a session"""
    with progress_lock:
        progress_store[session_id] = {
            'current': current,
            'total': total,
            'percentage': int((current / total) * 100) if total > 0 else 0,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }

def get_progress(session_id: str) -> Dict:
    """Get progress for a session"""
    with progress_lock:
        return progress_store.get(session_id, {
            'current': 0,
            'total': 0,
            'percentage': 0,
            'message': 'Ready',
            'timestamp': datetime.now().isoformat()
        })

class MortgageAnalyzer:
    """Advanced mortgage document analyzer with maximum OCR capabilities"""
    
    def __init__(self):
        self.section_patterns = {
            'Mortgage': {
                'patterns': [
                    r'mortgage\s+(?:deed|document|agreement)',
                    r'security\s+instrument',
                    r'deed\s+of\s+trust',
                    r'mortgage\s+note',
                    r'this\s+mortgage',
                    r'mortgagor\s+and\s+mortgagee'
                ],
                'priority': 10,
                'keywords': ['mortgage', 'mortgagor', 'mortgagee', 'lien', 'security', 'property']
            },
            'Promissory Note': {
                'patterns': [
                    r'promissory\s+note',
                    r'note\s+(?:dated|payable)',
                    r'borrower\s+promises\s+to\s+pay',
                    r'principal\s+amount',
                    r'interest\s+rate',
                    r'payment\s+schedule'
                ],
                'priority': 10,
                'keywords': ['promissory', 'note', 'borrower', 'lender', 'principal', 'interest']
            },
            'Lenders Closing Instructions Guaranty': {
                'patterns': [
                    r'lender(?:s)?\s+closing\s+instructions',
                    r'closing\s+instructions\s+guaranty',
                    r'title\s+company\s+instructions',
                    r'escrow\s+instructions',
                    r'closing\s+agent\s+instructions'
                ],
                'priority': 9,
                'keywords': ['closing', 'instructions', 'guaranty', 'title', 'escrow']
            },
            'Settlement Statement': {
                'patterns': [
                    r'settlement\s+statement',
                    r'hud-1\s+settlement',
                    r'closing\s+disclosure',
                    r'settlement\s+charges',
                    r'borrower\s+charges',
                    r'seller\s+charges'
                ],
                'priority': 9,
                'keywords': ['settlement', 'hud-1', 'closing', 'charges', 'borrower', 'seller']
            },
            'Statement of Anti Coercion Florida': {
                'patterns': [
                    r'statement\s+of\s+anti\s+coercion',
                    r'anti\s+coercion\s+florida',
                    r'florida\s+anti\s+coercion',
                    r'coercion\s+statement',
                    r'florida\s+statute.*coercion'
                ],
                'priority': 8,
                'keywords': ['anti', 'coercion', 'florida', 'statement', 'statute']
            },
            'Correction Agreement and Limited Power of Attorney': {
                'patterns': [
                    r'correction\s+agreement',
                    r'limited\s+power\s+of\s+attorney',
                    r'power\s+of\s+attorney.*correction',
                    r'correction.*power\s+of\s+attorney',
                    r'limited\s+poa'
                ],
                'priority': 8,
                'keywords': ['correction', 'agreement', 'power', 'attorney', 'limited']
            },
            'All Purpose Acknowledgment': {
                'patterns': [
                    r'all\s+purpose\s+acknowledgment',
                    r'general\s+acknowledgment',
                    r'notary\s+acknowledgment',
                    r'acknowledgment\s+of\s+signature',
                    r'sworn\s+to\s+and\s+subscribed'
                ],
                'priority': 8,
                'keywords': ['acknowledgment', 'notary', 'sworn', 'subscribed', 'signature']
            },
            'Flood Hazard Determination': {
                'patterns': [
                    r'flood\s+hazard\s+determination',
                    r'flood\s+zone\s+determination',
                    r'fema\s+flood\s+map',
                    r'flood\s+insurance\s+requirement',
                    r'special\s+flood\s+hazard\s+area'
                ],
                'priority': 7,
                'keywords': ['flood', 'hazard', 'determination', 'fema', 'insurance']
            },
            'Automatic Payments Authorization': {
                'patterns': [
                    r'automatic\s+payments?\s+authorization',
                    r'ach\s+authorization',
                    r'electronic\s+funds\s+transfer',
                    r'automatic\s+debit\s+authorization',
                    r'recurring\s+payment\s+authorization'
                ],
                'priority': 7,
                'keywords': ['automatic', 'payments', 'authorization', 'ach', 'electronic']
            },
            'Tax Record Information': {
                'patterns': [
                    r'tax\s+record\s+information',
                    r'property\s+tax\s+records',
                    r'tax\s+assessment',
                    r'tax\s+parcel\s+information',
                    r'real\s+estate\s+taxes'
                ],
                'priority': 7,
                'keywords': ['tax', 'record', 'information', 'assessment', 'parcel']
            },
            'Title Policy': {
                'patterns': [
                    r'title\s+(?:insurance\s+)?policy',
                    r'owner(?:s)?\s+title\s+policy',
                    r'lender(?:s)?\s+title\s+policy',
                    r'title\s+commitment',
                    r'title\s+insurance\s+commitment'
                ],
                'priority': 6,
                'keywords': ['title', 'policy', 'insurance', 'commitment', 'owner']
            },
            'Insurance Policy': {
                'patterns': [
                    r'insurance\s+policy',
                    r'homeowner(?:s)?\s+insurance',
                    r'property\s+insurance',
                    r'hazard\s+insurance',
                    r'insurance\s+declaration'
                ],
                'priority': 6,
                'keywords': ['insurance', 'policy', 'homeowner', 'property', 'hazard']
            },
            'Deed': {
                'patterns': [
                    r'warranty\s+deed',
                    r'quit\s+claim\s+deed',
                    r'special\s+warranty\s+deed',
                    r'deed\s+(?:of\s+)?conveyance',
                    r'grant\s+deed'
                ],
                'priority': 6,
                'keywords': ['deed', 'warranty', 'conveyance', 'grant', 'quit']
            },
            'UCC Filing': {
                'patterns': [
                    r'ucc\s+(?:filing|statement)',
                    r'uniform\s+commercial\s+code',
                    r'financing\s+statement',
                    r'ucc-1\s+form',
                    r'security\s+interest\s+filing'
                ],
                'priority': 5,
                'keywords': ['ucc', 'uniform', 'commercial', 'financing', 'security']
            },
            'Signature Page': {
                'patterns': [
                    r'signature\s+page',
                    r'execution\s+page',
                    r'borrower(?:s)?\s+signature',
                    r'lender(?:s)?\s+signature',
                    r'witness\s+signature'
                ],
                'priority': 5,
                'keywords': ['signature', 'execution', 'borrower', 'lender', 'witness']
            },
            'Affidavit': {
                'patterns': [
                    r'affidavit',
                    r'sworn\s+statement',
                    r'affirmation',
                    r'declaration\s+under\s+penalty',
                    r'notarized\s+statement'
                ],
                'priority': 5,
                'keywords': ['affidavit', 'sworn', 'statement', 'declaration', 'notarized']
            }
        }
    
    def preprocess_image(self, image: Image.Image) -> List[Image.Image]:
        """Apply multiple preprocessing techniques to improve OCR accuracy"""
        processed_images = []
        
        # Original image
        processed_images.append(image)
        
        # High contrast version
        enhancer = ImageEnhance.Contrast(image)
        high_contrast = enhancer.enhance(2.0)
        processed_images.append(high_contrast)
        
        # Sharpened version
        sharpened = image.filter(ImageFilter.SHARPEN)
        processed_images.append(sharpened)
        
        # Grayscale with enhanced contrast
        grayscale = image.convert('L')
        enhancer = ImageEnhance.Contrast(grayscale)
        enhanced_gray = enhancer.enhance(1.5)
        processed_images.append(enhanced_gray)
        
        return processed_images
    
    def extract_text_with_ocr(self, pdf_bytes: bytes, session_id: str) -> Tuple[str, List[Dict]]:
        """Extract text using multiple OCR strategies for maximum accuracy"""
        all_text = []
        page_details = []
        
        try:
            # Convert PDF to images
            update_progress(session_id, 1, 10, "Converting PDF to images...")
            images = convert_from_bytes(pdf_bytes, dpi=200, fmt='PNG')
            total_pages = len(images)
            
            update_progress(session_id, 2, 10, f"Processing {total_pages} pages with advanced OCR...")
            
            for page_num, image in enumerate(images, 1):
                page_text_variants = []
                
                # Apply multiple preprocessing techniques
                processed_images = self.preprocess_image(image)
                
                # Try different OCR configurations on each processed image
                ocr_configs = [
                    '--psm 1 --oem 3',  # Automatic page segmentation with orientation
                    '--psm 3 --oem 3',  # Fully automatic page segmentation
                    '--psm 6 --oem 3',  # Uniform block of text
                    '--psm 4 --oem 3'   # Single column of text
                ]
                
                for img_variant in processed_images:
                    for config in ocr_configs:
                        try:
                            text = pytesseract.image_to_string(img_variant, config=config)
                            if text.strip():
                                page_text_variants.append(text)
                        except Exception as e:
                            logger.warning(f"OCR config {config} failed for page {page_num}: {e}")
                
                # Select the best text variant (longest with most words)
                best_text = ""
                if page_text_variants:
                    best_text = max(page_text_variants, key=lambda x: len(x.split()))
                
                all_text.append(best_text)
                page_details.append({
                    'page': page_num,
                    'text_length': len(best_text),
                    'word_count': len(best_text.split()),
                    'variants_tried': len(page_text_variants)
                })
                
                # Update progress
                progress = int((page_num / total_pages) * 6) + 2  # Pages 2-8 of 10
                update_progress(session_id, progress, 10, f"OCR processing page {page_num} of {total_pages}...")
            
            return '\n\n'.join(all_text), page_details
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise Exception(f"OCR processing failed: {str(e)}")
    
    def extract_text_with_pdfplumber(self, pdf_bytes: bytes, session_id: str) -> Tuple[str, List[Dict]]:
        """Extract text using pdfplumber for text-based PDFs"""
        all_text = []
        page_details = []
        
        try:
            update_progress(session_id, 1, 10, "Analyzing PDF structure...")
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total_pages = len(pdf.pages)
                update_progress(session_id, 2, 10, f"Extracting text from {total_pages} pages...")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text() or ""
                        all_text.append(text)
                        page_details.append({
                            'page': page_num,
                            'text_length': len(text),
                            'word_count': len(text.split()),
                            'method': 'pdfplumber'
                        })
                        
                        # Update progress
                        progress = int((page_num / total_pages) * 6) + 2  # Pages 2-8 of 10
                        update_progress(session_id, progress, 10, f"Extracting text from page {page_num} of {total_pages}...")
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
                        all_text.append("")
                        page_details.append({
                            'page': page_num,
                            'text_length': 0,
                            'word_count': 0,
                            'method': 'pdfplumber',
                            'error': str(e)
                        })
            
            return '\n\n'.join(all_text), page_details
            
        except Exception as e:
            logger.error(f"PDFplumber extraction failed: {e}")
            raise Exception(f"PDF text extraction failed: {str(e)}")
    
    def analyze_sections(self, text: str, page_details: List[Dict], session_id: str) -> List[Dict]:
        """Analyze text to identify mortgage document sections"""
        update_progress(session_id, 9, 10, "Analyzing document sections...")
        
        sections_found = []
        text_lower = text.lower()
        
        # Split text into pages for page number tracking
        pages = text.split('\n\n')
        
        for section_name, section_info in self.section_patterns.items():
            best_match = None
            best_confidence = 0
            
            # Check each pattern
            for pattern in section_info['patterns']:
                matches = list(re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE))
                
                for match in matches:
                    # Calculate confidence based on pattern match and keyword density
                    confidence = 50  # Base confidence for pattern match
                    
                    # Find the page containing this match
                    char_pos = match.start()
                    page_num = 1
                    current_pos = 0
                    
                    for i, page_text in enumerate(pages):
                        if current_pos <= char_pos < current_pos + len(page_text):
                            page_num = i + 1
                            break
                        current_pos += len(page_text) + 2  # +2 for '\n\n'
                    
                    # Extract context around the match
                    context_start = max(0, match.start() - 200)
                    context_end = min(len(text), match.end() + 200)
                    context = text[context_start:context_end].lower()
                    
                    # Boost confidence based on keyword presence
                    keyword_count = sum(1 for keyword in section_info['keywords'] if keyword in context)
                    confidence += keyword_count * 10
                    
                    # Boost confidence based on section priority
                    confidence += section_info['priority'] * 2
                    
                    # Limit confidence to 100
                    confidence = min(confidence, 100)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = {
                            'section': section_name,
                            'confidence': confidence,
                            'page': page_num,
                            'pattern_matched': pattern,
                            'context': text[context_start:context_end][:100] + "...",
                            'priority': section_info['priority']
                        }
            
            if best_match and best_confidence >= 40:  # Minimum confidence threshold
                sections_found.append(best_match)
        
        # Sort by priority (higher first) then by confidence
        sections_found.sort(key=lambda x: (-x['priority'], -x['confidence']))
        
        update_progress(session_id, 10, 10, f"Analysis complete! Found {len(sections_found)} sections.")
        
        return sections_found
    
    def analyze_document(self, pdf_bytes: bytes, session_id: str) -> Dict:
        """Main document analysis function"""
        try:
            update_progress(session_id, 0, 10, "Starting document analysis...")
            
            # Try pdfplumber first (faster for text-based PDFs)
            try:
                text, page_details = self.extract_text_with_pdfplumber(pdf_bytes, session_id)
                
                # Check if we got meaningful text
                total_words = sum(detail.get('word_count', 0) for detail in page_details)
                if total_words < 50:  # If very little text, try OCR
                    update_progress(session_id, 2, 10, "PDF appears to be image-based, switching to OCR...")
                    text, page_details = self.extract_text_with_ocr(pdf_bytes, session_id)
                    extraction_method = "OCR (image-based PDF)"
                else:
                    extraction_method = "pdfplumber (text-based PDF)"
                    
            except Exception as e:
                logger.warning(f"pdfplumber failed, trying OCR: {e}")
                text, page_details = self.extract_text_with_ocr(pdf_bytes, session_id)
                extraction_method = "OCR (fallback)"
            
            # Analyze sections
            sections = self.analyze_sections(text, page_details, session_id)
            
            return {
                'success': True,
                'extraction_method': extraction_method,
                'total_pages': len(page_details),
                'total_text_length': len(text),
                'total_words': len(text.split()),
                'sections_found': len(sections),
                'sections': sections,
                'page_details': page_details,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }

# Initialize analyzer
analyzer = MortgageAnalyzer()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Complete Mortgage Package Analyzer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .main-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .upload-section {
            padding: 40px;
            text-align: center;
            background: linear-gradient(45deg, #f8f9fa, #e9ecef);
        }
        
        .upload-area {
            border: 3px dashed #007bff;
            border-radius: 10px;
            padding: 40px 20px;
            margin: 20px 0;
            cursor: pointer;
            transition: all 0.3s ease;
            background: white;
        }
        
        .upload-area:hover {
            border-color: #0056b3;
            background: #f8f9ff;
            transform: translateY(-2px);
        }
        
        .upload-area.dragover {
            border-color: #28a745;
            background: #f8fff8;
        }
        
        .upload-icon {
            font-size: 3rem;
            color: #007bff;
            margin-bottom: 20px;
        }
        
        .upload-text {
            font-size: 1.2rem;
            color: #666;
            margin-bottom: 10px;
        }
        
        .upload-subtext {
            color: #999;
            font-size: 0.9rem;
        }
        
        .file-input {
            display: none;
        }
        
        .btn {
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
            margin: 10px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,123,255,0.3);
        }
        
        .btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }
        
        .progress-section {
            padding: 20px 40px;
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
            display: none;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #28a745, #20c997);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 10px;
        }
        
        .progress-text {
            text-align: center;
            margin: 10px 0;
            font-weight: 500;
        }
        
        .results-section {
            padding: 40px;
            display: none;
        }
        
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .results-title {
            font-size: 1.8rem;
            color: #333;
        }
        
        .results-summary {
            background: linear-gradient(45deg, #28a745, #20c997);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .sections-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .section-card {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        
        .section-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .section-name {
            font-weight: 600;
            color: #333;
            font-size: 1.1rem;
        }
        
        .confidence-badge {
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .confidence-high {
            background: #d4edda;
            color: #155724;
        }
        
        .confidence-medium {
            background: #fff3cd;
            color: #856404;
        }
        
        .confidence-low {
            background: #f8d7da;
            color: #721c24;
        }
        
        .section-details {
            color: #666;
            font-size: 0.9rem;
        }
        
        .section-context {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            font-size: 0.8rem;
            color: #666;
            font-style: italic;
        }
        
        .actions-section {
            padding: 20px 40px;
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
            text-align: center;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #dc3545;
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .upload-section, .results-section {
                padding: 20px;
            }
            
            .sections-grid {
                grid-template-columns: 1fr;
            }
            
            .results-header {
                flex-direction: column;
                gap: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Complete Mortgage Package Analyzer</h1>
            <p>Advanced OCR-powered document analysis for mortgage packages</p>
        </div>
        
        <div class="main-card">
            <div class="upload-section">
                <div class="upload-area" id="uploadArea">
                    <div class="upload-icon">📄</div>
                    <div class="upload-text">Drop your mortgage package PDF here</div>
                    <div class="upload-subtext">or click to browse (up to 100MB)</div>
                </div>
                <input type="file" id="fileInput" class="file-input" accept=".pdf">
                <button class="btn" onclick="document.getElementById('fileInput').click()">
                    Choose PDF File
                </button>
                <button class="btn" id="analyzeBtn" onclick="analyzeDocument()" disabled>
                    🔍 Analyze Document
                </button>
            </div>
            
            <div class="progress-section" id="progressSection">
                <div class="progress-text" id="progressText">Preparing analysis...</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div id="progressPercentage">0%</div>
            </div>
            
            <div class="results-section" id="resultsSection">
                <div class="results-header">
                    <div class="results-title">📋 Analysis Results</div>
                    <div class="results-summary" id="resultsSummary">
                        0 sections identified
                    </div>
                </div>
                
                <div class="stats-grid" id="statsGrid">
                    <!-- Stats will be populated here -->
                </div>
                
                <div class="sections-grid" id="sectionsGrid">
                    <!-- Sections will be populated here -->
                </div>
            </div>
            
            <div class="actions-section">
                <button class="btn" onclick="resetAnalyzer()">
                    🔄 Analyze Another Document
                </button>
                <button class="btn" id="generateTocBtn" onclick="generateTableOfContents()" style="display: none;">
                    📑 Generate Table of Contents
                </button>
            </div>
        </div>
    </div>

    <script>
        (function() {
            let selectedFile = null;
            let analysisResults = null;
            let progressInterval = null;
            
            // File upload handling
            const fileInput = document.getElementById('fileInput');
            const uploadArea = document.getElementById('uploadArea');
            const analyzeBtn = document.getElementById('analyzeBtn');
            
            fileInput.addEventListener('change', handleFileSelect);
            uploadArea.addEventListener('click', () => fileInput.click());
            uploadArea.addEventListener('dragover', handleDragOver);
            uploadArea.addEventListener('dragleave', handleDragLeave);
            uploadArea.addEventListener('drop', handleDrop);
            
            function handleFileSelect(event) {
                const file = event.target.files[0];
                if (file) {
                    validateAndSetFile(file);
                }
            }
            
            function handleDragOver(event) {
                event.preventDefault();
                uploadArea.classList.add('dragover');
            }
            
            function handleDragLeave(event) {
                event.preventDefault();
                uploadArea.classList.remove('dragover');
            }
            
            function handleDrop(event) {
                event.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = event.dataTransfer.files;
                if (files.length > 0) {
                    validateAndSetFile(files[0]);
                }
            }
            
            function validateAndSetFile(file) {
                if (file.type !== 'application/pdf') {
                    showError('Please select a PDF file.');
                    return;
                }
                
                if (file.size > 100 * 1024 * 1024) {
                    showError('File size must be less than 100MB.');
                    return;
                }
                
                selectedFile = file;
                analyzeBtn.disabled = false;
                uploadArea.querySelector('.upload-text').textContent = `Selected: ${file.name}`;
                uploadArea.querySelector('.upload-subtext').textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
                hideError();
            }
            
            window.analyzeDocument = function() {
                if (!selectedFile) {
                    showError('Please select a PDF file first.');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', selectedFile);
                
                // Show progress section
                document.getElementById('progressSection').style.display = 'block';
                document.getElementById('resultsSection').style.display = 'none';
                analyzeBtn.disabled = true;
                
                // Start progress monitoring
                startProgressMonitoring();
                
                fetch('/analyze', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    stopProgressMonitoring();
                    if (data.success) {
                        displayResults(data);
                    } else {
                        showError(`Analysis failed: ${data.error}`);
                        document.getElementById('progressSection').style.display = 'none';
                    }
                    analyzeBtn.disabled = false;
                })
                .catch(error => {
                    stopProgressMonitoring();
                    showError(`Network error: ${error.message}`);
                    document.getElementById('progressSection').style.display = 'none';
                    analyzeBtn.disabled = false;
                });
            };
            
            function startProgressMonitoring() {
                progressInterval = setInterval(() => {
                    fetch('/progress')
                        .then(response => response.json())
                        .then(data => {
                            updateProgress(data.percentage, data.message);
                        })
                        .catch(error => {
                            console.error('Progress monitoring error:', error);
                        });
                }, 1000);
            }
            
            function stopProgressMonitoring() {
                if (progressInterval) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                }
            }
            
            function updateProgress(percentage, message) {
                document.getElementById('progressFill').style.width = percentage + '%';
                document.getElementById('progressPercentage').textContent = percentage + '%';
                document.getElementById('progressText').textContent = message || 'Processing...';
            }
            
            function displayResults(data) {
                analysisResults = data;
                
                // Hide progress, show results
                document.getElementById('progressSection').style.display = 'none';
                document.getElementById('resultsSection').style.display = 'block';
                
                // Update summary
                document.getElementById('resultsSummary').textContent = 
                    `${data.sections_found} sections identified`;
                
                // Display stats
                displayStats(data);
                
                // Display sections
                displaySections(data.sections);
                
                // Show generate TOC button if sections found
                if (data.sections_found > 0) {
                    document.getElementById('generateTocBtn').style.display = 'inline-block';
                }
            }
            
            function displayStats(data) {
                const statsGrid = document.getElementById('statsGrid');
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-number">${data.total_pages}</div>
                        <div class="stat-label">Total Pages</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${data.sections_found}</div>
                        <div class="stat-label">Sections Found</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${(data.total_words || 0).toLocaleString()}</div>
                        <div class="stat-label">Words Processed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${data.extraction_method.includes('OCR') ? 'OCR' : 'Text'}</div>
                        <div class="stat-label">Extraction Method</div>
                    </div>
                `;
            }
            
            function displaySections(sections) {
                const sectionsGrid = document.getElementById('sectionsGrid');
                
                if (!sections || sections.length === 0) {
                    sectionsGrid.innerHTML = '<div class="error-message">No mortgage sections were identified in this document.</div>';
                    return;
                }
                
                sectionsGrid.innerHTML = sections.map(section => {
                    const confidenceClass = section.confidence >= 80 ? 'confidence-high' : 
                                          section.confidence >= 60 ? 'confidence-medium' : 'confidence-low';
                    
                    return `
                        <div class="section-card">
                            <div class="section-header">
                                <div class="section-name">${section.section}</div>
                                <div class="confidence-badge ${confidenceClass}">
                                    ${section.confidence}% confidence
                                </div>
                            </div>
                            <div class="section-details">
                                <strong>Page:</strong> ${section.page}<br>
                                <strong>Pattern:</strong> ${section.pattern_matched}<br>
                                <strong>Priority:</strong> ${section.priority}/10
                            </div>
                            <div class="section-context">
                                "${section.context}"
                            </div>
                        </div>
                    `;
                }).join('');
            }
            
            window.generateTableOfContents = function() {
                if (!analysisResults || !analysisResults.sections) {
                    showError('No analysis results available.');
                    return;
                }
                
                const sections = analysisResults.sections.sort((a, b) => a.page - b.page);
                const toc = sections.map(section => 
                    `${section.section} ........................ Page ${section.page}`
                ).join('\n');
                
                const tocContent = `MORTGAGE PACKAGE TABLE OF CONTENTS\n\nGenerated: ${new Date().toLocaleString()}\nTotal Sections: ${sections.length}\n\n${toc}`;
                
                const blob = new Blob([tocContent], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'mortgage_package_toc.txt';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            };
            
            window.resetAnalyzer = function() {
                selectedFile = null;
                analysisResults = null;
                fileInput.value = '';
                analyzeBtn.disabled = true;
                
                document.getElementById('progressSection').style.display = 'none';
                document.getElementById('resultsSection').style.display = 'none';
                document.getElementById('generateTocBtn').style.display = 'none';
                
                uploadArea.querySelector('.upload-text').textContent = 'Drop your mortgage package PDF here';
                uploadArea.querySelector('.upload-subtext').textContent = 'or click to browse (up to 100MB)';
                
                hideError();
            };
            
            function showError(message) {
                const existingError = document.querySelector('.error-message');
                if (existingError) {
                    existingError.remove();
                }
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = message;
                
                const uploadSection = document.querySelector('.upload-section');
                uploadSection.appendChild(errorDiv);
            }
            
            function hideError() {
                const existingError = document.querySelector('.error-message');
                if (existingError) {
                    existingError.remove();
                }
            }
            
            console.log('Complete Mortgage Analyzer loaded successfully!');
        })();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main application page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze uploaded PDF document"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Only PDF files are allowed'})
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB'})
        
        # Generate session ID for progress tracking
        session_id = str(uuid.uuid4())
        session['analysis_session'] = session_id
        
        # Read file content
        pdf_bytes = file.read()
        
        # Analyze document
        result = analyzer.analyze_document(pdf_bytes, session_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Analysis endpoint error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Document processing error: {str(e)}'
        }), 500

@app.route('/progress')
def progress():
    """Get analysis progress"""
    session_id = session.get('analysis_session', 'default')
    progress_data = get_progress(session_id)
    return jsonify(progress_data)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'features': ['OCR', 'Pattern Matching', 'Progress Tracking']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

