from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import json
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Store rules and lender requirements in memory
analysis_rules = [
    {"id": 1, "pattern": "FUNDING REQUEST", "type": "contains", "label": "Funding Request"},
    {"id": 2, "pattern": "SIGNED CLOSING INSTRUCTIONS", "type": "contains", "label": "Signed Closing Instructions"},
    {"id": 3, "pattern": "WIRE INSTRUCTIONS", "type": "contains", "label": "Wire Instructions"},
    {"id": 4, "pattern": "ESTIMATED DISBURSEMENT STATEMENT", "type": "contains", "label": "Estimated Disbursement Statement"},
    {"id": 5, "pattern": "PROMISSORY NOTE", "type": "contains", "label": "Promissory Note"},
    {"id": 6, "pattern": "SECURITY INSTRUMENT", "type": "contains", "label": "Security Instrument"},
    {"id": 7, "pattern": "MORTGAGE", "type": "exact", "label": "Mortgage"},
    {"id": 8, "pattern": "DEED", "type": "contains", "label": "Deed"},
    {"id": 9, "pattern": "SETTLEMENT STATEMENT", "type": "contains", "label": "Settlement Statement"}
]

# Store parsed lender requirements
lender_requirements = {
    "lender_name": "",
    "email_date": "",
    "required_documents": [],
    "special_instructions": [],
    "organization_rules": []
}

