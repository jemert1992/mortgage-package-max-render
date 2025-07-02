#!/usr/bin/env python3
"""
🏠 Mortgage Package Reorganizer - Professional Edition
A robust AI-powered tool for reorganizing mortgage documents according to lender requirements
"""

import os
import json
import re
import traceback
import gc
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_file
from werkzeug.utils import secure_filename
import openai
from openai import OpenAI
import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import io
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Initialize OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    logger.error("❌ ERROR: OPENAI_API_KEY environment variable not found!")
    exit(1)

client = OpenAI(api_key=openai_api_key)
logger.info("✅ OpenAI client initialized successfully")

# Enhanced mortgage document classification keywords
MORTGAGE_DOCUMENT_KEYWORDS = {
    "loan_application": ["loan application", "1003", "uniform residential loan application"],
    "income_documentation": ["pay stub", "w-2", "tax return", "1040", "income statement"],
    "asset_documentation": ["bank statement", "asset verification", "savings account", "401k"],
    "credit_documentation": ["credit report", "credit score", "tri-merge", "fico score"],
    "property_documentation": ["appraisal", "property valuation", "home inspection", "title report"],
    "loan_documentation": ["loan estimate", "closing disclosure", "promissory note", "mortgage note"],
    "verification_documents": ["verification of employment", "verification of deposit", "voe", "vod"],
    "disclosures": ["disclosure", "tila", "respa", "good faith estimate", "right to cancel"]
}

# Section-specific keywords for boundary detection
SECTION_KEYWORDS = {
    "closing_instructions": ["closing instructions", "settlement agent acknowledgment"],
    "mortgage_heloc": ["mortgage", "heloc", "deed of trust", "promissory note", "signature"],
    "supporting_documents": ["flood notice", "w-9", "ssa-89", "4506-c", "anti-coercion"]
}

# HTML template (simplified for brevity, use the original if needed)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><title>Mortgage Package Reorganizer</title></head>
<body>
    <h1>🏠 Mortgage Package Reorganizer</h1>
    <div id="content"></div>
    <script>
        async function parseLenderRequirements() { /* Implementation */ }
        async function handleFiles(files) { /* Implementation */ }
        async function generateReorganizedPDF() { /* Implementation */ }
    </script>
