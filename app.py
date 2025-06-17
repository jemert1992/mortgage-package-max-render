from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>File Upload Test</title>
    <style>
        body { font-family: Arial; padding: 20px; }
        .upload-area { 
            border: 2px dashed #ccc; 
            padding: 40px; 
            text-align: center; 
            margin: 20px 0;
            cursor: pointer;
        }
        .upload-area:hover { border-color: #007bff; }
        .btn { 
            background: #007bff; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            cursor: pointer; 
            margin: 10px;
        }
        .btn:disabled { background: #ccc; }
        #result { margin: 20px 0; padding: 10px; background: #f8f9fa; }
    </style>
</head>
<body>
    <h1>Simple File Upload Test</h1>
    
    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
        <p>Click here to select a PDF file</p>
        <p id="fileName">No file selected</p>
    </div>
    
    <input type="file" id="fileInput" accept=".pdf" style="display: none;">
    <button class="btn" id="uploadBtn" onclick="uploadFile()" disabled>Upload File</button>
    
    <div id="result"></div>

    <script>
        let selectedFile = null;
        
        document.getElementById('fileInput').addEventListener('change', function(e) {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                document.getElementById('fileName').textContent = selectedFile.name;
                document.getElementById('uploadBtn').disabled = false;
            }
        });
        
        function uploadFile() {
            if (!selectedFile) {
                alert('Please select a file first');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            document.getElementById('result').innerHTML = 'Uploading...';
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('result').innerHTML = 
                    '<h3>Upload Result:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
            })
            .catch(error => {
                document.getElementById('result').innerHTML = 
                    '<h3>Error:</h3><p>' + error.message + '</p>';
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'})
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'size': len(file.read()),
            'message': 'File uploaded successfully!'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