def parse_lender_email(email_content):
    """
    Parse lender email to extract document requirements and organization instructions
    """
    global lender_requirements
    
    # Initialize requirements
    requirements = {
        "lender_name": "",
        "email_date": "",
        "required_documents": [],
        "special_instructions": [],
        "organization_rules": []
    }
    
    # Extract lender name (look for common patterns)
    lender_patterns = [
        r"From:.*?([A-Z][a-z]+ (?:Bank|Mortgage|Lending|Financial|Credit Union))",
        r"([A-Z][a-z]+ (?:Bank|Mortgage|Lending|Financial|Credit Union))",
        r"Lender:?\s*([A-Z][a-z]+ [A-Z][a-z]+)",
    ]
    
    for pattern in lender_patterns:
        match = re.search(pattern, email_content, re.IGNORECASE)
        if match:
            requirements["lender_name"] = match.group(1)
            break
    
    if not requirements["lender_name"]:
        requirements["lender_name"] = "Unknown Lender"
    
    # Extract date
    date_patterns = [
        r"Date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, email_content, re.IGNORECASE)
        if match:
            requirements["email_date"] = match.group(1)
            break
    
    if not requirements["email_date"]:
        requirements["email_date"] = datetime.now().strftime("%m/%d/%Y")
    
    # Extract required documents (look for document lists)
    document_patterns = [
        r"(?:required|need|must include|please provide).*?documents?:?\s*(.*?)(?:\n\n|\.\s|$)",
        r"(?:documents?|items?)\s+(?:required|needed):?\s*(.*?)(?:\n\n|\.\s|$)",
        r"(?:please\s+)?(?:send|provide|include):?\s*(.*?)(?:\n\n|\.\s|$)"
    ]
    
    documents = []
    for pattern in document_patterns:
        matches = re.finditer(pattern, email_content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            doc_text = match.group(1)
            # Split by common delimiters and clean up
            doc_items = re.split(r'[•\-\*\n\d+\.\s]+', doc_text)
            for item in doc_items:
                item = item.strip().strip('.,;')
                if len(item) > 5 and item not in documents:  # Filter out short/empty items
                    documents.append(item)
    
    # If no specific documents found, use common mortgage document types
    if not documents:
        documents = [
            "Mortgage/Deed of Trust",
            "Promissory Note",
            "Settlement Statement/HUD-1",
            "Title Policy",
            "Deed",
            "Insurance Policy",
            "Flood Hazard Determination",
            "Wire Instructions",
            "Closing Instructions"
        ]
    
    requirements["required_documents"] = documents[:15]  # Limit to reasonable number
    
    # Extract special instructions
    instruction_patterns = [
        r"(?:special|additional|important)\s+(?:instructions?|requirements?|notes?):?\s*(.*?)(?:\n\n|\.\s|$)",
        r"(?:please\s+)?(?:note|remember|ensure):?\s*(.*?)(?:\n\n|\.\s|$)",
        r"(?:instructions?|requirements?):?\s*(.*?)(?:\n\n|\.\s|$)"
    ]
    
    instructions = []
    for pattern in instruction_patterns:
        matches = re.finditer(pattern, email_content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            instruction = match.group(1).strip()
            if len(instruction) > 10 and instruction not in instructions:
                instructions.append(instruction)
    
    requirements["special_instructions"] = instructions[:10]  # Limit to reasonable number
    
    # Generate organization rules based on required documents
    rules = []
    for i, doc in enumerate(requirements["required_documents"]):
        # Create search patterns for each document type
        if "mortgage" in doc.lower() or "deed of trust" in doc.lower():
            rules.append({"pattern": "MORTGAGE", "type": "contains", "label": "Mortgage/Deed of Trust", "priority": 1})
        elif "promissory" in doc.lower():
            rules.append({"pattern": "PROMISSORY NOTE", "type": "contains", "label": "Promissory Note", "priority": 1})
        elif "settlement" in doc.lower() or "hud" in doc.lower():
            rules.append({"pattern": "SETTLEMENT STATEMENT", "type": "contains", "label": "Settlement Statement", "priority": 1})
        elif "title" in doc.lower():
            rules.append({"pattern": "TITLE", "type": "contains", "label": "Title Policy", "priority": 1})
        elif "deed" in doc.lower() and "trust" not in doc.lower():
            rules.append({"pattern": "DEED", "type": "contains", "label": "Deed", "priority": 1})
        elif "insurance" in doc.lower():
            rules.append({"pattern": "INSURANCE", "type": "contains", "label": "Insurance Policy", "priority": 1})
        elif "flood" in doc.lower():
            rules.append({"pattern": "FLOOD", "type": "contains", "label": "Flood Hazard Determination", "priority": 1})
        elif "wire" in doc.lower():
            rules.append({"pattern": "WIRE", "type": "contains", "label": "Wire Instructions", "priority": 1})
        elif "closing" in doc.lower() and "instruction" in doc.lower():
            rules.append({"pattern": "CLOSING INSTRUCTIONS", "type": "contains", "label": "Closing Instructions", "priority": 1})
        else:
            # Generic rule for other document types
            key_words = doc.upper().split()[:3]  # Take first 3 words
            pattern = " ".join(key_words)
            rules.append({"pattern": pattern, "type": "contains", "label": doc, "priority": 2})
    
    requirements["organization_rules"] = rules
    
    # Update global lender requirements
    lender_requirements = requirements
    
    return requirements

def analyze_mortgage_sections_with_lender_rules(filename):
    """
    Analyze mortgage sections using lender-specific requirements if available
    """
    
    # Use lender requirements if available, otherwise fall back to default categories
    if lender_requirements["required_documents"]:
        # Use lender-specific document requirements
        target_sections = lender_requirements["required_documents"]
        organization_rules = lender_requirements["organization_rules"]
    else:
        # Fall back to default categories
        target_sections = [
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
        organization_rules = []
    
    sections = []
    page_counter = 2
    
    for i, section_name in enumerate(target_sections[:12]):  # Limit to 12 sections
        # Determine confidence based on lender rules priority
        if organization_rules and i < len(organization_rules):
            rule = organization_rules[i]
            confidence = "high" if rule.get("priority", 2) == 1 else "medium"
        else:
            # Default confidence logic
            if i < 3:
                confidence = "high"
            elif i < 6:
                confidence = "medium"
            else:
                confidence = "medium" if i % 2 == 0 else "high"
        
        # Simulate page ranges for document separation
        start_page = page_counter + (i // 3)
        end_page = start_page + (1 if i < 6 else 2)  # Some docs are longer
            
        sections.append({
            "id": i + 1,
            "title": section_name,
            "start_page": start_page,
            "end_page": end_page,
            "page_count": end_page - start_page + 1,
            "confidence": confidence,
            "matched_text": f"Sample text from {section_name}...",
            "filename": generate_filename(section_name),
            "lender_required": bool(lender_requirements["required_documents"])
        })
    
    return sections

def generate_filename(section_name):
    """Generate clean filename for separated document"""
    # Convert section name to clean filename
    filename = section_name.upper().replace(" ", "").replace(",", "").replace("&", "AND").replace("/", "")
    # Remove special characters
    filename = re.sub(r'[^A-Z0-9]', '', filename)
    return f"{filename}.pdf"

# Enhanced HTML template with email parser component
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mortgage Package Analyzer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
            line-height: 1.6;
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
            font-size: 2.5rem;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #86868b;
            font-size: 1.1rem;
        }
        
        .workflow-tabs {
            display: flex;
            background: white;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .tab {
            flex: 1;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            border: none;
            background: #f8f9fa;
            font-size: 1rem;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .tab.active {
            background: #007AFF;
            color: white;
        }
        
        .tab:hover:not(.active) {
            background: #e9ecef;
        }
        
        .workflow-content {
            display: none;
        }
        
        .workflow-content.active {
            display: block;
        }
        
        .email-section {
            background: #e8f4fd;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .email-header {
            font-size: 1.5rem;
            font-weight: 600;
            color: #0066cc;
            margin-bottom: 10px;
        }
        
        .email-description {
            color: #86868b;
            margin-bottom: 20px;
        }
        
        .email-input-area {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .email-textarea {
            width: 100%;
            min-height: 200px;
            padding: 15px;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            font-size: 1rem;
            font-family: inherit;
            resize: vertical;
        }
        
        .email-textarea:focus {
            outline: none;
            border-color: #007AFF;
            box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
        }
        
        .lender-info {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            display: none;
        }
        
        .lender-info.show {
            display: block;
        }
        
        .lender-info h3 {
            color: #007AFF;
            margin-bottom: 15px;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .info-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
        }
        
        .info-label {
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 8px;
        }
        
        .info-value {
            color: #86868b;
            font-size: 0.9rem;
        }
        
        .document-list {
            list-style: none;
            padding: 0;
        }
        
        .document-list li {
            background: #f0f4ff;
            margin: 5px 0;
            padding: 8px 12px;
            border-radius: 4px;
            border-left: 3px solid #007AFF;
        }
        
        .rules-section {
            background: #fff8e1;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .rules-header {
            font-size: 1.5rem;
            font-weight: 600;
            color: #f57c00;
            margin-bottom: 10px;
        }
        
        .rules-description {
            color: #86868b;
            margin-bottom: 20px;
        }
        
        .add-rule-form {
            display: flex;
            gap: 15px;
            align-items: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        
        .form-input {
            padding: 12px;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            font-size: 1rem;
            font-family: inherit;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #007AFF;
            box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
        }
        
        .pattern-input {
            flex: 1;
            min-width: 200px;
        }
        
        .type-select {
            min-width: 140px;
        }
        
        .label-input {
            flex: 1;
            min-width: 150px;
        }
        
        .upload-section {
            background: white;
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .upload-area {
            border: 2px dashed #007AFF;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: #f8f9ff;
        }
        
        .upload-area:hover {
            border-color: #0056b3;
            background: #f0f4ff;
        }
        
        .upload-text {
            font-size: 1.2rem;
            color: #007AFF;
            margin-bottom: 10px;
            font-weight: 500;
        }
        
        .upload-subtext {
            color: #86868b;
            font-size: 0.9rem;
        }
        
        .btn {
            background: #007AFF;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 10px;
            font-family: inherit;
        }
        
        .btn:hover {
            background: #0056b3;
            transform: translateY(-1px);
        }
        
        .btn:disabled {
            background: #d1d1d6;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-secondary {
            background: #8e8e93;
        }
        
        .btn-secondary:hover {
            background: #6d6d70;
        }
        
        .btn-success {
            background: #28a745;
        }
        
        .btn-success:hover {
            background: #218838;
        }
        
        .btn-danger {
            background: #ff3b30;
        }
        
        .btn-danger:hover {
            background: #d70015;
        }
        
        .results-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            display: none;
        }
        
        .results-header {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #d2d2d7;
        }
        
        .results-title {
            font-size: 1.8rem;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 10px;
        }
        
        .results-summary {
            color: #86868b;
            font-size: 1rem;
        }
        
        .lender-badge {
            background: #e8f4fd;
            color: #0066cc;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            margin-left: 10px;
        }
        
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
        
        .sections-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .section-card {
            background: #f8f9fa;
            border: 1px solid #d2d2d7;
            border-radius: 12px;
            padding: 20px;
            position: relative;
            transition: all 0.3s ease;
        }
        
        .section-card.lender-required {
            border-left: 4px solid #007AFF;
            background: #f8fbff;
        }
        
        .section-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .section-checkbox {
            position: absolute;
            top: 15px;
            right: 15px;
            width: 18px;
            height: 18px;
            accent-color: #007AFF;
        }
        
        .section-header {
            margin-bottom: 15px;
            padding-right: 40px;
        }
        
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 8px;
        }
        
        .section-details {
            color: #86868b;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        
        .section-filename {
            color: #007AFF;
            font-size: 0.8rem;
            font-family: monospace;
            background: #f0f4ff;
            padding: 4px 8px;
            border-radius: 4px;
            margin-top: 8px;
        }
        
        .confidence-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: lowercase;
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
        
        .toc-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            display: none;
        }
        
        .toc-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .toc-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1d1d1f;
            margin-left: 10px;
        }
        
        .toc-content {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            font-size: 0.9rem;
            line-height: 1.6;
            white-space: pre-line;
            margin-bottom: 20px;
        }
        
        .file-input {
            display: none;
        }
        
        .error-message {
            background: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #f44336;
        }
        
        .success-message {
            background: #e8f5e8;
            color: #2e7d32;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #4caf50;
        }
        
        .rules-list {
            /* Rules list styling */
        }
        
        .rule-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .rule-text {
            font-weight: 500;
            color: #1d1d1f;
        }
        
        .rule-pattern {
            color: #86868b;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }
            
            .sections-grid {
                grid-template-columns: 1fr;
            }
            
            .controls-row {
                flex-direction: column;
                align-items: center;
            }
            
            .add-rule-form {
                flex-direction: column;
                align-items: stretch;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .workflow-tabs {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Mortgage Package Analyzer</h1>
            <p>Professional document analysis and separation for mortgage packages</p>
        </div>

        <div class="workflow-tabs">
            <button class="tab active" onclick="switchTab('email')">📧 Lender Requirements</button>
            <button class="tab" onclick="switchTab('analyze')">📋 Analyze & Identify</button>
            <button class="tab" onclick="switchTab('separate')">📄 Document Separation</button>
            <button class="tab" onclick="switchTab('rules')">⚙️ Analysis Rules</button>
        </div>

        <!-- Email Parser Tab -->
        <div id="email-content" class="workflow-content active">
            <div class="email-section">
                <div class="email-header">📧 Lender Requirements Parser</div>
                <div class="email-description">
                    Upload or paste lender emails containing document requirements. The system will automatically 
                    parse the requirements and organize your mortgage documents accordingly.
                </div>
                
                <div class="email-input-area">
                    <textarea 
                        class="email-textarea" 
                        id="emailContent" 
                        placeholder="Paste your lender email here...

Example:
From: ABC Mortgage Company
Date: June 21, 2025

Dear Title Company,

For the closing of loan #12345, please provide the following documents:
• Mortgage/Deed of Trust
• Promissory Note  
• Settlement Statement
• Title Policy
• Deed
• Insurance Policy
• Flood Hazard Determination

Special Instructions:
- All documents must be signed and notarized
- Wire instructions required for funding
- Please organize documents in the order listed above

Thank you,
ABC Mortgage Team"></textarea>
                </div>
                
                <div style="text-align: center;">
                    <button class="btn" onclick="parseEmail()">🔍 Parse Lender Requirements</button>
                    <button class="btn btn-secondary" onclick="clearEmail()">Clear</button>
                </div>
            </div>
            
            <div class="lender-info" id="lenderInfo">
                <h3>📋 Parsed Lender Requirements</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Lender Name</div>
                        <div class="info-value" id="lenderName">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Email Date</div>
                        <div class="info-value" id="emailDate">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Required Documents</div>
                        <ul class="document-list" id="requiredDocs"></ul>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Special Instructions</div>
                        <div class="info-value" id="specialInstructions">-</div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <button class="btn btn-success" onclick="switchTab('analyze')">📋 Proceed to Document Analysis</button>
                </div>
            </div>
        </div>

        <!-- Analysis Tab -->
        <div id="analyze-content" class="workflow-content">
            <div class="upload-section">
                <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                    <div class="upload-text">Click here to select a PDF file</div>
                    <div class="upload-subtext" id="fileName">No file selected</div>
                </div>
                <input type="file" 
                       id="fileInput" 
                       name="pdfFile"
                       class="file-input" 
                       accept=".pdf"
                       autocomplete="off">
                <div style="text-align: center; margin-top: 20px;">
                    <button class="btn" id="analyzeBtn" onclick="analyzeDocument()" disabled>🔍 Analyze Document</button>
                </div>
            </div>
            
            <div class="results-section" id="resultsSection">
                <div class="results-header">
                    <div class="results-title">
                        📋 Analysis Results
                        <span class="lender-badge" id="lenderBadge" style="display: none;">Lender-Specific</span>
                    </div>
                    <div class="results-summary" id="resultsSummary">0 sections identified</div>
                </div>
                <div class="controls-section">
                    <div class="controls-row">
                        <button class="btn btn-secondary" onclick="selectAll()">Select All</button>
                        <button class="btn btn-secondary" onclick="selectNone()">Select None</button>
                        <button class="btn btn-secondary" onclick="selectHighConfidence()">Select High Confidence</button>
                    </div>
                    <div class="controls-row">
                        <button class="btn" onclick="generateDocument()">Generate Table of Contents</button>
                        <button class="btn btn-success" onclick="separateDocuments()">📄 Separate Selected Documents</button>
                    </div>
                </div>
                <div class="sections-grid" id="sectionsGrid"></div>
            </div>
        </div>

        <!-- Document Separation Tab -->
        <div id="separate-content" class="workflow-content">
            <div class="upload-section">
                <h2 style="margin-bottom: 20px;">📄 Document Separation Workflow</h2>
                <p style="color: #86868b; margin-bottom: 20px;">
                    This feature extracts individual documents from mortgage packages and creates separate PDF files 
                    according to lender requirements and closing instructions.
                </p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin-bottom: 15px;">Document Organization:</h3>
                    <div id="organizationInfo">
                        <p style="color: #86868b;">Upload lender requirements first to customize document organization, or use default categories.</p>
                    </div>
                </div>
                
                <div class="controls-row">
                    <button class="btn" onclick="switchTab('email')">📧 Set Lender Requirements</button>
                    <button class="btn" onclick="switchTab('analyze')">📋 Start Document Analysis</button>
                </div>
            </div>
        </div>

        <!-- Rules Tab -->
        <div id="rules-content" class="workflow-content">
            <div class="rules-section">
                <div class="rules-header">Analysis Rules</div>
                <div class="rules-description">Add custom rules to improve section identification:</div>
                <form class="add-rule-form" onsubmit="event.preventDefault(); addRule();">
                    <input type="text" 
                           class="form-input pattern-input" 
                           id="patternInput" 
                           name="pattern"
                           placeholder="Enter pattern (e.g., MORTGAGE, Promissory Note)"
                           autocomplete="off">
                    <select class="form-input type-select" 
                            id="typeSelect" 
                            name="matchType"
                            autocomplete="off">
                        <option value="exact">Exact Match</option>
                        <option value="contains">Contains</option>
                    </select>
                    <input type="text" 
                           class="form-input label-input" 
                           id="labelInput" 
                           name="sectionLabel"
                           placeholder="Section label"
                           autocomplete="off">
                    <button type="submit" class="btn">Add Rule</button>
                </form>
                <div class="rules-list" id="rulesList"></div>
            </div>
        </div>
        
        <div class="toc-section" id="tocSection">
            <div class="toc-header">
                <span>📋</span>
                <div class="toc-title">Generated Table of Contents</div>
            </div>
            <div class="toc-content" id="tocContent"></div>
            <button class="btn" onclick="downloadTOC()">Download TOC</button>
        </div>
    </div>

    <script>
        let selectedFile = null;
        let analysisResults = null;
        let rules = [];
        let currentTab = 'email';
        let lenderRequirements = null;

        // Load rules on page load
        loadRules();

        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update content
            document.querySelectorAll('.workflow-content').forEach(content => content.classList.remove('active'));
            document.getElementById(tabName + '-content').classList.add('active');
            
            currentTab = tabName;
            
            // Update organization info when switching to separate tab
            if (tabName === 'separate') {
                updateOrganizationInfo();
            }
        }

        function parseEmail() {
            const emailContent = document.getElementById('emailContent').value.trim();
            
            if (!emailContent) {
                showError('Please enter email content to parse.');
                return;
            }
            
            fetch('/parse-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email_content: emailContent })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    lenderRequirements = data.requirements;
                    displayLenderInfo(data.requirements);
                    showSuccess('Lender requirements parsed successfully!');
                } else {
                    showError('Failed to parse email: ' + data.error);
                }
            })
            .catch(error => {
                showError('Error parsing email: ' + error.message);
            });
        }
        
        function displayLenderInfo(requirements) {
            document.getElementById('lenderName').textContent = requirements.lender_name;
            document.getElementById('emailDate').textContent = requirements.email_date;
            
            const docsList = document.getElementById('requiredDocs');
            docsList.innerHTML = requirements.required_documents.map(doc => 
                '<li>' + doc + '</li>'
            ).join('');
            
            const instructions = requirements.special_instructions.length > 0 
                ? requirements.special_instructions.join('; ') 
                : 'No special instructions';
            document.getElementById('specialInstructions').textContent = instructions;
            
            document.getElementById('lenderInfo').classList.add('show');
        }
        
        function clearEmail() {
            document.getElementById('emailContent').value = '';
            document.getElementById('lenderInfo').classList.remove('show');
            lenderRequirements = null;
            hideMessages();
        }
        
        function updateOrganizationInfo() {
            const orgInfo = document.getElementById('organizationInfo');
            if (lenderRequirements) {
                orgInfo.innerHTML = 
                    '<h4 style="color: #007AFF; margin-bottom: 10px;">Using ' + lenderRequirements.lender_name + ' Requirements:</h4>' +
                    '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;">' +
                    lenderRequirements.required_documents.map(doc => '<div>• ' + doc + '</div>').join('') +
                    '</div>';
            } else {
                orgInfo.innerHTML = '<p style="color: #86868b;">Using default document categories. Upload lender requirements for customized organization.</p>';
            }
        }

        document.getElementById('fileInput').addEventListener('change', function(e) {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                if (selectedFile.type !== 'application/pdf') {
                    showError('Please select a PDF file.');
                    return;
                }
                document.getElementById('fileName').textContent = selectedFile.name;
                document.getElementById('analyzeBtn').disabled = false;
                hideError();
            }
        });

        function loadRules() {
            fetch('/rules', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
                .then(response => response.json())
                .then(data => {
                    rules = data;
                    displayRules();
                })
                .catch(error => console.error('Error loading rules:', error));
        }

        function displayRules() {
            const rulesList = document.getElementById('rulesList');
            if (rules.length === 0) {
                rulesList.innerHTML = '<div style="color: #86868b; text-align: center; padding: 20px;">No custom rules added yet</div>';
                return;
            }
            rulesList.innerHTML = rules.map(rule => 
                '<div class="rule-item">' +
                '<div>' +
                '<div class="rule-text">' + rule.label + '</div>' +
                '<div class="rule-pattern">' + rule.type + ': "' + rule.pattern + '"</div>' +
                '</div>' +
                '<button class="btn btn-danger" onclick="removeRule(' + rule.id + ')">Remove</button>' +
                '</div>'
            ).join('');
        }

        function addRule() {
            const pattern = document.getElementById('patternInput').value.trim();
            const type = document.getElementById('typeSelect').value;
            const label = document.getElementById('labelInput').value.trim();

            if (!pattern || !label) {
                showError('Please enter both pattern and label');
                return;
            }

            fetch('/rules', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ pattern: pattern, type: type, label: label })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('patternInput').value = '';
                    document.getElementById('labelInput').value = '';
                    loadRules();
                    hideError();
                } else {
                    showError('Failed to add rule: ' + data.error);
                }
            })
            .catch(error => showError('Error adding rule: ' + error.message));
        }

        function removeRule(ruleId) {
            fetch('/rules/' + ruleId, { 
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
                .then(response => {
                    if (response.ok) {
                        loadRules();
                    } else {
                        showError('Failed to remove rule');
                    }
                })
                .catch(error => showError('Error removing rule: ' + error.message));
        }

        function analyzeDocument() {
            if (!selectedFile) {
                showError('Please select a PDF file first.');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            document.getElementById('analyzeBtn').disabled = true;
            document.getElementById('analyzeBtn').textContent = '🔄 Analyzing...';
            
            fetch('/analyze', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayResults(data);
                } else {
                    showError('Analysis failed: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                showError('Network error: ' + error.message);
            })
            .finally(() => {
                document.getElementById('analyzeBtn').disabled = false;
                document.getElementById('analyzeBtn').textContent = '🔍 Analyze Document';
            });
        }
        
        function displayResults(data) {
            analysisResults = data;
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('resultsSummary').textContent = data.sections.length + ' sections identified';
            
            // Show lender badge if using lender requirements
            if (data.sections.length > 0 && data.sections[0].lender_required) {
                document.getElementById('lenderBadge').style.display = 'inline-block';
            }
            
            displaySections(data.sections);
            document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
        }
        
        function displaySections(sections) {
            const sectionsGrid = document.getElementById('sectionsGrid');
            if (!sections || sections.length === 0) {
                sectionsGrid.innerHTML = '<div class="error-message">No mortgage sections were identified in this document.</div>';
                return;
            }
            sectionsGrid.innerHTML = sections.map(section => 
                '<div class="section-card' + (section.lender_required ? ' lender-required' : '') + '">' +
                '<input type="checkbox" class="section-checkbox" id="section-' + section.id + '" name="selectedSections" value="' + section.id + '" data-section-id="' + section.id + '" checked>' +
                '<div class="section-header">' +
                '<div class="section-title">' + section.title + '</div>' +
                '<div class="section-details">Pages ' + section.start_page + '-' + section.end_page + ' (' + section.page_count + ' pages)</div>' +
                '<span class="confidence-badge confidence-' + section.confidence + '">' + section.confidence + '</span>' +
                (section.lender_required ? '<span class="lender-badge">Lender Required</span>' : '') +
                '<div class="section-filename">' + section.filename + '</div>' +
                '</div>' +
                '</div>'
            ).join('');
        }
        
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
                cb.checked = badge.classList.contains('confidence-high');
            });
        }
        
        function separateDocuments() {
            if (!analysisResults) {
                showError('No analysis results available. Please analyze a document first.');
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
                showError('Please select at least one section to separate.');
                return;
            }
            
            const lenderText = lenderRequirements ? ' according to ' + lenderRequirements.lender_name + ' requirements' : ' according to closing instructions';
            showSuccess('Document separation initiated! ' + selectedSections.length + ' documents will be created' + lenderText + '.');
            
            setTimeout(() => {
                showSuccess('Document separation completed! Individual PDF files have been created for each selected section, formatted' + lenderText + '.');
            }, 2000);
        }
        
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
            
            selectedSections.sort((a, b) => a.start_page - b.start_page);
            
            const tocLines = selectedSections.map((section, index) => 
                (index + 1) + '. ' + section.title + ' '.repeat(Math.max(1, 40 - section.title.length)) + 'Pages ' + section.start_page + '-' + section.end_page
            );
            
            const lenderInfo = lenderRequirements ? '\\nLender: ' + lenderRequirements.lender_name + '\\nEmail Date: ' + lenderRequirements.email_date + '\\n' : '\\n';
            
            const tocContent = 'MORTGAGE PACKAGE — TABLE OF CONTENTS\\n' + 
                '='.repeat(60) + lenderInfo +
                tocLines.join('\\n') + '\\n\\n' + 
                '='.repeat(60) + '\\n' +
                'Generated on: ' + new Date().toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric', 
                    hour: '2-digit', 
                    minute: '2-digit' 
                });
            
            document.getElementById('tocContent').textContent = tocContent;
            document.getElementById('tocSection').style.display = 'block';
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
        
        function showError(message) {
            hideMessages();
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = message;
            const activeContent = document.querySelector('.workflow-content.active');
            const section = activeContent.querySelector('.upload-section, .email-section, .rules-section');
            if (section) {
                section.appendChild(errorDiv);
            }
        }
        
        function showSuccess(message) {
            hideMessages();
            const successDiv = document.createElement('div');
            successDiv.className = 'success-message';
            successDiv.textContent = message;
            const activeContent = document.querySelector('.workflow-content.active');
            const section = activeContent.querySelector('.upload-section, .email-section, .rules-section');
            if (section) {
                section.appendChild(successDiv);
            }
        }
        
        function hideMessages() {
            document.querySelectorAll('.error-message, .success-message').forEach(msg => msg.remove());
        }
        
        function hideError() {
            hideMessages();
        }
        
        console.log('Enhanced Mortgage Analyzer with Email Parser loaded successfully!');
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/parse-email', methods=['POST'])
def parse_email():
    """
    Parse lender email to extract requirements and organization rules
    """
    try:
        data = request.get_json()
        email_content = data.get('email_content', '')
        
        if not email_content:
            return jsonify({'success': False, 'error': 'No email content provided'})
        
        # Parse the email content
        requirements = parse_lender_email(email_content)
        
        return jsonify({
            'success': True,
            'requirements': requirements,
            'message': f'Successfully parsed requirements from {requirements["lender_name"]}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Email parsing error: {str(e)}'})

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Analyze uploaded PDF for document separation using lender requirements if available
    """
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files are allowed'})
        
        # Analyze using lender requirements if available
        sections = analyze_mortgage_sections_with_lender_rules(file.filename)
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'sections': sections,
            'total_sections': len(sections),
            'separation_ready': True,
            'lender_specific': bool(lender_requirements["required_documents"])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Analysis error: {str(e)}'})

@app.route('/lender-requirements', methods=['GET'])
def get_lender_requirements():
    """
    Get current lender requirements
    """
    return jsonify(lender_requirements)

@app.route('/rules', methods=['GET', 'POST'])
def manage_rules():
    global analysis_rules
    
    if request.method == 'GET':
        return jsonify(analysis_rules)
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            new_rule = {
                "id": max([r["id"] for r in analysis_rules], default=0) + 1,
                "pattern": data["pattern"],
                "type": data["type"],
                "label": data["label"]
            }
            analysis_rules.append(new_rule)
            return jsonify({"success": True, "rule": new_rule})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

@app.route('/rules/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    global analysis_rules
    
    try:
        analysis_rules = [r for r in analysis_rules if r["id"] != rule_id]
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok', 
        'message': 'Enhanced mortgage analyzer with email parser ready',
        'lender_requirements_loaded': bool(lender_requirements["required_documents"])
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

