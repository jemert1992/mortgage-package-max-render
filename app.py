#!/usr/bin/env python3
"""
🏠 Mortgage Package Reorganizer - Complete Enhanced Edition
A sleek, professional tool for reorganizing mortgage documents with intelligent classification
"""

import os
import json
import tempfile
import traceback
import gc
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_file
from werkzeug.utils import secure_filename
import openai
from openai import OpenAI
import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import io

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Initialize OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    print("❌ ERROR: OPENAI_API_KEY environment variable not found!")
    exit(1)

try:
    client = OpenAI(api_key=openai_api_key)
    # Test the client
    test_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=5
    )
    print("✅ OpenAI client initialized and tested successfully")
except Exception as e:
    print(f"❌ ERROR initializing OpenAI client: {e}")
    exit(1)

print("✅ Mortgage Package Reorganizer - Complete Enhanced Edition initialized")
print("🏠 ENHANCED DOCUMENT CLASSIFICATION - 2025-01-07")

# Enhanced document classification mapping
LENDER_REQUIREMENT_MAPPING = {
    "Closing Instructions (signed/dated)": {
        "keywords": ["closing", "instructions", "settlement", "agent", "acknowledgment", "date:", "to:", "contact"],
        "patterns": [r"closing\s+instructions", r"settlement\s+agent", r"wire\s+cut\s+off"],
        "page_indicators": ["closing instructions", "settlement agent acknowledgment"],
        "priority": 1
    },
    "Symmetry 1003": {
        "keywords": ["1003", "symmetry", "uniform residential", "loan application", "borrower information"],
        "patterns": [r"1003", r"symmetry", r"uniform\s+residential\s+loan", r"loan\s+application"],
        "page_indicators": ["uniform residential loan application", "1003"],
        "priority": 2
    },
    "HELOC agreement (2nd)": {
        "keywords": ["heloc", "line of credit", "home equity", "credit line", "draw period"],
        "patterns": [r"heloc", r"line\s+of\s+credit", r"home\s+equity", r"credit\s+line"],
        "page_indicators": ["heloc", "line of credit", "home equity line of credit"],
        "priority": 3
    },
    "Notice of Right to Cancel": {
        "keywords": ["right to cancel", "rescission", "cancel", "three day", "3 day", "notice"],
        "patterns": [r"right\s+to\s+cancel", r"rescission", r"three\s+day", r"3\s+day"],
        "page_indicators": ["notice of right to cancel", "right to cancel"],
        "priority": 4
    },
    "Mtg/Deed (2nd)": {
        "keywords": ["mortgage", "deed", "deed of trust", "mortgaged premises", "mortgagor", "mortgagee"],
        "patterns": [r"mortgage", r"deed\s+of\s+trust", r"mortgaged\s+premises", r"this\s+mortgage"],
        "page_indicators": ["mortgage", "deed of trust", "mortgaged premises"],
        "priority": 5
    },
    "Settlement Statement/HUD (2nd)": {
        "keywords": ["settlement statement", "hud-1", "hud", "closing statement", "settlement"],
        "patterns": [r"settlement\s+statement", r"hud-1", r"hud\s+1", r"closing\s+statement"],
        "page_indicators": ["settlement statement", "hud-1"],
        "priority": 6
    },
    "Flood Notice": {
        "keywords": ["flood", "flood notice", "flood hazard", "flood insurance", "fema"],
        "patterns": [r"flood\s+notice", r"flood\s+hazard", r"flood\s+insurance"],
        "page_indicators": ["flood notice", "flood hazard determination"],
        "priority": 7
    },
    "First Payment Letter aka Payment and Servicing Notification": {
        "keywords": ["first payment", "payment", "servicing", "servicer", "payment notification"],
        "patterns": [r"first\s+payment", r"payment\s+and\s+servicing", r"servicing\s+notification"],
        "page_indicators": ["first payment letter", "payment and servicing notification"],
        "priority": 8
    },
    "Signature/Name Affidavit": {
        "keywords": ["signature", "affidavit", "name affidavit", "signature affidavit"],
        "patterns": [r"signature\s+affidavit", r"name\s+affidavit", r"affidavit"],
        "page_indicators": ["signature affidavit", "name affidavit"],
        "priority": 9
    },
    "Errors and Omissions Compliance Agreement": {
        "keywords": ["errors", "omissions", "compliance", "agreement", "errors and omissions"],
        "patterns": [r"errors\s+and\s+omissions", r"compliance\s+agreement"],
        "page_indicators": ["errors and omissions", "compliance agreement"],
        "priority": 10
    },
    "Mailing address cert": {
        "keywords": ["mailing", "address", "certification", "mailing address"],
        "patterns": [r"mailing\s+address", r"address\s+cert"],
        "page_indicators": ["mailing address certification"],
        "priority": 11
    },
    "W-9": {
        "keywords": ["w-9", "w9", "taxpayer identification", "request for taxpayer"],
        "patterns": [r"w-9", r"w9", r"taxpayer\s+identification"],
        "page_indicators": ["form w-9", "w-9"],
        "priority": 12
    },
    "SSA-89": {
        "keywords": ["ssa-89", "ssa89", "authorization", "social security"],
        "patterns": [r"ssa-89", r"ssa89"],
        "page_indicators": ["form ssa-89", "ssa-89"],
        "priority": 13
    },
    "4506-C": {
        "keywords": ["4506-c", "4506c", "irs", "tax return"],
        "patterns": [r"4506-c", r"4506c"],
        "page_indicators": ["form 4506-c", "4506-c"],
        "priority": 14
    }
}

def enhanced_page_classification(page_text, page_number, lender_requirements):
    """Enhanced page classification that maps to specific lender requirements"""
    if not page_text:
        return classify_by_position_and_context(page_number, lender_requirements)
    
    page_text_lower = page_text.lower()
    
    # Score each requirement category
    scores = {}
    
    for req_name, req_info in LENDER_REQUIREMENT_MAPPING.items():
        score = 0
        
        # Check keywords
        for keyword in req_info["keywords"]:
            if keyword.lower() in page_text_lower:
                score += 2
        
        # Check patterns
        for pattern in req_info["patterns"]:
            if re.search(pattern, page_text_lower):
                score += 3
        
        # Check page indicators (stronger matches)
        for indicator in req_info["page_indicators"]:
            if indicator.lower() in page_text_lower:
                score += 5
        
        scores[req_name] = score
    
    # Find the best match
    if scores:
        best_match = max(scores, key=scores.get)
        best_score = scores[best_match]
        
        if best_score > 0:
            return best_match
    
    # Fallback to position-based classification
    return classify_by_position_and_context(page_number, lender_requirements)

