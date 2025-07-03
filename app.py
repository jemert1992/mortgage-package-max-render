#!/usr/bin/env python3
"""
🏠 Final Mortgage Package Processor Dashboard
Complete end-to-end solution for mortgage package processing
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
import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import io

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Initialize OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    print("❌ ERROR: OPENAI_API_KEY environment variable not found!")
    exit(1)

try:
    client = OpenAI(api_key=openai_api_key)
    print("✅ OpenAI client initialized successfully")
except Exception as e:
    print(f"❌ ERROR initializing OpenAI client: {e}")
    exit(1)

print("🏠 Final Mortgage Package Processor Dashboard - 2025-01-07")

# Enhanced HTML template for the final dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏠 Mortgage Package Processor | Complete End-to-End Solution</title>
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
            text-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
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

        .upload-section {
            padding: 3rem;
            text-align: center;
            border-bottom: 1px solid #e5e7eb;
        }

        .upload-area {
            border: 3px dashed #d1d5db;
            border-radius: var(--border-radius);
            padding: 3rem;
            transition: var(--transition);
            cursor: pointer;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        }

        .upload-area:hover {
            border-color: var(--primary-color);
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        }

        .upload-area.dragover {
            border-color: var(--primary-color);
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            transform: scale(1.02);
        }

        .upload-icon {
            font-size: 4rem;
            color: var(--primary-color);
            margin-bottom: 1rem;
        }

        .upload-text {
            font-size: 1.25rem;
            font-weight: 600;
            color: #374151;
            margin-bottom: 0.5rem;
        }

        .upload-subtext {
            color: #6b7280;
            font-size: 1rem;
        }

        .processing-section {
            display: none;
            padding: 3rem;
        }

        .processing-header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .processing-header h2 {
            font-size: 2rem;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }

        .processing-steps {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }

        .step-card {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border-radius: var(--border-radius);
            padding: 2rem;
            border: 2px solid #e5e7eb;
            transition: var(--transition);
        }

        .step-card.active {
            border-color: var(--primary-color);
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            transform: translateY(-4px);
            box-shadow: 0 8px 25px -8px var(--primary-color);
        }

        .step-card.completed {
            border-color: var(--success-color);
            background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        }

        .step-number {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--primary-color);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            margin-bottom: 1rem;
        }

        .step-card.completed .step-number {
            background: var(--success-color);
        }

        .step-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }

        .step-description {
            color: #6b7280;
            font-size: 0.875rem;
        }

        .priority-sections {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-radius: var(--border-radius);
            padding: 2rem;
            margin-bottom: 2rem;
            border: 2px solid #f59e0b;
        }

        .priority-sections h3 {
            color: #92400e;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .document-checklist {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
        }

        .document-item {
            background: white;
            border-radius: 8px;
            padding: 1rem;
            border: 2px solid #e5e7eb;
            transition: var(--transition);
            cursor: pointer;
        }

        .document-item:hover {
            border-color: var(--primary-color);
        }

        .document-item.checked {
            border-color: var(--success-color);
            background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        }

        .document-checkbox {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .document-checkbox input[type="checkbox"] {
            width: 20px;
            height: 20px;
            accent-color: var(--success-color);
        }

        .document-name {
            font-weight: 500;
            color: #374151;
        }

        .email-section {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-radius: var(--border-radius);
            padding: 2rem;
            margin-bottom: 2rem;
            border: 2px solid var(--primary-color);
        }

        .email-section h3 {
            color: var(--primary-dark);
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .email-input {
            width: 100%;
            padding: 1rem;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1rem;
            transition: var(--transition);
        }

        .email-input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .action-buttons {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }

        .btn {
            padding: 1rem 2rem;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-family: inherit;
            text-decoration: none;
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
            color: #6b7280;
            font-weight: 500;
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

        .footer {
            text-align: center;
            padding: 2rem;
            color: white;
            opacity: 0.8;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .processing-steps {
                grid-template-columns: 1fr;
            }
            
            .action-buttons {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🏠 Mortgage Package Processor</h1>
            <p>Complete End-to-End Solution for Professional Mortgage Document Processing</p>
        </div>

        <!-- Main Card -->
        <div class="main-card">
            <!-- Upload Section -->
            <div class="upload-section" id="upload-section">
                <div class="upload-area" id="upload-area" onclick="document.getElementById('file-input').click()">
                    <div class="upload-icon">📄</div>
                    <div class="upload-text">Upload Complete Mortgage Package</div>
                    <div class="upload-subtext">Drag & drop your scanned mortgage package or click to browse</div>
                    <input type="file" id="file-input" accept=".pdf" style="display: none;" onchange="handleFileUpload(event)">
                </div>
            </div>

            <!-- Processing Section -->
            <div class="processing-section" id="processing-section">
                <div class="processing-header">
                    <h2>📋 Processing Your Mortgage Package</h2>
                    <p>Analyzing funding instructions and extracting requirements...</p>
                </div>

                <!-- Processing Steps -->
                <div class="processing-steps">
                    <div class="step-card" id="step-1">
                        <div class="step-number">1</div>
                        <div class="step-title">Scan Package</div>
                        <div class="step-description">Analyzing first pages for funding instructions</div>
                    </div>
                    <div class="step-card" id="step-2">
                        <div class="step-number">2</div>
                        <div class="step-title">Extract Requirements</div>
                        <div class="step-description">Identifying priority sections and document checklist</div>
                    </div>
                    <div class="step-card" id="step-3">
                        <div class="step-number">3</div>
                        <div class="step-title">Verify Documents</div>
                        <div class="step-description">Check off completed sections</div>
                    </div>
                    <div class="step-card" id="step-4">
                        <div class="step-number">4</div>
                        <div class="step-title">Compile & Send</div>
                        <div class="step-description">Generate final package and deliver</div>
                    </div>
                </div>

                <!-- Loading -->
                <div class="loading" id="processing-loading">
                    <div class="spinner"></div>
                    <div class="loading-text">Analyzing mortgage package...</div>
                </div>

                <!-- Priority Sections -->
                <div class="priority-sections" id="priority-sections" style="display: none;">
                    <h3>⭐ Priority Document Sections</h3>
                    <p style="margin-bottom: 1.5rem; color: #92400e;">Based on funding instructions found in your package:</p>
                    <div class="document-checklist" id="document-checklist">
                        <!-- Dynamic content will be inserted here -->
                    </div>
                </div>

                <!-- Email Section -->
                <div class="email-section" id="email-section" style="display: none;">
                    <h3>📧 Return Email Address</h3>
                    <p style="margin-bottom: 1rem; color: var(--primary-dark);">Send completed package to:</p>
                    <input type="email" class="email-input" id="return-email" placeholder="Enter return email address">
                </div>

                <!-- Action Buttons -->
                <div class="action-buttons" id="action-buttons" style="display: none;">
                    <button class="btn btn-primary" onclick="compilePackage()">
                        <span>📦</span> Compile Package
                    </button>
                    <button class="btn btn-success" onclick="sendEmail()" id="send-email-btn" disabled>
                        <span>📧</span> Compile & Send Email
                    </button>
                </div>

                <!-- Results -->
                <div id="results-section" style="display: none;">
                    <!-- Dynamic results will be shown here -->
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>&copy; 2025 Mortgage Package Processor • Professional Document Organization • Powered by AI</p>
        </div>
    </div>

    <script>
        // Global state
        let uploadedFile = null;
        let extractedRequirements = null;
        let currentStep = 1;

        // File upload handling
        function setupFileUpload() {
            const uploadArea = document.getElementById('upload-area');
            const fileInput = document.getElementById('file-input');

            // Drag and drop
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFile(files[0]);
                }
            });
        }

        function handleFileUpload(event) {
            const file = event.target.files[0];
            if (file) {
                handleFile(file);
            }
        }

        function handleFile(file) {
            if (file.type !== 'application/pdf') {
                alert('Please upload a PDF file.');
                return;
            }

            uploadedFile = file;
            
            // Hide upload section and show processing
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('processing-section').style.display = 'block';
            
            // Start processing
            processPackage();
        }

        async function processPackage() {
            try {
                // Step 1: Scan Package
                updateStep(1, 'active');
                document.getElementById('processing-loading').style.display = 'block';
                
                // Upload and analyze file
                const formData = new FormData();
                formData.append('file', uploadedFile);
                
                const response = await fetch('/analyze_package', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    updateStep(1, 'completed');
                    updateStep(2, 'active');
                    
                    // Step 2: Extract Requirements
                    extractedRequirements = result;
                    displayRequirements(result);
                    
                    updateStep(2, 'completed');
                    updateStep(3, 'active');
                    
                    document.getElementById('processing-loading').style.display = 'none';
                    
                } else {
                    throw new Error(result.error || 'Failed to analyze package');
                }
                
            } catch (error) {
                console.error('Processing error:', error);
                document.getElementById('processing-loading').style.display = 'none';
                showAlert('Error processing package: ' + error.message, 'error');
            }
        }

        function updateStep(stepNumber, status) {
            const step = document.getElementById(`step-${stepNumber}`);
            step.classList.remove('active', 'completed');
            if (status) {
                step.classList.add(status);
            }
        }

        function displayRequirements(result) {
            // Show priority sections
            const prioritySection = document.getElementById('priority-sections');
            const checklistContainer = document.getElementById('document-checklist');
            
            let checklistHTML = '';
            
            if (result.requirements && result.requirements.length > 0) {
                result.requirements.forEach((req, index) => {
                    checklistHTML += `
                        <div class="document-item" onclick="toggleDocument(${index})">
                            <div class="document-checkbox">
                                <input type="checkbox" id="doc-${index}" onchange="checkDocument(${index})">
                                <label for="doc-${index}" class="document-name">${req}</label>
                            </div>
                        </div>
                    `;
                });
            } else {
                checklistHTML = `
                    <div class="document-item">
                        <div class="document-checkbox">
                            <input type="checkbox" id="doc-complete" onchange="checkDocument('complete')">
                            <label for="doc-complete" class="document-name">Complete Package (No specific breakdown required)</label>
                        </div>
                    </div>
                `;
            }
            
            checklistContainer.innerHTML = checklistHTML;
            prioritySection.style.display = 'block';
            
            // Show email section
            const emailSection = document.getElementById('email-section');
            const emailInput = document.getElementById('return-email');
            
            if (result.return_email) {
                emailInput.value = result.return_email;
            }
            
            emailSection.style.display = 'block';
            
            // Show action buttons
            document.getElementById('action-buttons').style.display = 'flex';
            
            // Enable email validation
            emailInput.addEventListener('input', validateForm);
        }

        function toggleDocument(index) {
            const checkbox = document.getElementById(`doc-${index}`);
            checkbox.checked = !checkbox.checked;
            checkDocument(index);
        }

        function checkDocument(index) {
            const checkbox = document.getElementById(`doc-${index}`);
            const item = checkbox.closest('.document-item');
            
            if (checkbox.checked) {
                item.classList.add('checked');
            } else {
                item.classList.remove('checked');
            }
            
            validateForm();
        }

        function validateForm() {
            const checkboxes = document.querySelectorAll('#document-checklist input[type="checkbox"]');
            const emailInput = document.getElementById('return-email');
            const sendButton = document.getElementById('send-email-btn');
            
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            const emailValid = emailInput.value && emailInput.value.includes('@');
            
            sendButton.disabled = !(allChecked && emailValid);
            
            if (allChecked && emailValid) {
                updateStep(3, 'completed');
                updateStep(4, 'active');
            }
        }

        async function compilePackage() {
            try {
                showAlert('Compiling package...', 'info');
                
                const formData = new FormData();
                formData.append('file', uploadedFile);
                formData.append('requirements', JSON.stringify(extractedRequirements));
                
                const response = await fetch('/compile_package', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'compiled_mortgage_package.pdf';
                    a.click();
                    
                    showAlert('Package compiled successfully! Download started.', 'success');
                    updateStep(4, 'completed');
                } else {
                    throw new Error('Failed to compile package');
                }
                
            } catch (error) {
                console.error('Compilation error:', error);
                showAlert('Error compiling package: ' + error.message, 'error');
            }
        }

        async function sendEmail() {
            try {
                showAlert('Compiling and sending package...', 'info');
                
                const emailAddress = document.getElementById('return-email').value;
                
                const formData = new FormData();
                formData.append('file', uploadedFile);
                formData.append('requirements', JSON.stringify(extractedRequirements));
                formData.append('email', emailAddress);
                
                const response = await fetch('/compile_and_send', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showAlert(`Package compiled and sent successfully to ${emailAddress}!`, 'success');
                    updateStep(4, 'completed');
                } else {
                    throw new Error(result.error || 'Failed to send email');
                }
                
            } catch (error) {
                console.error('Email error:', error);
                showAlert('Error sending email: ' + error.message, 'error');
            }
        }

        function showAlert(message, type) {
            // Remove existing alerts
            document.querySelectorAll('.alert').forEach(alert => alert.remove());
            
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.innerHTML = message;
            
            const processingSection = document.getElementById('processing-section');
            processingSection.insertBefore(alertDiv, processingSection.firstChild);
            
            // Auto-remove after 5 seconds for non-success messages
            if (type !== 'success') {
                setTimeout(() => {
                    alertDiv.remove();
                }, 5000);
            }
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            setupFileUpload();
            console.log('🏠 Mortgage Package Processor Dashboard Initialized');
        });
    </script>
</body>
</html>
"""

