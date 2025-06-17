# Complete Mortgage Package Analyzer

A professional-grade mortgage document analyzer with advanced OCR capabilities, designed for Render.com deployment.

## 🚀 Features

### 📄 **Maximum OCR Processing**
- **Multi-Engine Text Extraction**: Uses both pdfplumber and pytesseract for optimal accuracy
- **Advanced Image Preprocessing**: Multiple enhancement techniques for better OCR results
- **Intelligent Fallback**: Automatically switches to OCR for image-based PDFs
- **High-Resolution Processing**: 200 DPI conversion for maximum text clarity

### 🎯 **Comprehensive Section Analysis**
Identifies 16 different mortgage document types:
1. **Mortgage** (Priority 10)
2. **Promissory Note** (Priority 10)
3. **Lenders Closing Instructions Guaranty** (Priority 9)
4. **Settlement Statement** (Priority 9)
5. **Statement of Anti Coercion Florida** (Priority 8)
6. **Correction Agreement and Limited Power of Attorney** (Priority 8)
7. **All Purpose Acknowledgment** (Priority 8)
8. **Flood Hazard Determination** (Priority 7)
9. **Automatic Payments Authorization** (Priority 7)
10. **Tax Record Information** (Priority 7)
11. **Title Policy** (Priority 6)
12. **Insurance Policy** (Priority 6)
13. **Deed** (Priority 6)
14. **UCC Filing** (Priority 5)
15. **Signature Page** (Priority 5)
16. **Affidavit** (Priority 5)

### 💡 **Smart Analysis**
- **Confidence Scoring**: Each section identified with accuracy percentage
- **Context Validation**: Analyzes surrounding text for better accuracy
- **Priority-Based Ranking**: Important sections identified first
- **Page Number Tracking**: Precise location of each section

### 🎨 **Professional Interface**
- **Modern Design**: Clean, responsive interface
- **Real-Time Progress**: Session-based progress tracking with live updates
- **Drag & Drop Upload**: Intuitive file upload with visual feedback
- **Results Dashboard**: Comprehensive analysis results with statistics
- **Table of Contents**: Generate organized TOC from identified sections

## 📋 **Quick Deploy to Render**

### **Prerequisites**
- GitHub account
- Render.com account (free tier available)

### **Deployment Steps**

1. **Create GitHub Repository**
   ```bash
   # Create new repository on GitHub
   # Upload all files from this package
   ```

2. **Connect to Render**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository with these files

3. **Configure Service**
   - **Name**: `mortgage-analyzer-complete`
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh && pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
   - **Plan**: Free (or paid for better performance)

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete (5-10 minutes)
   - Your app will be available at `https://your-service-name.onrender.com`

### **Files Included**
- `app.py` - Complete Flask application with maximum OCR features
- `requirements.txt` - Python dependencies (OCR-optimized)
- `build.sh` - System dependencies installer for Render
- `render.yaml` - Render service configuration
- `README.md` - This documentation

## 🔧 **Technical Specifications**

### **System Requirements**
- **Python**: 3.8+
- **System Dependencies**: tesseract-ocr, poppler-utils
- **Memory**: Minimum 512MB (1GB+ recommended for large files)
- **Storage**: Temporary space for PDF processing

### **Performance**
- **File Size Limit**: 100MB
- **Processing Timeout**: 5 minutes
- **Supported Formats**: PDF only
- **OCR Languages**: English (expandable)

### **API Endpoints**
- `GET /` - Main application interface
- `POST /analyze` - Document analysis endpoint
- `GET /progress` - Real-time progress tracking
- `GET /health` - Health check and status

## 🎯 **Usage**

1. **Upload PDF**: Drag and drop or click to browse
2. **Analyze**: Click "Analyze Document" button
3. **Monitor Progress**: Watch real-time progress updates
4. **Review Results**: Examine identified sections with confidence scores
5. **Generate TOC**: Create table of contents from results
6. **Repeat**: Analyze additional documents as needed

## 🔍 **Analysis Process**

1. **File Validation**: Checks format and size limits
2. **Text Extraction**: Attempts pdfplumber first, falls back to OCR
3. **Image Processing**: Multiple preprocessing techniques for OCR
4. **Pattern Matching**: Searches for mortgage section patterns
5. **Confidence Scoring**: Calculates accuracy based on context
6. **Results Compilation**: Organizes findings by priority and confidence

## 🛠️ **Troubleshooting**

### **Common Issues**

**Build Fails on Render**
- Ensure `build.sh` is executable (`chmod +x build.sh`)
- Check that all files are uploaded to GitHub
- Verify render.yaml configuration

**OCR Not Working**
- Confirm tesseract installation in build logs
- Check PDF is not password protected
- Ensure sufficient memory allocation

**Slow Processing**
- Large files take longer to process
- OCR processing is CPU intensive
- Consider upgrading to paid Render plan

**No Sections Found**
- Document may not contain standard mortgage sections
- Try different document or check for scanned/image-based content
- Review confidence threshold settings

## 📊 **Performance Optimization**

### **For Better Performance**
- **Upgrade Plan**: Use Render paid plans for more resources
- **Optimize Images**: Reduce PDF file size before upload
- **Batch Processing**: Process multiple documents separately

### **Memory Management**
- Application uses in-memory processing to avoid file system issues
- Automatic cleanup after processing
- Session-based progress tracking

## 🔒 **Security & Privacy**

- **No Data Storage**: Documents are processed in memory only
- **Session Isolation**: Each analysis uses unique session ID
- **Secure Upload**: Files validated before processing
- **No Logging**: Document content is not logged or stored

## 📈 **Monitoring**

- **Health Endpoint**: `/health` for status monitoring
- **Progress Tracking**: Real-time updates during processing
- **Error Handling**: Comprehensive error reporting
- **Performance Metrics**: Processing time and accuracy statistics

## 🎉 **Success Indicators**

After successful deployment, you should see:
- ✅ Clean, professional interface loads
- ✅ File upload works with drag & drop
- ✅ Progress bar shows during processing
- ✅ Results display with confidence scores
- ✅ Table of contents generation works
- ✅ No JavaScript or file system errors

## 📞 **Support**

This application is optimized for Render.com deployment and includes all necessary configurations for reliable operation. The OCR processing is designed to handle both text-based and image-based PDFs with maximum accuracy.

For best results, ensure your Render service has adequate resources and the build process completes successfully with all system dependencies installed.

---

**Built with Flask, pytesseract, pdfplumber, and professional-grade OCR processing for reliable mortgage document analysis.**

