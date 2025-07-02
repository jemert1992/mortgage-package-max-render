#!/usr/bin/env python3
"""
🏠 Mortgage Package Reorganizer - Professional Edition
A sleek, professional tool for reorganizing mortgage documents based on lender requirements
"""

import os
import json
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