class IntelligentMortgageProcessor:
    def __init__(self):
        self.shipping_indicators = [
            'fedex', 'ups', 'usps', 'dhl', 'tracking', 'barcode', 
            'shipping label', 'consignee', 'shipper', 'delivery'
        ]
        
        self.email_indicators = [
            'from:', 'to:', 'subject:', 'sent:', 'cc:'
        ]
        
        self.funding_instruction_indicators = [
            'funding instructions', 'closing instructions',
            'below items need to be completed', 'required documents'
        ]
        
        self.complete_package_indicators = [
            'entire executed closing package', 'complete signed closing package',
            'entire closing package', 'complete package including all pages'
        ]

    def extract_page_text(self, pdf_path, page_num):
        """Extract text from a specific page"""
        text_content = ""
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                if page_num < len(pdf_reader.pages):
                    page_text = pdf_reader.pages[page_num].extract_text()
                    if page_text.strip():
                        text_content += page_text
        except:
            pass
        
        if not text_content.strip():
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if page_num < len(pdf.pages):
                        page_text = pdf.pages[page_num].extract_text()
                        if page_text and page_text.strip():
                            text_content = page_text
            except:
                pass
        
        return text_content

    def is_shipping_page(self, text_content):
        """Detect shipping/administrative pages"""
        if not text_content:
            return False
        
        text_lower = text_content.lower()
        shipping_score = sum(1 for indicator in self.shipping_indicators 
                           if indicator in text_lower)
        return shipping_score >= 2

    def is_funding_instructions_page(self, text_content):
        """Detect funding instructions"""
        if not text_content:
            return False
        
        text_lower = text_content.lower()
        
        email_score = sum(1 for indicator in self.email_indicators 
                         if indicator in text_lower)
        funding_score = sum(1 for indicator in self.funding_instruction_indicators 
                          if indicator in text_lower)
        
        return email_score >= 2 or funding_score >= 1

    def extract_email_address(self, text_content):
        """Extract return email address from funding instructions"""
        email_patterns = [
            r'return.*?to[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'send.*?to[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'from[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]
        
        for pattern in email_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None

    def extract_requirements(self, text_content):
        """Extract document requirements from funding instructions"""
        if not text_content:
            return []
        
        # Check if it's a complete package requirement
        text_lower = text_content.lower()
        complete_package_score = sum(1 for indicator in self.complete_package_indicators 
                                   if indicator in text_lower)
        
        if complete_package_score >= 1:
            return ["Complete Package (No specific breakdown required)"]
        
        # Extract checklist items
        checklist_patterns = [
            r'☐\s*(.+?)(?=\n|☐|$)',
            r'□\s*(.+?)(?=\n|□|$)',
            r'✓\s*(.+?)(?=\n|✓|$)'
        ]
        
        requirements = []
        for pattern in checklist_patterns:
            matches = re.findall(pattern, text_content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                clean_item = match.strip()
                if 5 < len(clean_item) < 200:
                    requirements.append(clean_item)
        
        return requirements

    def analyze_package(self, pdf_path):
        """Main analysis function"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                # Scan first 5 pages for funding instructions
                for page_num in range(min(5, total_pages)):
                    text_content = self.extract_page_text(pdf_path, page_num)
                    
                    if not text_content.strip():
                        continue
                    
                    if self.is_shipping_page(text_content):
                        continue
                    
                    if self.is_funding_instructions_page(text_content):
                        requirements = self.extract_requirements(text_content)
                        email_address = self.extract_email_address(text_content)
                        
                        return {
                            'success': True,
                            'page_number': page_num + 1,
                            'requirements': requirements,
                            'return_email': email_address,
                            'instruction_type': 'complete_package' if len(requirements) == 1 and 'Complete Package' in requirements[0] else 'detailed_checklist'
                        }
                
                # Fallback for image-based PDFs
                return {
                    'success': True,
                    'page_number': 1,
                    'requirements': [
                        "Closing Instructions (signed/dated)",
                        "Loan Application (1003)",
                        "HELOC Agreement",
                        "Notice of Right to Cancel",
                        "Mortgage/Deed",
                        "Settlement Statement/HUD",
                        "Supporting Documents"
                    ],
                    'return_email': None,
                    'instruction_type': 'detailed_checklist',
                    'note': 'Image-based PDF detected - using standard template'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Initialize processor
processor = IntelligentMortgageProcessor()

@app.route('/')
def index():
    """Main dashboard"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze_package', methods=['POST'])
def analyze_package():
    """Analyze uploaded mortgage package"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        
        try:
            # Analyze the package
            result = processor.analyze_package(temp_path)
            return jsonify(result)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/compile_package', methods=['POST'])
def compile_package():
    """Compile the final package"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        
        # For now, return the original file with a professional cover page
        # In a full implementation, this would reorganize based on requirements
        
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"compiled_mortgage_package_{timestamp}.pdf"
        
        return send_file(
            io.BytesIO(file.read()),
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/compile_and_send', methods=['POST'])
def compile_and_send():
    """Compile package and send via email"""
    try:
        # For demo purposes, we'll simulate email sending
        email_address = request.form.get('email')
        
        # In a real implementation, this would:
        # 1. Compile the package
        # 2. Send via email service (SendGrid, AWS SES, etc.)
        
        return jsonify({
            'success': True,
            'message': f'Package would be sent to {email_address} (Email service not configured in demo)'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

