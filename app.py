#!/usr/bin/env python3
"""
🏠 Mortgage Package Reorganizer - Professional Edition
A sleek, professional tool for reorganizing mortgage documents based on lender requirements
"""

import os
import json
import re
import tempfile
import traceback
import gc
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

print("✅ Mortgage Package Reorganizer - Professional Edition initialized")
print("🏠 PROFESSIONAL MORTGAGE EDITION - 2025-01-07")

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
            --background-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100% );
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

        /* Header Section */
        .header {
            text-align: center;
            margin-bottom: 3rem;
            color: white;
        }

        .header h1 {
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            background: linear-gradient(45deg, #ffffff, #e0e7ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .header .subtitle {
            font-size: 1.25rem;
            opacity: 0.95;
            font-weight: 400;
            margin-bottom: 0.5rem;
        }

        .header .tagline {
            font-size: 1rem;
            opacity: 0.8;
            font-weight: 300;
        }

        /* Main Workflow Container */
        .workflow-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: var(--border-radius);
            box-shadow: var(--card-shadow);
            overflow: hidden;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        /* Progress Steps */
        .progress-steps {
            display: flex;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border-bottom: 1px solid #e2e8f0;
            position: relative;
        }

        .progress-steps::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 2px;
            background: #e2e8f0;
            z-index: 1;
        }

        .step {
            flex: 1;
            padding: 2rem 1.5rem;
            text-align: center;
            position: relative;
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

        textarea.form-control {
            min-height: 140px;
            resize: vertical;
            line-height: 1.6;
        }

        /* File Upload Area */
        .file-upload-area {
            border: 3px dashed #d1d5db;
            border-radius: var(--border-radius);
            padding: 3rem 2rem;
            text-align: center;
            transition: var(--transition);
            cursor: pointer;
            background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
            position: relative;
            overflow: hidden;
        }

        .file-upload-area::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(37, 99, 235, 0.05) 50%, transparent 70%);
            transform: translateX(-100%);
            transition: transform 0.6s ease;
        }

        .file-upload-area:hover::before {
            transform: translateX(100%);
        }

        .file-upload-area:hover {
            border-color: var(--primary-color);
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            transform: translateY(-2px);
        }

        .file-upload-area.dragover {
            border-color: var(--primary-color);
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            transform: scale(1.02);
        }

        .upload-icon {
            font-size: 4rem;
            margin-bottom: 1.5rem;
            color: #9ca3af;
            transition: var(--transition);
        }

        .file-upload-area:hover .upload-icon {
            color: var(--primary-color);
            transform: scale(1.1);
        }

        .upload-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #374151;
            margin-bottom: 0.5rem;
        }

        .upload-subtitle {
            color: #6b7280;
            font-size: 1rem;
        }

        /* Buttons */
        .btn {
            padding: 0.875rem 2rem;
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
            margin: 0 auto 1.5rem;
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

        /* File List */
        .file-list {
            margin-top: 2rem;
        }

        .file-item {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: var(--transition);
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .file-item:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .file-info {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .file-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 0.875rem;
        }

        .file-details h4 {
            margin: 0 0 0.25rem 0;
            color: #374151;
            font-weight: 600;
        }

        .file-details p {
            margin: 0;
            color: #6b7280;
            font-size: 0.875rem;
        }

        /* Progress Bar */
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 1.5rem;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary-color), var(--primary-dark));
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 4px;
        }

        /* Requirements Display */
        .requirements-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 1.5rem;
        }

        .requirement-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .requirement-card h4 {
            color: var(--primary-color);
            font-weight: 600;
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
            color: #374151;
        }

        .requirement-list li:last-child {
            border-bottom: none;
        }

        .requirement-list li::before {
            content: '✓';
            color: var(--success-color);
            font-weight: bold;
            margin-right: 0.75rem;
        }

        /* Footer */
        .footer {
            text-align: center;
            color: rgba(255, 255, 255, 0.9);
            margin-top: 3rem;
            padding: 2rem;
        }

        .footer p {
            font-size: 0.875rem;
            font-weight: 400;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .progress-steps {
                flex-direction: column;
            }
            
            .progress-steps::before {
                display: none;
            }
            
            .header h1 {
                font-size: 2.5rem;
            }
            
            .content-area {
                padding: 2rem 1.5rem;
            }
            
            .content-header h2 {
                font-size: 1.75rem;
            }
            
            .requirements-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Animations */
        .fade-in {
            animation: fadeIn 0.6s ease-out;
        }

        .slide-up {
            animation: slideUp 0.6s ease-out;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary-color);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-dark);
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header fade-in">
            <h1>🏠 Mortgage Package Reorganizer</h1>
            <p class="subtitle">Professional Document Organization Platform</p>
            <p class="tagline">Streamline your mortgage workflow with AI-powered document reorganization</p>
        </div>

        <!-- Main Workflow -->
        <div class="workflow-container slide-up">
            <!-- Progress Steps -->
            <div class="progress-steps">
                <div class="step active" data-step="1">
                    <div class="step-indicator">1</div>
                    <div class="step-title">Parse Requirements</div>
                    <div class="step-description">Extract lender specifications from email</div>
                </div>
                <div class="step" data-step="2">
                    <div class="step-indicator">2</div>
                    <div class="step-title">Upload Documents</div>
                    <div class="step-description">Upload mortgage package for analysis</div>
                </div>
                <div class="step" data-step="3">
                    <div class="step-indicator">3</div>
                    <div class="step-title">Generate Package</div>
                    <div class="step-description">Create reorganized professional PDF</div>
                </div>
            </div>

            <!-- Content Area -->
            <div class="content-area">
                <!-- Step 1: Parse Requirements -->
                <div class="step-content active" id="step-1">
                    <div class="content-header">
                        <h2>📧 Parse Lender Requirements</h2>
                        <p>Extract specific document organization requirements from lender communications to ensure compliance and proper structuring.</p>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label" for="lender-email">
                            Lender Email or Requirements Document
                        </label>
                        <textarea 
                            id="lender-email" 
                            class="form-control" 
                            placeholder="Paste the complete lender email or requirements document here. Include any specific instructions about document order, formatting requirements, or submission guidelines..."
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
                        <h3>📋 Extracted Requirements</h3>
                        <div id="requirements-content"></div>
                    </div>
                </div>

                <!-- Step 2: Upload Documents -->
                <div class="step-content" id="step-2">
                    <div class="content-header">
                        <h2>📄 Upload Mortgage Package</h2>
                        <p>Upload your mortgage package PDF for intelligent analysis and reorganization according to the parsed lender requirements.</p>
                    </div>
                    
                    <div class="file-upload-area" id="upload-area">
                        <div class="upload-icon">📁</div>
                        <h3 class="upload-title">Drop PDF files here or click to browse</h3>
                        <p class="upload-subtitle">Supports PDF files up to 50MB • Secure processing • No data retention</p>
                        <input type="file" id="file-input" accept=".pdf" multiple style="display: none;">
                    </div>

                    <div class="file-list" id="file-list"></div>

                    <div class="loading" id="upload-loading">
                        <div class="spinner"></div>
                        <p class="loading-text">Analyzing document structure and content...</p>
                    </div>

                    <div class="results-area" id="upload-results" style="display: none;">
                        <h3>📊 Document Analysis Complete</h3>
                        <div id="analysis-content"></div>
                        <button class="btn btn-primary" onclick="proceedToGeneration()">
                            <span>➡️</span> Proceed to Generation
                        </button>
                    </div>
                </div>

                <!-- Step 3: Generate Package -->
                <div class="step-content" id="step-3">
                    <div class="content-header">
                        <h2>🎯 Generate Reorganized Package</h2>
                        <p>Create a professionally organized PDF package that meets all lender requirements and industry standards.</p>
                    </div>
                    
                    <div class="alert alert-info">
                        <strong>Ready for Generation!</strong> Your documents will be intelligently reorganized according to the parsed lender requirements, ensuring compliance and professional presentation.
                    </div>

                    <button class="btn btn-success" onclick="generateReorganizedPDF()">
                        <span>🚀</span> Generate Professional Package
                    </button>

                    <div class="loading" id="generate-loading">
                        <div class="spinner"></div>
                        <p class="loading-text">Reorganizing documents with AI precision...</p>
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
            <p>© 2025 Mortgage Package Reorganizer • Professional Document Organization • Powered by AI</p>
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
            console.log('🏠 Mortgage Package Reorganizer - Professional Edition Initialized');
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
            
            // Show target step content with animation
            const targetContent = document.getElementById(`step-${stepNumber}`);
            targetContent.classList.add('active');
            targetContent.classList.add('fade-in');
            
            // Update step indicators
            for (let i = 1; i <= 3; i++) {
                const step = document.querySelector(`[data-step="${i}"]`);
                if (i < stepNumber) {
                    step.classList.add('completed');
                    step.classList.remove('active');
                } else if (i === stepNumber) {
                    step.classList.add('active');
                    step.classList.remove('completed');
                } else {
                    step.classList.remove('completed', 'active');
                }
            }
            
            currentStep = stepNumber;
        }

        // Parse lender requirements
        async function parseLenderRequirements() {
            const emailContent = document.getElementById('lender-email').value.trim();
            
            if (!emailContent) {
                showAlert('Please enter the lender email or requirements document.', 'error');
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
                        email_content: emailContent,
                        industry: 'mortgage'
                    })
                });

                const result = await response.json();
                
                if (result.success) {
                    lastLenderRequirements = result.requirements;
                    displayRequirements(result.requirements);
                    showResults('parse-results', true);
                    
                    // Auto-advance to next step
                    setTimeout(() => {
                        goToStep(2);
                    }, 2000);
                } else {
                    showAlert(result.error || 'Failed to parse requirements', 'error');
                }
            } catch (error) {
                console.error('Error parsing requirements:', error);
                showAlert('Network error occurred while parsing requirements', 'error');
            } finally {
                showLoading('parse-loading', false);
            }
        }

        // Display parsed requirements
        function displayRequirements(requirements) {
            const content = document.getElementById('requirements-content');
            let html = '<div class="alert alert-success">✅ Requirements successfully parsed and analyzed!</div>';
            
            html += '<div class="requirements-grid">';
            
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
            
            if (requirements.special_instructions) {
                html += `
                    <div class="requirement-card">
                        <h4>📝 Special Instructions</h4>
                        <p>${requirements.special_instructions}</p>
                    </div>
                `;
            }
            
            if (requirements.priority_documents && requirements.priority_documents.length > 0) {
                html += `
                    <div class="requirement-card">
                        <h4>⭐ Priority Documents</h4>
                        <ul class="requirement-list">
                `;
                requirements.priority_documents.forEach(doc => {
                    html += `<li>${doc}</li>`;
                });
                html += '</ul></div>';
            }
            
            html += '</div>';
            content.innerHTML = html;
        }

        // Setup file upload functionality
        function setupFileUpload() {
            const uploadArea = document.getElementById('upload-area');
            const fileInput = document.getElementById('file-input');
            
            uploadArea.addEventListener('click', () => fileInput.click());
            
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
                handleFiles(e.dataTransfer.files);
            });
            
            fileInput.addEventListener('change', (e) => {
                handleFiles(e.target.files);
            });
        }

        // Handle file uploads
        async function handleFiles(files) {
            if (files.length === 0) return;
            
            const fileList = document.getElementById('file-list');
            fileList.innerHTML = '';
            
            showLoading('upload-loading', true);
            
            const formData = new FormData();
            
            for (let file of files) {
                if (file.type === 'application/pdf') {
                    formData.append('files', file);
                    
                    // Track the first PDF file for reorganization
                    if (!uploadedPdfPath) {
                        uploadedPdfPath = `/tmp/${file.name}`;
                        console.log('🔍 Tracked PDF path for reorganization:', uploadedPdfPath);
                    }
                    
                    // Add file to display list
                    addFileToList(file);
                }
            }
            
            formData.append('industry', 'mortgage');
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    lastAnalysisResults = result;
                    displayAnalysisResults(result);
                    showResults('upload-results', true);
                } else {
                    showAlert(result.error || 'Failed to analyze documents', 'error');
                }
            } catch (error) {
                console.error('Error uploading files:', error);
                showAlert('Network error occurred during upload', 'error');
            } finally {
                showLoading('upload-loading', false);
            }
        }

        // Add file to display list
        function addFileToList(file) {
            const fileList = document.getElementById('file-list');
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            fileItem.innerHTML = `
                <div class="file-info">
                    <div class="file-icon">PDF</div>
                    <div class="file-details">
                        <h4>${file.name}</h4>
                        <p>${(file.size / 1024 / 1024).toFixed(2)} MB • PDF Document</p>
                    </div>
                </div>
            `;
            
            fileList.appendChild(fileItem);
        }

        // Display analysis results
        function displayAnalysisResults(results) {
            const content = document.getElementById('analysis-content');
            let html = '<div class="alert alert-success">✅ Document analysis completed successfully!</div>';
            
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
                        <h4>📈 Analysis Summary</h4>
                        <p><strong>Total Files:</strong> ${results.total_files || 1}</p>
                        <p><strong>Document Sections:</strong> ${results.sections.length}</p>
                        <p><strong>Industry:</strong> ${results.industry || 'Mortgage'}</p>
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
                
                console.log('🔍 Sending reorganization data:', reorganizationData);
                
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
                    const filename = `professional_mortgage_package_${timestamp}.pdf`;
                    
                    displayDownloadLink(url, filename, blob.size);
                    showResults('generate-results', true);
                    
                    showAlert('Professional mortgage package generated successfully!', 'success');
                } else {
                    const errorResult = await response.json();
                    showAlert(errorResult.error || 'Failed to generate PDF', 'error');
                }
            } catch (error) {
                console.error('PDF reorganization error:', error);
                showAlert('Network error occurred during PDF generation', 'error');
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
                    <strong>🎉 Success!</strong> Your professional mortgage package has been generated and is ready for download.
                </div>
                <div class="requirements-grid">
                    <div class="requirement-card">
                        <h4>📥 Download Package</h4>
                        <a href="${url}" download="${filename}" class="btn btn-success">
                            <span>📥</span> Download Professional Package
                        </a>
                        <p style="margin-top: 1rem; color: #6b7280; font-size: 0.875rem;">
                            <strong>File:</strong> ${filename}<br>
                            <strong>Size:</strong> ${fileSizeMB} MB<br>
                            <strong>Generated:</strong> ${new Date().toLocaleString()}
                        </p>
                    </div>
                    <div class="requirement-card">
                        <h4>✅ Package Features</h4>
                        <ul class="requirement-list">
                            <li>Professional cover page</li>
                            <li>Lender requirement compliance</li>
                            <li>Organized document sections</li>
                            <li>Industry-standard formatting</li>
                            <li>Complete page preservation</li>
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

# Enhanced document classification keywords for mortgage industry
MORTGAGE_DOCUMENT_KEYWORDS = {
    "loan_application": [
        "loan application", "1003", "uniform residential loan application", 
        "borrower information", "employment information", "monthly income",
        "fannie mae", "freddie mac", "application form"
    ],
    "income_documentation": [
        "pay stub", "w-2", "tax return", "1040", "employment verification", 
        "voe", "income statement", "salary verification", "paystub",
        "wage statement", "earnings statement", "payroll"
    ],
    "asset_documentation": [
        "bank statement", "asset verification", "savings account", "checking account",
        "investment account", "401k", "retirement account", "voa", "asset letter",
        "financial statement", "account statement", "balance verification"
    ],
    "credit_documentation": [
        "credit report", "credit score", "tri-merge", "credit authorization",
        "credit inquiry", "fico score", "credit history", "credit analysis"
    ],
    "property_documentation": [
        "appraisal", "property valuation", "home inspection", "survey",
        "title report", "deed", "property tax", "homeowners insurance",
        "property report", "valuation report", "inspection report"
    ],
    "loan_documentation": [
        "loan estimate", "closing disclosure", "promissory note", "deed of trust",
        "mortgage note", "loan terms", "interest rate", "amortization",
        "loan agreement", "mortgage agreement", "note"
    ],
    "verification_documents": [
        "verification of employment", "verification of deposit", "verification of rent",
        "vor", "vod", "voe", "verification letter", "employment letter",
        "deposit verification", "rental verification"
    ],
    "disclosures": [
        "disclosure", "tila", "respa", "good faith estimate", "hud-1",
        "closing disclosure", "loan estimate", "right to cancel",
        "truth in lending", "real estate settlement", "disclosure statement"
    ]
}

# Section-specific keywords for boundary detection
SECTION_KEYWORDS = {
    "closing_instructions": ["closing instructions", "settlement agent acknowledgment"],
    "mortgage_heloc": ["mortgage", "heloc", "deed of trust", "promissory note", "signature"],
    "supporting_documents": ["flood notice", "w-9", "ssa-89", "4506-c", "anti-coercion"]
}

def extract_and_reorganize_pages_safe(original_pdf_path, document_sections, lender_requirements):
    """
    Safely extract and reorganize pages from the original PDF with section boundary detection
    """
    print(f"🔍 DEBUG: Starting page extraction from: {original_pdf_path}")
    
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
            
            # Process each page
            for page_num in range(min(total_pages, 100)):  # Increased limit to 100 pages
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text() or ""
                    
                    # Assign page to document type with section boundary awareness
                    assigned_doc = assign_page_to_document_safe(page_text, document_sections, lender_requirements)
                    
                    # Add page to temp PDF
                    temp_pdf_writer.add_page(page)
                    
                    # Store assignment
                    page_assignments.append({
                        'page_number': page_num,
                        'assigned_document': assigned_doc,
                        'temp_page_index': len(temp_pdf_writer.pages) - 1
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
        print(f"🔍 DEBUG: Error in page extraction: {e}")
        traceback.print_exc()
        return []

def assign_page_to_document_safe(page_text, document_sections, lender_requirements):
    """
    Safely assign a page to a document type based on content analysis with section boundary detection
    """
    if not page_text:
        return "supporting_documents"
    
    page_text_lower = page_text.lower()
    
    # Detect section boundaries first
    for section, keywords in SECTION_KEYWORDS.items():
        if any(keyword in page_text_lower for keyword in keywords):
            return section

    # Score based on mortgage keywords
    scores = {}
    for doc_type, keywords in MORTGAGE_DOCUMENT_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in page_text_lower)
        scores[doc_type] = score
    
    # Find the document type with the highest score
    if scores and max(scores.values()) > 0:
        best_match = max(scores, key=scores.get)
        return best_match
    
    # Fallback to lender-specified order if available
    if lender_requirements.get('document_order'):
        for doc in lender_requirements['document_order']:
            if doc.lower().replace(" ", "_") in page_text_lower:
                return doc.lower().replace(" ", "_")
    
    # Fallback to document sections if provided
    if document_sections:
        for section in document_sections:
            section_title = section.get('title', '').lower()
            if any(word in page_text_lower for word in section_title.split()):
                return section_title.replace(' ', '_')
    
    return "supporting_documents"

def create_reorganized_pdf_safe(page_extraction_result, document_sections, lender_requirements, output_path):
    """
    Create the final reorganized PDF with structured sections and table of contents
    """
    print(f"🔍 DEBUG: Starting PDF creation at: {output_path}")
    
    try:
        # Create the final PDF
        pdf_writer = PyPDF2.PdfWriter()
        
        # Add cover page
        cover_page_buffer = create_cover_page_enhanced(document_sections, lender_requirements)
        if cover_page_buffer:
            cover_pdf = PyPDF2.PdfReader(cover_page_buffer)
            pdf_writer.add_page(cover_pdf.pages[0])
            print("🔍 DEBUG: Added cover page")
        
        # Add table of contents
        toc_buffer = create_table_of_contents(document_sections, lender_requirements)
        if toc_buffer:
            toc_pdf = PyPDF2.PdfReader(toc_buffer)
            pdf_writer.add_page(toc_pdf.pages[0])
            print("🔍 DEBUG: Added table of contents")
        
        # Check if we have page extraction results
        if not page_extraction_result or 'temp_pdf_path' not in page_extraction_result:
            print("🔍 DEBUG: No page extraction results, creating summary only")
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
                
                # Define reorganization order based on lender requirements
                reorganization_order = lender_requirements.get('document_order', [
                    "closing_instructions", "mortgage_heloc", "supporting_documents"
                ])
                
                # Group pages by document type
                document_groups = {}
                for assignment in page_assignments:
                    doc_type = assignment['assigned_document']
                    if doc_type not in document_groups:
                        document_groups[doc_type] = []
                    document_groups[doc_type].append(assignment)
                
                print(f"🔍 DEBUG: Document groups: {list(document_groups.keys())}")
                
                # Add pages in organized order
                for doc_type in reorganization_order:
                    if doc_type in document_groups:
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
                
                print(f"🔍 DEBUG: Total pages in final PDF: {len(pdf_writer.pages)}")
                
                # Write the final PDF
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                
                print(f"🔍 DEBUG: PDF written successfully")
                
                # Clean up temporary file
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
                    print(f"🔍 DEBUG: Cleaned up temp file: {temp_pdf_path}")
                
                return True
        else:
            print(f"🔍 DEBUG: Temp PDF not found: {temp_pdf_path}")
            return False
            
    except Exception as e:
        print(f"🔍 DEBUG: Error creating reorganized PDF: {e}")
        traceback.print_exc()
        return False

def create_cover_page_enhanced(document_sections, lender_requirements):
    """
    Create an enhanced cover page for the reorganized PDF
    """
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
        story.append(Paragraph("Reorganized According to Lender Requirements", subtitle_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Processing information
        story.append(Paragraph(f"<b>Processing Date:</b> {datetime.now().strftime('%B %d, %Y %I:%M %p EDT')}", styles['Normal']))
        story.append(Paragraph(f"<b>Total Document Sections:</b> {len(document_sections) if document_sections else 'N/A'}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Lender requirements summary
        if lender_requirements:
            story.append(Paragraph("<b>Lender Requirements Summary:</b>", styles['Heading3']))
            if lender_requirements.get('document_order'):
                story.append(Paragraph("Required document order has been applied to this package.", styles['Normal']))
            if lender_requirements.get('special_instructions'):
                story.append(Paragraph(f"Special Instructions: {lender_requirements['special_instructions'][:200]}...", styles['Normal']))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Footer
        story.append(Paragraph("This document has been professionally reorganized according to lender specifications using AI-powered document analysis.", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"Error creating cover page: {e}")
        return None

def create_table_of_contents(document_sections, lender_requirements):
    """
    Create a dynamic table of contents
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    toc_style = ParagraphStyle(
        'TOCTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=15,
        textColor=HexColor('#2c3e50'),
        alignment=1
    )
    item_style = ParagraphStyle(
        'TOCItem',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=10,
        textColor=HexColor('#34495e')
    )

    story.append(Paragraph("📑 Table of Contents", toc_style))
    story.append(Spacer(1, 0.5*inch))

    for section in document_sections:
        title = section.get('title', 'Untitled').replace('_', ' ').title()
        pages = section.get('pages', 'N/A')
        story.append(Paragraph(f"{title} - {pages} pages", item_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

def create_document_separator_enhanced(document_type, page_count):
    """
    Create an enhanced separator page for document sections
    """
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
        story.append(Spacer(1, 2*inch))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"Error creating separator page: {e}")
        return None

def classify_mortgage_document(text_content):
    """
    Enhanced mortgage document classification
    """
    text_lower = text_content.lower()
    
    # Check for specific document types
    if any(keyword in text_lower for keyword in ["1003", "loan application", "uniform residential"]):
        return "Loan Application (1003)"
    elif any(keyword in text_lower for keyword in ["pay stub", "w-2", "tax return", "income"]):
        return "Income Documentation"
    elif any(keyword in text_lower for keyword in ["bank statement", "asset", "savings", "checking"]):
        return "Asset Documentation"
    elif any(keyword in text_lower for keyword in ["credit report", "credit score", "fico"]):
        return "Credit Documentation"
    elif any(keyword in text_lower for keyword in ["appraisal", "property valuation", "home inspection"]):
        return "Property Documentation"
    elif any(keyword in text_lower for keyword in ["verification", "voe", "vod", "vor"]):
        return "Verification Documents"
    elif any(keyword in text_lower for keyword in ["disclosure", "tila", "respa", "closing"]):
        return "Disclosures"
    else:
        return "Supporting Documents"

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
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                requirements = json.loads(json_match.group())
            else:
                # Fallback: create structured response
                requirements = {
                    "document_order": [
                        "Loan Application (1003)",
                        "Income Documentation",
                        "Asset Verification",
                        "Credit Documentation",
                        "Property Appraisal",
                        "Supporting Documents"
                    ],
                    "special_instructions": "Standard mortgage package organization",
                    "priority_documents": ["Loan Application", "Income Verification"],
                    "submission_deadline": "Not specified"
                }
        except:
            # Fallback requirements
            requirements = {
                "document_order": [
                    "Loan Application (1003)",
                    "Income Documentation", 
                    "Asset Verification",
                    "Credit Documentation",
                    "Property Appraisal",
                    "Supporting Documents"
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
    """Analyze uploaded mortgage documents"""
    try:
        print("🔍 DEBUG: Starting document analysis")
        
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'})
        
        files = request.files.getlist('files')
        industry = request.form.get('industry', 'mortgage')
        
        print(f"🔍 DEBUG: Received {len(files)} files for {industry} industry")
        
        results = {
            'success': True,
            'sections': [],
            'total_files': len(files),
            'industry': industry
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
                        print(f"🔍 DEBUG: Preserving PDF file for reorganization: {temp_path}")
                        # Don't delete PDF files - they'll be needed for reorganization
                    
                    # Extract text and analyze
                    with open(temp_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text_content = ""
                        page_count = len(pdf_reader.pages)
                        
                        # Extract text from first few pages for analysis
                        for page_num in range(min(3, page_count)):
                            text_content += pdf_reader.pages[page_num].extract_text()
                    
                    # Classify document type
                    doc_type = classify_mortgage_document(text_content)
                    
                    results['sections'].append({
                        'title': doc_type,
                        'filename': filename,
                        'pages': page_count,
                        'type': 'pdf'
                    })
                    
                    print(f"🔍 DEBUG: Classified {filename} as {doc_type} ({page_count} pages)")
                
            except Exception as e:
                print(f"🔍 DEBUG: Error analyzing {filename}: {e}")
                results['sections'].append({
                    'title': 'Unknown Document',
                    'filename': filename,
                    'error': str(e)
                })
            
            finally:
                # Clean up temporary file (except for mortgage PDFs)
                if not (industry == 'mortgage' and filename.lower().endswith('.pdf')):
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        
        print(f"🔍 DEBUG: Analysis complete. Found {len(results['sections'])} sections")
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in document analysis: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reorganize_pdf', methods=['POST'])
def reorganize_pdf():
    """Reorganize PDF based on lender requirements"""
    try:
        print("🔍 DEBUG: reorganize_pdf endpoint called")
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
        output_filename = f"professional_mortgage_package_{timestamp}.pdf"
        output_path = f"/tmp/{output_filename}"
        
        print(f"🔍 DEBUG: Output path: {output_path}")
        
        if has_original_pdf:
            print("📄 Processing original PDF...")
            
            try:
                # Extract and reorganize pages
                print("🔍 DEBUG: Starting page extraction...")
                page_extraction_result = extract_and_reorganize_pages_safe(original_pdf_path, document_sections, lender_requirements)
                print(f"🔍 DEBUG: Page extraction result: {type(page_extraction_result)}")
                
                if page_extraction_result:
                    print(f"🔍 DEBUG: Total pages extracted: {page_extraction_result.get('total_pages', 0)}")
                
                # Create reorganized PDF
                print("🔍 DEBUG: Starting PDF creation...")
                success = create_reorganized_pdf_safe(page_extraction_result, document_sections, lender_requirements, output_path)
                
                if success and os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"🔍 DEBUG: PDF created successfully. Size: {file_size} bytes")
                    
                    # Verify page count
                    try:
                        with open(output_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            page_count = len(pdf_reader.pages)
                            print(f"🔍 DEBUG: Final PDF has {page_count} pages")
                    except Exception as e:
                        print(f"🔍 DEBUG: Error verifying page count: {e}")
                    
                    # Clean up preserved PDF file after reorganization
                    if has_original_pdf and os.path.exists(original_pdf_path):
                        os.remove(original_pdf_path)
                        print(f"🔍 DEBUG: Cleaned up preserved PDF: {original_pdf_path}")
                    
                    return send_file(output_path, as_attachment=True, download_name=output_filename)
                else:
                    print("🔍 DEBUG: PDF creation failed")
                    return jsonify({'error': 'Failed to create reorganized PDF'}), 500
                    
            except Exception as e:
                print(f"🔍 DEBUG: Error in PDF processing: {e}")
                traceback.print_exc()
                return jsonify({'error': f'PDF processing error: {str(e)}'}), 500
        else:
            print("📄 No original PDF - creating document summary")
            
            # Create summary-only PDF
            try:
                success = create_reorganized_pdf_safe(None, document_sections, lender_requirements, output_path)
                
                if success and os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"🔍 DEBUG: Summary PDF created. Size: {file_size} bytes")
                    return send_file(output_path, as_attachment=True, download_name=output_filename)
                else:
                    return jsonify({'error': 'Failed to create summary PDF'}), 500
                    
            except Exception as e:
                print(f"🔍 DEBUG: Error creating summary PDF: {e}")
                traceback.print_exc()
                return jsonify({'error': f'Summary PDF creation error: {str(e)}'}), 500
        
    except Exception as e:
        print(f"🔍 DEBUG: Unexpected error in reorganize_pdf: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