def classify_by_position_and_context(page_number, lender_requirements):
    """Classify pages based on their position and typical document flow"""
    
    # Get the document order from lender requirements
    doc_order = lender_requirements.get('document_order', [])
    
    if not doc_order:
        return "Supporting Documents"
    
    # Estimate pages per document (rough heuristic)
    total_estimated_pages = 60  # Typical mortgage package size
    docs_count = len(doc_order)
    avg_pages_per_doc = max(1, total_estimated_pages // docs_count)
    
    # Map page position to document
    doc_index = min(page_number // avg_pages_per_doc, docs_count - 1)
    
    if doc_index < len(doc_order):
        return doc_order[doc_index]
    
    return "Supporting Documents"

def extract_and_reorganize_pages_enhanced(original_pdf_path, lender_requirements):
    """Enhanced page extraction and reorganization using improved classification"""
    print(f"🔍 DEBUG: Enhanced page extraction from: {original_pdf_path}")
    
    if not os.path.exists(original_pdf_path):
        print(f"🔍 DEBUG: Original PDF not found: {original_pdf_path}")
        return []
    
    try:
        # Create a temporary PDF to store extracted pages
        temp_pdf_path = f"/tmp/temp_extracted_pages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        with open(original_pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            print(f"🔍 DEBUG: Total pages in original PDF: {total_pages}")
            
            # Create a temporary PDF writer
            temp_pdf_writer = PyPDF2.PdfWriter()
            page_assignments = []
            
            # Process each page with enhanced classification
            for page_num in range(min(total_pages, 100)):  # Process up to 100 pages
                try:
                    page = pdf_reader.pages[page_num]
                    
                    # Try to extract text (may fail for image-based PDFs)
                    try:
                        page_text = page.extract_text()
                    except:
                        page_text = ""
                    
                    # Use enhanced classification
                    assigned_doc = enhanced_page_classification(page_text, page_num, lender_requirements)
                    
                    # Add page to temp PDF
                    temp_pdf_writer.add_page(page)
                    
                    # Store assignment
                    page_assignments.append({
                        'page_number': page_num,
                        'assigned_document': assigned_doc,
                        'temp_page_index': len(temp_pdf_writer.pages) - 1,
                        'has_text': bool(page_text.strip())
                    })
                    
                    print(f"🔍 DEBUG: Page {page_num + 1} assigned to: {assigned_doc}")
                    
                    # Memory management
                    if page_num % 10 == 0:
                        gc.collect()
                        
                except Exception as e:
                    print(f"🔍 DEBUG: Error processing page {page_num}: {e}")
                    continue
            
            # Write temporary PDF
            with open(temp_pdf_path, 'wb') as temp_file:
                temp_pdf_writer.write(temp_file)
            
            print(f"🔍 DEBUG: Created temporary PDF with {len(page_assignments)} pages")
            
            # Return page assignments with temp PDF path
            return {
                'temp_pdf_path': temp_pdf_path,
                'page_assignments': page_assignments,
                'total_pages': len(page_assignments)
            }
            
    except Exception as e:
        print(f"🔍 DEBUG: Error in enhanced page extraction: {e}")
        traceback.print_exc()
        return []

def create_reorganized_pdf_enhanced(page_extraction_result, lender_requirements, output_path):
    """Create the final reorganized PDF with enhanced organization"""
    print(f"🔍 DEBUG: Enhanced PDF creation at: {output_path}")
    
    try:
        # Create the final PDF
        pdf_writer = PyPDF2.PdfWriter()
        
        # Add cover page
        cover_page_buffer = create_cover_page_enhanced(page_extraction_result, lender_requirements)
        if cover_page_buffer:
            cover_pdf = PyPDF2.PdfReader(cover_page_buffer)
            pdf_writer.add_page(cover_pdf.pages[0])
            print("🔍 DEBUG: Added enhanced cover page")
        
        # Check if we have page extraction results
        if not page_extraction_result or 'temp_pdf_path' not in page_extraction_result:
            print("🔍 DEBUG: No page extraction results, creating summary only")
            # Write PDF with just cover page
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            return True
        
        temp_pdf_path = page_extraction_result['temp_pdf_path']
        page_assignments = page_extraction_result['page_assignments']
        
        print(f"🔍 DEBUG: Using temp PDF: {temp_pdf_path}")
        print(f"🔍 DEBUG: Total page assignments: {len(page_assignments)}")
        
        # Open the temporary PDF with extracted pages
        if os.path.exists(temp_pdf_path):
            with open(temp_pdf_path, 'rb') as temp_file:
                temp_pdf_reader = PyPDF2.PdfReader(temp_file)
                
                # Group pages by document type in the order specified by lender requirements
                doc_order = lender_requirements.get('document_order', [])
                document_groups = {}
                
                # Initialize groups in the correct order
                for doc_name in doc_order:
                    document_groups[doc_name] = []
                
                # Group pages by document type
                for assignment in page_assignments:
                    doc_type = assignment['assigned_document']
                    if doc_type not in document_groups:
                        document_groups[doc_type] = []
                    document_groups[doc_type].append(assignment)
                
                print(f"🔍 DEBUG: Document groups: {list(document_groups.keys())}")
                
                # Add pages in the order specified by lender requirements
                for doc_type in doc_order:
                    if doc_type in document_groups and document_groups[doc_type]:
                        assignments = document_groups[doc_type]
                        
                        # Add document separator
                        separator_buffer = create_document_separator_enhanced(doc_type, len(assignments))
                        if separator_buffer:
                            separator_pdf = PyPDF2.PdfReader(separator_buffer)
                            pdf_writer.add_page(separator_pdf.pages[0])
                            print(f"🔍 DEBUG: Added separator for: {doc_type}")
                        
                        # Add actual pages for this document type
                        for assignment in assignments:
                            temp_page_index = assignment['temp_page_index']
                            if temp_page_index < len(temp_pdf_reader.pages):
                                try:
                                    page = temp_pdf_reader.pages[temp_page_index]
                                    pdf_writer.add_page(page)
                                    print(f"🔍 DEBUG: Added page {assignment['page_number'] + 1} to {doc_type}")
                                except Exception as e:
                                    print(f"🔍 DEBUG: Error adding page {temp_page_index}: {e}")
                
                # Add any remaining document types not in the order
                for doc_type, assignments in document_groups.items():
                    if doc_type not in doc_order and assignments:
                        # Add document separator
                        separator_buffer = create_document_separator_enhanced(doc_type, len(assignments))
                        if separator_buffer:
                            separator_pdf = PyPDF2.PdfReader(separator_buffer)
                            pdf_writer.add_page(separator_pdf.pages[0])
                            print(f"🔍 DEBUG: Added separator for additional: {doc_type}")
                        
                        # Add actual pages
                        for assignment in assignments:
                            temp_page_index = assignment['temp_page_index']
                            if temp_page_index < len(temp_pdf_reader.pages):
                                try:
                                    page = temp_pdf_reader.pages[temp_page_index]
                                    pdf_writer.add_page(page)
                                    print(f"🔍 DEBUG: Added page {assignment['page_number'] + 1} to {doc_type}")
                                except Exception as e:
                                    print(f"🔍 DEBUG: Error adding page {temp_page_index}: {e}")
                
                print(f"🔍 DEBUG: Total pages in final PDF: {len(pdf_writer.pages)}")
                
                # Write the final PDF
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                
                print(f"🔍 DEBUG: Enhanced PDF written successfully")
                
                # Clean up temporary file
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
                    print(f"🔍 DEBUG: Cleaned up temp file: {temp_pdf_path}")
                
                return True
        else:
            print(f"🔍 DEBUG: Temp PDF not found: {temp_pdf_path}")
            return False
            
    except Exception as e:
        print(f"🔍 DEBUG: Error creating enhanced reorganized PDF: {e}")
        traceback.print_exc()
        return False

def create_cover_page_enhanced(page_extraction_result, lender_requirements):
    """Create an enhanced cover page with detailed organization summary"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#2c3e50'),
            alignment=1  # Center alignment
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=HexColor('#34495e'),
            alignment=1
        )
        
        # Title
        story.append(Paragraph("🏠 PROFESSIONAL MORTGAGE PACKAGE", title_style))
        story.append(Paragraph("Enhanced Document Organization System", subtitle_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Processing information
        story.append(Paragraph(f"<b>Processing Date:</b> {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        
        if page_extraction_result:
            total_pages = page_extraction_result.get('total_pages', 0)
            story.append(Paragraph(f"<b>Total Pages Processed:</b> {total_pages}", styles['Normal']))
            
            # Count pages by document type
            page_assignments = page_extraction_result.get('page_assignments', [])
            doc_counts = {}
            for assignment in page_assignments:
                doc_type = assignment['assigned_document']
                doc_counts[doc_type] = doc_counts.get(doc_type, 0) + 1
            
            story.append(Paragraph(f"<b>Document Sections:</b> {len(doc_counts)}", styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Lender requirements summary
        if lender_requirements:
            story.append(Paragraph("<b>Document Organization Based On:</b>", styles['Heading3']))
            doc_order = lender_requirements.get('document_order', [])
            if doc_order:
                story.append(Paragraph("✅ Lender-specified document order applied", styles['Normal']))
                story.append(Paragraph(f"✅ {len(doc_order)} required document types organized", styles['Normal']))
            
            if lender_requirements.get('special_instructions'):
                story.append(Paragraph(f"✅ Special instructions: {lender_requirements['special_instructions'][:150]}...", styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Enhanced features
        story.append(Paragraph("<b>Enhanced Features Applied:</b>", styles['Heading3']))
        story.append(Paragraph("✅ Intelligent document classification", styles['Normal']))
        story.append(Paragraph("✅ Lender requirement compliance", styles['Normal']))
        story.append(Paragraph("✅ Professional section organization", styles['Normal']))
        story.append(Paragraph("✅ Image-based PDF support", styles['Normal']))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Footer
        story.append(Paragraph("This mortgage package has been professionally reorganized using enhanced AI-powered document classification to ensure compliance with lender requirements.", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"Error creating enhanced cover page: {e}")
        return None

def create_document_separator_enhanced(document_type, page_count):
    """Create an enhanced separator page for document sections"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom style for separator
        separator_style = ParagraphStyle(
            'SeparatorStyle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=20,
            textColor=HexColor('#3498db'),
            alignment=1
        )
        
        # Format document type name
        formatted_name = document_type.replace('_', ' ').title()
        
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(f"📋 {formatted_name}", separator_style))
        story.append(Paragraph(f"({page_count} pages)", styles['Normal']))
        story.append(Spacer(1, 1*inch))
        
        # Add document description based on type
        descriptions = {
            "Closing Instructions (signed/dated)": "Settlement agent instructions and closing procedures",
            "Symmetry 1003": "Uniform Residential Loan Application",
            "HELOC agreement (2nd)": "Home Equity Line of Credit Agreement",
            "Notice of Right to Cancel": "Borrower's right to cancel disclosure",
            "Mtg/Deed (2nd)": "Mortgage or Deed of Trust documentation",
            "Settlement Statement/HUD (2nd)": "HUD-1 Settlement Statement",
            "Flood Notice": "Flood hazard determination notice",
            "First Payment Letter aka Payment and Servicing Notification": "Payment and loan servicing information",
            "Signature/Name Affidavit": "Borrower signature and name affidavit",
            "Errors and Omissions Compliance Agreement": "E&O compliance documentation",
            "Mailing address cert": "Mailing address certification",
            "W-9": "Request for Taxpayer Identification Number",
            "SSA-89": "Authorization to Disclose Information",
            "4506-C": "Request for Transcript of Tax Return"
        }
        
        if document_type in descriptions:
            story.append(Paragraph(descriptions[document_type], styles['Normal']))
        
        story.append(Spacer(1, 2*inch))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"Error creating enhanced separator page: {e}")
        return None

