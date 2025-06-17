#!/usr/bin/env bash

# Render build script for Complete Mortgage Analyzer
# Installs system dependencies required for OCR processing

echo "Installing system dependencies for OCR processing..."

# Update package list
apt-get update

# Install tesseract OCR engine and language packs
apt-get install -y tesseract-ocr tesseract-ocr-eng

# Install poppler utilities for PDF to image conversion
apt-get install -y poppler-utils

# Install additional image processing libraries
apt-get install -y libjpeg-dev libpng-dev libtiff-dev

# Verify installations
echo "Verifying installations..."
tesseract --version
pdftoppm -h | head -1

echo "System dependencies installed successfully!"
echo "Ready for Python package installation..."

