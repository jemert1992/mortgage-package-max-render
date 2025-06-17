from flask import Flask, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mortgage Analyzer - Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Mortgage Package Analyzer - Test Version</h1>
        <div class="upload-area">
            <h3>Upload Test Successful!</h3>
            <p>This is a minimal test version to verify Render deployment works.</p>
            <p>Once this loads successfully, we can add the full OCR features.</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    return {"status": "healthy", "message": "Minimal test version running"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