</body>
</html>
"""

def assign_page_to_document_safe(page_text, document_sections, lender_requirements):
    """Safely assign a page to a document type with section boundary detection"""
    if not page_text:
        return "supporting_documents"

    page_text_lower = page_text.lower()

    # Detect section boundaries
    for section, keywords in SECTION_KEYWORDS.items():
        if any(keyword in page_text_lower for keyword in keywords):
            return section

    # Score based on mortgage keywords
    scores = {doc_type: sum(1 for keyword in keywords if keyword.lower() in page_text_lower)
              for doc_type, keywords in MORTGAGE_DOCUMENT_KEYWORDS.items()}
    if scores and max(scores.values()) > 0:
        best_match = max(scores, key=scores.get)
        return best_match

    # Use lender-specified order if available
    if lender_requirements.get('document_order'):
        for doc in lender_requirements['document_order']:
            if doc.lower().replace(" ", "_") in page_text_lower:
                return doc.lower().replace(" ", "_")

    return "supporting_documents"

def extract_and_reorganize_pages_safe(original_pdf_path, document_sections, lender_requirements):
    """Extract and assign pages from the original PDF with memory efficiency"""
    logger.info(f"🔍 Starting page extraction from: {original_pdf_path}")
    if not os.path.exists(original_pdf_path):
        logger.error(f"🔍 Original PDF not found: {original_pdf_path}")
        return {}

    try:
        temp_pdf_path = f"/tmp/temp_extracted_pages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        with open(original_pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            logger.info(f"🔍 Total pages in original PDF: {total_pages}")

            temp_pdf_writer = PyPDF2.PdfWriter()
            page_assignments = []

            for page_num in range(total_pages):  # Removed arbitrary limit
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text() or ""
                    assigned_doc = assign_page_to_document_safe(page_text, document_sections, lender_requirements)
                    temp_pdf_writer.add_page(page)
                    page_assignments.append({
                        'page_number': page_num,
                        'assigned_document': assigned_doc,
                        'temp_page_index': len(temp_pdf_writer.pages) - 1
                    })
                    logger.debug(f"🔍 Page {page_num + 1} assigned to: {assigned_doc}")
                    if page_num % 10 == 0:
                        gc.collect()
                except Exception as e:
                    logger.error(f"🔍 Error processing page {page_num}: {e}")
                    continue

            with open(temp_pdf_path, 'wb') as temp_file:
                temp_pdf_writer.write(temp_file)
            logger.info(f"🔍 Created temporary PDF with {len(page_assignments)} pages")
            return {'temp_pdf_path': temp_pdf_path, 'page_assignments': page_assignments, 'total_pages': len(page_assignments)}

    except Exception as e:
        logger.error(f"🔍 Error in page extraction: {e}")
        traceback.print_exc()
        return {}

def create_table_of_contents(document_sections, lender_requirements):
    """Create a dynamic table of contents"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    toc_style = ParagraphStyle('TOCTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=15, textColor=HexColor('#2c3e50'), alignment=1)
    item_style = ParagraphStyle('TOCItem', parent=styles['Normal'], fontSize=12, spaceAfter=10, textColor=HexColor('#34495e'))

    story.append(Paragraph("📑 Table of Contents", toc_style))
    story.append(Spacer(1, 0.5*inch))

    for section in document_sections:
        title = section.get('title', 'Untitled').replace('_', ' ').title()
        pages = section.get('pages', 'N/A')
        story.append(Paragraph(f"{title} - {pages} pages", item_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

def create_cover_page_enhanced(document_sections, lender_requirements):
    """Create an enhanced cover page"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=30, textColor=HexColor('#2c3e50'), alignment=1)
    subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=16, spaceAfter=20, textColor=HexColor('#34495e'), alignment=1)

    story.append(Paragraph("🏠 PROFESSIONAL MORTGAGE PACKAGE", title_style))
    story.append(Paragraph("Reorganized According to Lender Requirements", subtitle_style))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"<b>Processing Date:</b> {datetime.now().strftime('%B %d, %Y %I:%M %p EDT')}", styles['Normal']))
    story.append(Paragraph(f"<b>Total Document Sections:</b> {len(document_sections) if document_sections else 'N/A'}", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

def create_document_separator_enhanced(document_type, page_count):
    """Create an enhanced separator page"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    separator_style = ParagraphStyle('SeparatorStyle', parent=styles['Heading1'], fontSize=20, spaceAfter=20, textColor=HexColor('#3498db'), alignment=1)
    formatted_name = document_type.replace('_', ' ').title()
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph(f"📋 {formatted_name}", separator_style))
    story.append(Paragraph(f"({page_count} pages)", styles['Normal']))
    story.append(Spacer(1, 2*inch))

    doc.build(story)
    buffer.seek(0)
    return buffer

def create_reorganized_pdf_safe(page_extraction_result, document_sections, lender_requirements, output_path):
    """Create the final reorganized PDF with structured sections"""
    logger.info(f"🔍 Starting PDF creation at: {output_path}")
    try:
        pdf_writer = PyPDF2.PdfWriter()

        # Add cover page
        cover_page_buffer = create_cover_page_enhanced(document_sections, lender_requirements)
        if cover_page_buffer:
            cover_pdf = PyPDF2.PdfReader(cover_page_buffer)
            pdf_writer.add_page(cover_pdf.pages[0])
            logger.info("🔍 Added cover page")

        # Add table of contents
        toc_buffer = create_table_of_contents(document_sections, lender_requirements)
        if toc_buffer:
            toc_pdf = PyPDF2.PdfReader(toc_buffer)
            pdf_writer.add_page(toc_pdf.pages[0])
            logger.info("🔍 Added table of contents")

        if not page_extraction_result or 'temp_pdf_path' not in page_extraction_result:
            logger.warning("🔍 No page extraction results, creating summary only")
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            return True

        temp_pdf_path = page_extraction_result['temp_pdf_path']
        page_assignments = page_extraction_result['page_assignments']

        if os.path.exists(temp_pdf_path):
            with open(temp_pdf_path, 'rb') as temp_file:
                temp_pdf_reader = PyPDF2.PdfReader(temp_file)

                # Define reorganization order based on lender requirements
                reorganization_order = lender_requirements.get('document_order', [
                    "closing_instructions", "mortgage_heloc", "supporting_documents"
                ])

                for doc_type in reorganization_order:
                    assignments = [a for a in page_assignments if a['assigned_document'] == doc_type]
                    if assignments:
                        separator_buffer = create_document_separator_enhanced(doc_type, len(assignments))
                        if separator_buffer:
                            separator_pdf = PyPDF2.PdfReader(separator_buffer)
                            pdf_writer.add_page(separator_pdf.pages[0])
                            logger.info(f"🔍 Added separator for: {doc_type}")

                        for assignment in assignments:
                            temp_page_index = assignment['temp_page_index']
                            if temp_page_index < len(temp_pdf_reader.pages):
                                try:
                                    page = temp_pdf_reader.pages[temp_page_index]
                                    pdf_writer.add_page(page)
                                    logger.debug(f"🔍 Added page {assignment['page_number'] + 1} to {doc_type}")
                                except Exception as e:
                                    logger.error(f"🔍 Error adding page {temp_page_index}: {e}")

                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                logger.info(f"🔍 PDF written successfully with {len(pdf_writer.pages)} pages")

                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
                    logger.info(f"🔍 Cleaned up temp file: {temp_pdf_path}")

                return True
        else:
            logger.error(f"🔍 Temp PDF not found: {temp_pdf_path}")
            return False

    except Exception as e:
        logger.error(f"🔍 Error creating reorganized PDF: {e}")
        traceback.print_exc()
        return False

@app.route('/')
def index():
    """Main page with mortgage-focused interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/parse_email', methods=['POST'])
def parse_email():
    """Parse lender requirements from email content"""
    try:
        data = request.get_json()
        email_content = data.get('email_content', '')

        if not email_content:
            return jsonify({'success': False, 'error': 'No email content provided'})

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a mortgage industry expert. Parse the provided email or document to extract specific lender requirements for document organization. Identify sections like 'Closing Instructions', 'Mortgage/HELOC', and 'Supporting Documents'. Return a JSON object with:
                    - document_order: Array of required document types/sections in order
                    - special_instructions: Any specific formatting or organization requirements
                    - priority_documents: Documents that must be included
                    - submission_deadline: If mentioned"""
                },
                {"role": "user", "content": f"Parse this lender communication:\n\n{email_content}"}
            ],
            max_tokens=1000,
            temperature=0.3
        )

        ai_response = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        requirements = json.loads(json_match.group()) if json_match else {
            "document_order": ["closing_instructions", "mortgage_heloc", "supporting_documents"],
            "special_instructions": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response
        }

        return jsonify({'success': True, 'requirements': requirements})

    except Exception as e:
        logger.error(f"Error parsing email: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analyze', methods=['POST'])
def analyze_documents():
    """Analyze uploaded mortgage documents"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'})

        files = request.files.getlist('files')
        logger.info(f"🔍 Received {len(files)} files for mortgage industry")

        results = {'success': True, 'sections': [], 'total_files': len(files), 'industry': 'mortgage'}

        for file in files:
            if file.filename == '':
                continue

            filename = secure_filename(file.filename)
            temp_path = os.path.join('/tmp', filename)
            file.save(temp_path)
            logger.info(f"🔍 Saved file: {temp_path}")

            try:
                if filename.lower().endswith('.pdf'):
                    with open(temp_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text_content = "".join(page.extract_text() or "" for page in pdf_reader.pages[:3])
                        doc_type = assign_page_to_document_safe(text_content, [], {})
                        results['sections'].append({
                            'title': doc_type,
                            'filename': filename,
                            'pages': len(pdf_reader.pages),
                            'type': 'pdf'
                        })
                        logger.info(f"🔍 Classified {filename} as {doc_type} ({len(pdf_reader.pages)} pages)")

            except Exception as e:
                logger.error(f"🔍 Error analyzing {filename}: {e}")
                results['sections'].append({'title': 'Unknown Document', 'filename': filename, 'error': str(e)})

            if not (filename.lower().endswith('.pdf')):
                os.remove(temp_path)

        logger.info(f"🔍 Analysis complete. Found {len(results['sections'])} sections")
        return jsonify(results)

    except Exception as e:
        logger.error(f"Error in document analysis: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reorganize_pdf', methods=['POST'])
def reorganize_pdf():
    """Reorganize PDF based on lender requirements"""
    try:
        logger.info("🔍 reorganize_pdf endpoint called")
        data = request.get_json()

        if not data:
            logger.error("🔍 No JSON data received")
            return jsonify({'error': 'No data provided'}), 400

        document_sections = data.get('document_sections', [])
        lender_requirements = data.get('lender_requirements', {})
        original_pdf_path = data.get('original_pdf_path', '')

        logger.info(f"🔍 Received {len(document_sections)} document sections")
        logger.info(f"🔍 Original PDF path: {original_pdf_path}")

        has_original_pdf = os.path.exists(original_pdf_path)
        if not has_original_pdf:
            tmp_files = os.listdir('/tmp')
            pdf_files = [f for f in tmp_files if f.lower().endswith('.pdf')]
            if pdf_files:
                original_pdf_path = f"/tmp/{pdf_files[0]}"
                has_original_pdf = True
                logger.info(f"🔍 Using fallback PDF: {original_pdf_path}")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"professional_mortgage_package_{timestamp}.pdf"
        output_path = f"/tmp/{output_filename}"

        if has_original_pdf:
            logger.info("📄 Processing original PDF...")
            page_extraction_result = extract_and_reorganize_pages_safe(original_pdf_path, document_sections, lender_requirements)
            success = create_reorganized_pdf_safe(page_extraction_result, document_sections, lender_requirements, output_path)

            if success and os.path.exists(output_path):
                logger.info(f"🔍 PDF created successfully. Size: {os.path.getsize(output_path)} bytes")
                if os.path.exists(original_pdf_path):
                    os.remove(original_pdf_path)
                    logger.info(f"🔍 Cleaned up preserved PDF: {original_pdf_path}")
                return send_file(output_path, as_attachment=True, download_name=output_filename)
            else:
                logger.error("🔍 PDF creation failed")
                return jsonify({'error': 'Failed to create reorganized PDF'}), 500
        else:
            logger.warning("📄 No original PDF - creating document summary")
            success = create_reorganized_pdf_safe(None, document_sections, lender_requirements, output_path)
            if success and os.path.exists(output_path):
                return send_file(output_path, as_attachment=True, download_name=output_filename)
            return jsonify({'error': 'Failed to create summary PDF'}), 500

    except Exception as e:
        logger.error(f"🔍 Unexpected error in reorganize_pdf: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