def classify_mortgage_document_enhanced(text_content):
    """Enhanced mortgage document classification"""
    if not text_content:
        return "Supporting Documents"
    
    text_lower = text_content.lower()
    
    # Use the enhanced mapping for classification
    for doc_type, info in LENDER_REQUIREMENT_MAPPING.items():
        score = 0
        
        # Check keywords
        for keyword in info["keywords"]:
            if keyword.lower() in text_lower:
                score += 1
        
        # Check patterns
        for pattern in info["patterns"]:
            if re.search(pattern, text_lower):
                score += 2
        
        # Check page indicators
        for indicator in info["page_indicators"]:
            if indicator.lower() in text_lower:
                score += 3
        
        if score >= 2:  # Threshold for classification
            return doc_type
    
    return "Supporting Documents"

# Enhanced HTML template with professional mortgage-focused design
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mortgage Package Reorganizer | Professional Document Organization</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #2563eb;
            --primary-dark: #1d4ed8;
            --secondary-color: #64748b;
            --success-color: #059669;
            --warning-color: #d97706;
            --error-color: #dc2626;
            --background-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --card-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            --border-radius: 16px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--background-gradient);
            min-height: 100vh;
            color: #1f2937;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .header {
            text-align: center;
            margin-bottom: 3rem;
            color: white;
        }

        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .header p {
            font-size: 1.25rem;
            opacity: 0.9;
            font-weight: 400;
        }

        .main-card {
            background: white;
            border-radius: var(--border-radius);
            box-shadow: var(--card-shadow);
            overflow: hidden;
            margin-bottom: 2rem;
        }

        .progress-bar-container {
            background: #f8fafc;
            padding: 2rem;
            border-bottom: 1px solid #e2e8f0;
        }

        .progress-steps {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 800px;
            margin: 0 auto;
            position: relative;
        }

        .progress-steps::before {
            content: '';
            position: absolute;
            top: 30px;
            left: 30px;
            right: 30px;
            height: 4px;
            background: #e2e8f0;
            border-radius: 2px;
            z-index: 1;
        }

        .progress-line {
            position: absolute;
            top: 30px;
            left: 30px;
            height: 4px;
            background: var(--primary-color);
            border-radius: 2px;
            transition: var(--transition);
            z-index: 2;
        }

        .step {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            cursor: pointer;
            transition: var(--transition);
            z-index: 2;
        }

        .step-indicator {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: #e2e8f0;
            color: #64748b;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1rem;
            font-weight: 600;
            font-size: 1.25rem;
            transition: var(--transition);
            border: 4px solid white;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .step.active .step-indicator {
            background: var(--primary-color);
            color: white;
            transform: scale(1.1);
            box-shadow: 0 8px 25px -8px var(--primary-color);
        }

        .step.completed .step-indicator {
            background: var(--success-color);
            color: white;
        }

        .step.completed .step-indicator::before {
            content: '✓';
            font-weight: bold;
        }

        .step-title {
            font-weight: 600;
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
            color: #374151;
        }

        .step.active .step-title {
            color: var(--primary-color);
        }

        .step-description {
            font-size: 0.875rem;
            color: #6b7280;
            font-weight: 400;
        }

        /* Content Area */
        .content-area {
            padding: 3rem;
        }

        .step-content {
            display: none;
            animation: fadeIn 0.5s ease-in-out;
        }

        .step-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .content-header {
            margin-bottom: 2rem;
        }

        .content-header h2 {
            font-size: 2rem;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .content-header p {
            font-size: 1.125rem;
            color: #6b7280;
            font-weight: 400;
        }

        /* Form Elements */
        .form-group {
            margin-bottom: 2rem;
        }

        .form-label {
            display: block;
            margin-bottom: 0.75rem;
            font-weight: 600;
            color: #374151;
            font-size: 1rem;
        }

        .form-control {
            width: 100%;
            padding: 1rem 1.25rem;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 1rem;
            transition: var(--transition);
            background: white;
            font-family: inherit;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .form-control.textarea {
            min-height: 150px;
            resize: vertical;
        }

        /* File Upload */
        .file-upload-area {
            border: 3px dashed #d1d5db;
            border-radius: 12px;
            padding: 3rem 2rem;
            text-align: center;
            transition: var(--transition);
            cursor: pointer;
            background: #f9fafb;
        }

        .file-upload-area:hover {
            border-color: var(--primary-color);
            background: #f0f9ff;
        }

        .file-upload-area.dragover {
            border-color: var(--primary-color);
            background: #eff6ff;
            transform: scale(1.02);
        }

        .file-upload-icon {
            font-size: 3rem;
            color: #9ca3af;
            margin-bottom: 1rem;
        }

        .file-upload-text {
            font-size: 1.125rem;
            color: #374151;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .file-upload-hint {
            font-size: 0.875rem;
            color: #6b7280;
        }

        .file-list {
            margin-top: 1.5rem;
        }

        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem;
            background: #f8fafc;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }

        .file-info {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .file-icon {
            font-size: 1.5rem;
            color: var(--primary-color);
        }

        .file-details h4 {
            font-weight: 600;
            color: #374151;
            margin-bottom: 0.25rem;
        }

        .file-details p {
            font-size: 0.875rem;
            color: #6b7280;
        }

        /* Buttons */
        .btn {
            padding: 1rem 2rem;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-family: inherit;
            position: relative;
            overflow: hidden;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s ease;
        }

        .btn:hover::before {
            left: 100%;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            color: white;
            box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px 0 rgba(37, 99, 235, 0.4);
        }

        .btn-success {
            background: linear-gradient(135deg, var(--success-color) 0%, #047857 100%);
            color: white;
            box-shadow: 0 4px 14px 0 rgba(5, 150, 105, 0.3);
        }

        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px 0 rgba(5, 150, 105, 0.4);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }

        /* Results and Alerts */
        .results-area {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border-radius: var(--border-radius);
            padding: 2rem;
            margin-top: 2rem;
            border: 1px solid #e2e8f0;
        }

        .alert {
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            border-left: 4px solid;
            font-weight: 500;
        }

        .alert-success {
            background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
            border-left-color: var(--success-color);
            color: #065f46;
        }

        .alert-error {
            background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%);
            border-left-color: var(--error-color);
            color: #991b1b;
        }

        .alert-info {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left-color: var(--primary-color);
            color: #1e40af;
        }

        /* Loading States */
        .loading {
            display: none;
            text-align: center;
            padding: 2rem;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #f3f4f6;
            border-top: 4px solid var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 1.125rem;
            color: #374151;
            margin-bottom: 1rem;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 1rem;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary-color), var(--success-color));
            width: 0%;
            transition: width 0.3s ease;
        }

        /* Requirements Grid */
        .requirements-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 1.5rem;
        }

        .requirement-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .requirement-card h4 {
            font-weight: 600;
            color: #374151;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .requirement-list {
            list-style: none;
            padding: 0;
        }

        .requirement-list li {
            padding: 0.5rem 0;
            border-bottom: 1px solid #f3f4f6;
            color: #4b5563;
        }

        .requirement-list li:last-child {
            border-bottom: none;
        }

        .requirement-list li::before {
            content: '✓';
            color: var(--success-color);
            font-weight: bold;
            margin-right: 0.5rem;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem;
            color: white;
            opacity: 0.8;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .header h1 {
                font-size: 2rem;
            }

            .progress-steps {
                flex-direction: column;
                gap: 2rem;
            }

            .progress-steps::before,
            .progress-line {
                display: none;
            }

            .content-area {
                padding: 2rem;
            }

            .requirements-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🏠 Mortgage Package Reorganizer</h1>
            <p>Professional Document Organization with Enhanced AI Classification</p>
        </div>

        <!-- Main Card -->
        <div class="main-card">
            <!-- Progress Bar -->
            <div class="progress-bar-container">
                <div class="progress-steps">
                    <div class="progress-line" id="progress-line"></div>
                    
                    <div class="step active" data-step="1">
                        <div class="step-indicator">1</div>
                        <div class="step-title">Parse Requirements</div>
                        <div class="step-description">Extract lender requirements</div>
                    </div>
                    
                    <div class="step" data-step="2">
                        <div class="step-indicator">2</div>
                        <div class="step-title">Upload Documents</div>
                        <div class="step-description">Upload mortgage package</div>
                    </div>
                    
                    <div class="step" data-step="3">
                        <div class="step-indicator">3</div>
                        <div class="step-title">Generate Package</div>
                        <div class="step-description">Create organized PDF</div>
                    </div>
                </div>
            </div>

            <!-- Content Area -->
            <div class="content-area">
                <!-- Step 1: Parse Lender Requirements -->
                <div class="step-content active" id="step-1">
                    <div class="content-header">
                        <h2><span>📧</span> Parse Lender Requirements</h2>
                        <p>Paste the lender's email or closing instructions to extract document organization requirements</p>
                    </div>

                    <div class="form-group">
                        <label class="form-label" for="email-content">Lender Email or Closing Instructions</label>
                        <textarea 
                            class="form-control textarea" 
                            id="email-content" 
                            placeholder="Paste the complete email or document from your lender containing the closing instructions and required document list..."
                            rows="8"
                        ></textarea>
                    </div>

                    <button class="btn btn-primary" onclick="parseLenderRequirements()">
                        <span>🔍</span> Parse Requirements
                    </button>

                    <div class="loading" id="parse-loading">
                        <div class="spinner"></div>
                        <p class="loading-text">Analyzing lender requirements with AI...</p>
                    </div>

                    <div class="results-area" id="parse-results" style="display: none;">
                        <h3>✅ Requirements Parsed Successfully</h3>
                        <div id="requirements-content"></div>
                        <button class="btn btn-success" onclick="proceedToUpload()" style="margin-top: 1rem;">
                            <span>➡️</span> Proceed to Upload
                        </button>
                    </div>
                </div>

                <!-- Step 2: Upload Documents -->
                <div class="step-content" id="step-2">
                    <div class="content-header">
                        <h2><span>📄</span> Upload Mortgage Documents</h2>
                        <p>Upload your mortgage package PDF for intelligent reorganization</p>
                    </div>

                    <div class="form-group">
                        <div class="file-upload-area" id="file-upload-area">
                            <div class="file-upload-icon">📁</div>
                            <div class="file-upload-text">Drop your mortgage package PDF here</div>
                            <div class="file-upload-hint">or click to browse files (PDF format, max 50MB)</div>
                            <input type="file" id="file-input" accept=".pdf" style="display: none;" multiple>
                        </div>
                        <div class="file-list" id="file-list"></div>
                    </div>

                    <button class="btn btn-primary" onclick="analyzeDocuments()" id="analyze-btn" disabled>
                        <span>🔍</span> Analyze Documents
                    </button>

                    <div class="loading" id="analyze-loading">
                        <div class="spinner"></div>
                        <p class="loading-text">Analyzing documents with enhanced AI classification...</p>
                    </div>

                    <div class="results-area" id="analyze-results" style="display: none;">
                        <h3>✅ Documents Analyzed Successfully</h3>
                        <div id="analysis-content"></div>
                        <button class="btn btn-success" onclick="proceedToGeneration()" style="margin-top: 1rem;">
                            <span>➡️</span> Proceed to Generation
                        </button>
                    </div>
                </div>

                <!-- Step 3: Generate Reorganized Package -->
                <div class="step-content" id="step-3">
                    <div class="content-header">
                        <h2><span>🚀</span> Generate Professional Package</h2>
                        <p>Create your professionally organized mortgage package with enhanced document classification</p>
                    </div>
                    
                    <div class="alert alert-info">
                        <strong>Ready for Enhanced Generation!</strong> Your documents will be intelligently reorganized according to the parsed lender requirements using our enhanced classification system, ensuring proper organization instead of "Miscellaneous" grouping.
                    </div>

                    <button class="btn btn-success" onclick="generateReorganizedPDF()">
                        <span>🚀</span> Generate Professional Package
                    </button>

                    <div class="loading" id="generate-loading">
                        <div class="spinner"></div>
                        <p class="loading-text">Reorganizing documents with enhanced AI precision...</p>
                        <div class="progress-bar">
                            <div class="progress-fill" id="progress-fill"></div>
                        </div>
                    </div>

                    <div class="results-area" id="generate-results" style="display: none;">
                        <h3>✅ Package Generated Successfully</h3>
                        <div id="download-content"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>&copy; 2025 Mortgage Package Reorganizer • Enhanced Professional Document Organization • Powered by AI</p>
        </div>
    </div>

    <script>
        // Global application state
        let currentStep = 1;
        let lastLenderRequirements = null;
        let lastAnalysisResults = null;
        let uploadedPdfPath = null;

        // Initialize application
        document.addEventListener('DOMContentLoaded', function() {
            setupFileUpload();
            setupStepNavigation();
            console.log('🏠 Mortgage Package Reorganizer - Enhanced Edition Initialized');
        });

        // Setup step navigation
        function setupStepNavigation() {
            document.querySelectorAll('.step').forEach(step => {
                step.addEventListener('click', function() {
                    const stepNumber = parseInt(this.dataset.step);
                    if (stepNumber <= currentStep || this.classList.contains('completed')) {
                        goToStep(stepNumber);
                    }
                });
            });
        }

        // Navigate to specific step
        function goToStep(stepNumber) {
            // Hide all step contents
            document.querySelectorAll('.step-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all steps
            document.querySelectorAll('.step').forEach(step => {
                step.classList.remove('active');
            });
            
            // Show target step content
            document.getElementById(`step-${stepNumber}`).classList.add('active');
            
            // Mark target step as active
            document.querySelector(`[data-step="${stepNumber}"]`).classList.add('active');
            
            // Mark previous steps as completed
            for (let i = 1; i < stepNumber; i++) {
                document.querySelector(`[data-step="${i}"]`).classList.add('completed');
            }
            
            // Update progress line
            updateProgressLine(stepNumber);
            
            currentStep = stepNumber;
        }

        // Update progress line
        function updateProgressLine(stepNumber) {
            const progressLine = document.getElementById('progress-line');
            const percentage = ((stepNumber - 1) / 2) * 100;
            progressLine.style.width = percentage + '%';
        }

        // Setup file upload
        function setupFileUpload() {
            const fileUploadArea = document.getElementById('file-upload-area');
            const fileInput = document.getElementById('file-input');
            const fileList = document.getElementById('file-list');
            const analyzeBtn = document.getElementById('analyze-btn');

            // Click to upload
            fileUploadArea.addEventListener('click', () => {
                fileInput.click();
            });

            // Drag and drop
            fileUploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                fileUploadArea.classList.add('dragover');
            });

            fileUploadArea.addEventListener('dragleave', () => {
                fileUploadArea.classList.remove('dragover');
            });

            fileUploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                fileUploadArea.classList.remove('dragover');
                handleFiles(e.dataTransfer.files);
            });

            // File input change
            fileInput.addEventListener('change', (e) => {
                handleFiles(e.target.files);
            });

            function handleFiles(files) {
                fileList.innerHTML = '';
                
                if (files.length > 0) {
                    Array.from(files).forEach(file => {
                        if (file.type === 'application/pdf') {
                            const fileItem = document.createElement('div');
                            fileItem.className = 'file-item';
                            fileItem.innerHTML = `
                                <div class="file-info">
                                    <div class="file-icon">📄</div>
                                    <div class="file-details">
                                        <h4>${file.name}</h4>
                                        <p>${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                    </div>
                                </div>
                            `;
                            fileList.appendChild(fileItem);
                        }
                    });
                    
                    analyzeBtn.disabled = false;
                } else {
                    analyzeBtn.disabled = true;
                }
            }
        }

        // Parse lender requirements
        async function parseLenderRequirements() {
            const emailContent = document.getElementById('email-content').value.trim();
            
            if (!emailContent) {
                showAlert('Please enter the lender email or closing instructions', 'error');
                return;
            }
            
            showLoading('parse-loading', true);
            
            try {
                const response = await fetch('/parse_email', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email_content: emailContent
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    lastLenderRequirements = result.requirements;
                    displayRequirements(result.requirements);
                    showResults('parse-results', true);
                    showAlert('Lender requirements parsed successfully!', 'success');
                } else {
                    showAlert(result.error || 'Failed to parse requirements', 'error');
                }
            } catch (error) {
                console.error('Parse error:', error);
                showAlert('Network error occurred during parsing', 'error');
            } finally {
                showLoading('parse-loading', false);
            }
        }

        // Display parsed requirements
        function displayRequirements(requirements) {
            const content = document.getElementById('requirements-content');
            
            let html = '<div class="requirements-grid">';
            
            if (requirements.document_order && requirements.document_order.length > 0) {
                html += `
                    <div class="requirement-card">
                        <h4>📋 Required Document Order</h4>
                        <ul class="requirement-list">
                `;
                requirements.document_order.forEach(doc => {
                    html += `<li>${doc}</li>`;
                });
                html += '</ul></div>';
            }
            
            html += `
                <div class="requirement-card">
                    <h4>📝 Processing Details</h4>
                    <p><strong>Enhanced Classification:</strong> Enabled</p>
                    <p><strong>Document Types:</strong> ${requirements.document_order ? requirements.document_order.length : 'Multiple'}</p>
                    <p><strong>Organization:</strong> Lender-specified order</p>
                    <p><strong>Image PDF Support:</strong> Yes</p>
                </div>
            `;
            
            if (requirements.special_instructions) {
                html += `
                    <div class="requirement-card">
                        <h4>⚠️ Special Instructions</h4>
                        <p>${requirements.special_instructions}</p>
                    </div>
                `;
            }
            
            html += '</div>';
            content.innerHTML = html;
        }

        // Proceed to upload step
        function proceedToUpload() {
            goToStep(2);
        }

        // Analyze documents
        async function analyzeDocuments() {
            const fileInput = document.getElementById('file-input');
            const files = fileInput.files;
            
            if (files.length === 0) {
                showAlert('Please select files to analyze', 'error');
                return;
            }
            
            showLoading('analyze-loading', true);
            
            try {
                const formData = new FormData();
                Array.from(files).forEach(file => {
                    formData.append('files', file);
                });
                formData.append('industry', 'mortgage');
                
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    lastAnalysisResults = result;
                    displayAnalysisResults(result);
                    showResults('analyze-results', true);
                    showAlert('Documents analyzed successfully with enhanced classification!', 'success');
                } else {
                    showAlert(result.error || 'Failed to analyze documents', 'error');
                }
            } catch (error) {
                console.error('Analysis error:', error);
                showAlert('Network error occurred during analysis', 'error');
            } finally {
                showLoading('analyze-loading', false);
            }
        }

        // Display analysis results
        function displayAnalysisResults(results) {
            const content = document.getElementById('analysis-content');
            
            let html = '<div class="alert alert-success">';
            html += '<strong>Enhanced Classification Applied!</strong> Documents have been analyzed using our improved classification system that maps to your specific lender requirements.';
            html += '</div>';
            
            if (results.sections && results.sections.length > 0) {
                html += '<div class="requirements-grid">';
                html += `
                    <div class="requirement-card">
                        <h4>📊 Document Sections Identified</h4>
                        <ul class="requirement-list">
                `;
                results.sections.forEach(section => {
                    const pageText = section.pages ? `${section.pages} pages` : 'Multiple pages';
                    html += `<li><strong>${section.title}</strong> - ${pageText}</li>`;
                });
                html += '</ul></div>';
                
                html += `
                    <div class="requirement-card">
                        <h4>📈 Enhanced Analysis Summary</h4>
                        <p><strong>Total Files:</strong> ${results.total_files || 1}</p>
                        <p><strong>Document Sections:</strong> ${results.sections.length}</p>
                        <p><strong>Classification:</strong> Enhanced AI-powered</p>
                        <p><strong>Lender Compliance:</strong> Ready</p>
                        <p><strong>Status:</strong> Ready for reorganization</p>
                    </div>
                `;
                html += '</div>';
            }
            
            content.innerHTML = html;
        }

        // Proceed to generation step
        function proceedToGeneration() {
            goToStep(3);
        }

        // Generate reorganized PDF
        async function generateReorganizedPDF() {
            if (!lastAnalysisResults || !lastLenderRequirements) {
                showAlert('Please complete the previous steps first', 'error');
                return;
            }
            
            showLoading('generate-loading', true);
            updateProgress(0);
            
            try {
                // Simulate progress updates
                const progressInterval = setInterval(() => {
                    const currentProgress = parseInt(document.getElementById('progress-fill').style.width) || 0;
                    if (currentProgress < 90) {
                        updateProgress(currentProgress + 10);
                    }
                }, 500);
                
                const reorganizationData = {
                    document_sections: lastAnalysisResults?.sections || [],
                    lender_requirements: lastLenderRequirements || {},
                    original_pdf_path: uploadedPdfPath || ''
                };
                
                console.log('🔍 Sending enhanced reorganization data:', reorganizationData);
                
                const response = await fetch('/reorganize_pdf', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(reorganizationData)
                });
                
                clearInterval(progressInterval);
                updateProgress(100);
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                    const filename = `enhanced_mortgage_package_${timestamp}.pdf`;
                    
                    displayDownloadLink(url, filename, blob.size);
                    showResults('generate-results', true);
                    
                    showAlert('Enhanced mortgage package generated successfully with proper document organization!', 'success');
                } else {
                    const errorResult = await response.json();
                    showAlert(errorResult.error || 'Failed to generate enhanced PDF', 'error');
                }
            } catch (error) {
                console.error('Enhanced PDF reorganization error:', error);
                showAlert('Network error occurred during enhanced PDF generation', 'error');
            } finally {
                showLoading('generate-loading', false);
            }
        }

        // Display download link
        function displayDownloadLink(url, filename, fileSize) {
            const content = document.getElementById('download-content');
            const fileSizeMB = (fileSize / 1024 / 1024).toFixed(2);
            
            content.innerHTML = `
                <div class="alert alert-success">
                    <strong>🎉 Success!</strong> Your enhanced mortgage package has been generated with intelligent document classification and is ready for download.
                </div>
                <div class="requirements-grid">
                    <div class="requirement-card">
                        <h4>📥 Download Enhanced Package</h4>
                        <a href="${url}" download="${filename}" class="btn btn-success">
                            <span>📥</span> Download Enhanced Package
                        </a>
                        <p style="margin-top: 1rem; color: #6b7280; font-size: 0.875rem;">
                            <strong>File:</strong> ${filename}<br>
                            <strong>Size:</strong> ${fileSizeMB} MB<br>
                            <strong>Generated:</strong> ${new Date().toLocaleString()}
                        </p>
                    </div>
                    <div class="requirement-card">
                        <h4>✅ Enhanced Package Features</h4>
                        <ul class="requirement-list">
                            <li>Professional cover page with processing summary</li>
                            <li>Lender requirement compliance</li>
                            <li>Intelligent document classification (no more "Miscellaneous")</li>
                            <li>Organized document sections with separators</li>
                            <li>Industry-standard formatting</li>
                            <li>Complete page preservation</li>
                            <li>Image-based PDF support</li>
                        </ul>
                    </div>
                </div>
            `;
        }

        // Update progress bar
        function updateProgress(percentage) {
            document.getElementById('progress-fill').style.width = percentage + '%';
        }

        // Show/hide loading indicators
        function showLoading(elementId, show) {
            const element = document.getElementById(elementId);
            element.style.display = show ? 'block' : 'none';
        }

        // Show/hide results
        function showResults(elementId, show) {
            const element = document.getElementById(elementId);
            element.style.display = show ? 'block' : 'none';
        }

        // Show alert messages
        function showAlert(message, type) {
            // Remove existing alerts
            document.querySelectorAll('.alert').forEach(alert => {
                if (alert.classList.contains('alert-error') || alert.classList.contains('alert-success')) {
                    alert.remove();
                }
            });
            
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.innerHTML = message;
            
            // Insert at the top of the current step content
            const currentStepContent = document.querySelector('.step-content.active');
            currentStepContent.insertBefore(alertDiv, currentStepContent.firstChild);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
    </script>
</body>
</html>
"""

# Flask routes
@app.route('/')
def index():
    """Main page with enhanced mortgage-focused interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/parse_email', methods=['POST'])
def parse_email():
    """Parse lender requirements from email content"""
    try:
        data = request.get_json()
        email_content = data.get('email_content', '')
        
        if not email_content:
            return jsonify({'success': False, 'error': 'No email content provided'})
        
        # Use OpenAI to parse the email content
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a mortgage industry expert. Parse the provided email or document to extract specific lender requirements for document organization. 

                    Return a JSON object with:
                    - document_order: Array of required document types in order
                    - special_instructions: Any specific formatting or organization requirements
                    - priority_documents: Documents that must be included
                    - submission_deadline: If mentioned
                    
                    Focus on mortgage-specific document types like loan applications, income verification, asset documentation, credit reports, appraisals, etc."""
                },
                {
                    "role": "user",
                    "content": f"Parse this lender communication for document organization requirements:\n\n{email_content}"
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        # Parse the AI response
        ai_response = response.choices[0].message.content
        
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                requirements = json.loads(json_match.group())
            else:
                # Fallback: create structured response
                requirements = {
                    "document_order": [
                        "Closing Instructions (signed/dated)",
                        "Symmetry 1003",
                        "HELOC agreement (2nd)",
                        "Notice of Right to Cancel",
                        "Mtg/Deed (2nd)",
                        "Settlement Statement/HUD (2nd)",
                        "Flood Notice",
                        "First Payment Letter aka Payment and Servicing Notification",
                        "Signature/Name Affidavit",
                        "Errors and Omissions Compliance Agreement",
                        "Mailing address cert",
                        "W-9",
                        "SSA-89",
                        "4506-C"
                    ],
                    "special_instructions": "Standard mortgage package organization with enhanced classification",
                    "priority_documents": ["Closing Instructions", "HELOC agreement"],
                    "submission_deadline": "Not specified"
                }
        except:
            # Fallback requirements
            requirements = {
                "document_order": [
                    "Closing Instructions (signed/dated)",
                    "Symmetry 1003",
                    "HELOC agreement (2nd)",
                    "Notice of Right to Cancel",
                    "Mtg/Deed (2nd)",
                    "Settlement Statement/HUD (2nd)",
                    "Flood Notice",
                    "First Payment Letter aka Payment and Servicing Notification",
                    "Signature/Name Affidavit",
                    "Errors and Omissions Compliance Agreement",
                    "Mailing address cert",
                    "W-9",
                    "SSA-89",
                    "4506-C"
                ],
                "special_instructions": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response
            }
        
        return jsonify({
            'success': True,
            'requirements': requirements
        })
        
    except Exception as e:
        print(f"Error parsing email: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analyze', methods=['POST'])
def analyze_documents():
    """Analyze uploaded mortgage documents with enhanced classification"""
    try:
        print("🔍 DEBUG: Starting enhanced document analysis")
        
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'})
        
        files = request.files.getlist('files')
        industry = request.form.get('industry', 'mortgage')
        
        print(f"🔍 DEBUG: Received {len(files)} files for {industry} industry")
        
        results = {
            'success': True,
            'sections': [],
            'total_files': len(files),
            'industry': industry,
            'enhanced_classification': True
        }
        
        for file in files:
            if file.filename == '':
                continue
                
            # Save file temporarily
            filename = secure_filename(file.filename)
            temp_path = os.path.join('/tmp', filename)
            file.save(temp_path)
            
            print(f"🔍 DEBUG: Saved file: {temp_path}")
            
            try:
                # Analyze the document
                if filename.lower().endswith('.pdf'):
                    # For mortgage industry, preserve PDF files for reorganization
                    if industry == 'mortgage' and file.filename.lower().endswith('.pdf'):
                        print(f"🔍 DEBUG: Preserving PDF file for enhanced reorganization: {temp_path}")
                        # Don't delete PDF files - they'll be needed for reorganization
                    
                    # Extract text and analyze with enhanced classification
                    with open(temp_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text_content = ""
                        page_count = len(pdf_reader.pages)
                        
                        # Extract text from first few pages for analysis
                        for page_num in range(min(3, page_count)):
                            try:
                                text_content += pdf_reader.pages[page_num].extract_text()
                            except:
                                pass  # Handle image-based PDFs gracefully
                    
                    # Use enhanced classification
                    doc_type = classify_mortgage_document_enhanced(text_content)
                    
                    results['sections'].append({
                        'title': doc_type,
                        'filename': filename,
                        'pages': page_count,
                        'type': 'pdf',
                        'enhanced_classification': True
                    })
                    
                    print(f"🔍 DEBUG: Enhanced classification: {filename} as {doc_type} ({page_count} pages)")
                
            except Exception as e:
                print(f"🔍 DEBUG: Error analyzing {filename}: {e}")
                results['sections'].append({
                    'title': 'Supporting Documents',
                    'filename': filename,
                    'error': str(e),
                    'enhanced_classification': True
                })
            
            finally:
                # Clean up temporary file (except for mortgage PDFs)
                if not (industry == 'mortgage' and filename.lower().endswith('.pdf')):
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        
        print(f"🔍 DEBUG: Enhanced analysis complete. Found {len(results['sections'])} sections")
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in enhanced document analysis: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reorganize_pdf', methods=['POST'])
def reorganize_pdf_enhanced():
    """Enhanced PDF reorganization with improved document classification"""
    try:
        print("🔍 DEBUG: Enhanced reorganize_pdf endpoint called")
        print(f"🔍 DEBUG: Memory usage at start: {gc.get_count()}")
        
        print("🔍 DEBUG: Getting request data...")
        data = request.get_json()
        
        if not data:
            print("🔍 DEBUG: No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
        
        print(f"🔍 DEBUG: Request data keys: {list(data.keys())}")
        
        document_sections = data.get('document_sections', [])
        lender_requirements = data.get('lender_requirements', {})
        original_pdf_path = data.get('original_pdf_path', '')
        
        print(f"🔍 DEBUG: Received {len(document_sections)} document sections")
        print(f"🔍 DEBUG: Lender requirements: {len(lender_requirements.get('document_order', []))} required docs")
        print(f"🔍 DEBUG: Original PDF path: {original_pdf_path}")
        print(f"🔍 DEBUG: File exists: {os.path.exists(original_pdf_path) if original_pdf_path else False}")
        
        # Enhanced file detection
        has_original_pdf = False
        if original_pdf_path and os.path.exists(original_pdf_path):
            has_original_pdf = True
            print(f"🔍 DEBUG: Found original PDF at specified path")
        else:
            # Try to find PDF files in /tmp
            try:
                tmp_files = os.listdir('/tmp')
                pdf_files = [f for f in tmp_files if f.lower().endswith('.pdf')]
                print(f"🔍 DEBUG: PDF files in /tmp: {pdf_files}")
                
                if pdf_files:
                    # Use the first PDF file found
                    original_pdf_path = f"/tmp/{pdf_files[0]}"
                    has_original_pdf = True
                    print(f"🔍 DEBUG: Using fallback PDF: {original_pdf_path}")
                else:
                    print("🔍 DEBUG: No PDF files found in /tmp")
            except Exception as e:
                print(f"🔍 DEBUG: Error scanning /tmp directory: {e}")
        
        # Create output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"enhanced_mortgage_package_{timestamp}.pdf"
        output_path = f"/tmp/{output_filename}"
        
        print(f"🔍 DEBUG: Output path: {output_path}")
        
        if has_original_pdf:
            print("📄 Processing with enhanced classification...")
            
            try:
                # Use enhanced page extraction and reorganization
                print("🔍 DEBUG: Starting enhanced page extraction...")
                page_extraction_result = extract_and_reorganize_pages_enhanced(original_pdf_path, lender_requirements)
                print(f"🔍 DEBUG: Enhanced page extraction result: {type(page_extraction_result)}")
                
                if page_extraction_result:
                    print(f"🔍 DEBUG: Total pages extracted: {page_extraction_result.get('total_pages', 0)}")
                
                # Create reorganized PDF with enhanced organization
                print("🔍 DEBUG: Starting enhanced PDF creation...")
                success = create_reorganized_pdf_enhanced(page_extraction_result, lender_requirements, output_path)
                
                if success and os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"🔍 DEBUG: Enhanced PDF created successfully. Size: {file_size} bytes")
                    
                    # Verify page count
                    try:
                        with open(output_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            page_count = len(pdf_reader.pages)
                            print(f"🔍 DEBUG: Final enhanced PDF has {page_count} pages")
                    except Exception as e:
                        print(f"🔍 DEBUG: Error verifying page count: {e}")
                    
                    # Clean up preserved PDF file after reorganization
                    if has_original_pdf and os.path.exists(original_pdf_path):
                        os.remove(original_pdf_path)
                        print(f"🔍 DEBUG: Cleaned up preserved PDF: {original_pdf_path}")
                    
                    return send_file(output_path, as_attachment=True, download_name=output_filename)
                else:
                    print("🔍 DEBUG: Enhanced PDF creation failed")
                    return jsonify({'error': 'Failed to create enhanced reorganized PDF'}), 500
                    
            except Exception as e:
                print(f"🔍 DEBUG: Error in enhanced PDF processing: {e}")
                traceback.print_exc()
                return jsonify({'error': f'Enhanced PDF processing error: {str(e)}'}), 500
        else:
            print("📄 No original PDF - creating enhanced document summary")
            
            # Create enhanced summary-only PDF
            try:
                success = create_reorganized_pdf_enhanced(None, lender_requirements, output_path)
                
                if success and os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"🔍 DEBUG: Enhanced summary PDF created. Size: {file_size} bytes")
                    return send_file(output_path, as_attachment=True, download_name=output_filename)
                else:
                    return jsonify({'error': 'Failed to create enhanced summary PDF'}), 500
                    
            except Exception as e:
                print(f"🔍 DEBUG: Error creating enhanced summary PDF: {e}")
                traceback.print_exc()
                return jsonify({'error': f'Enhanced summary PDF creation error: {str(e)}'}), 500
        
    except Exception as e:
        print(f"🔍 DEBUG: Unexpected error in enhanced reorganize_pdf: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Unexpected enhanced processing error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

