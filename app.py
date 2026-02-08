import os
from uuid import uuid4
from flask import Flask, request, render_template, send_from_directory, url_for, jsonify
from PyPDF2 import PdfMerger
from werkzeug.utils import secure_filename

# Initialize Flask App
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=BASE_DIR,
    static_folder=os.path.join(BASE_DIR, "static"),
)

# Configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
MERGED_FOLDER = os.path.join(BASE_DIR, "merged")
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MERGED_FOLDER'] = MERGED_FOLDER
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MERGED_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_files(paths):
    for file_path in paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/merge', methods=['POST'])
def merge_files():
    if 'files[]' not in request.files:
        return jsonify({'success': False, 'error': 'No file part in the request.'}), 400

    files = request.files.getlist('files[]')

    if len(files) < 2:
        return jsonify({'success': False, 'error': 'Select at least two PDFs.'}), 400

    uploaded_files = []

    try:
        # Save uploaded files
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = f"{uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(filepath)
                uploaded_files.append(filepath)
            else:
                cleanup_files(uploaded_files)
                return jsonify({'success': False, 'error': f'Invalid file: {file.filename}'}), 400

        if len(uploaded_files) < 2:
            cleanup_files(uploaded_files)
            return jsonify({'success': False, 'error': 'Upload at least two valid PDFs.'}), 400

        # Merge PDFs
        merger = PdfMerger()
        for pdf_path in uploaded_files:
            merger.append(pdf_path)

        output_filename = f"merged_{uuid4().hex}.pdf"
        output_path = os.path.join(app.config['MERGED_FOLDER'], output_filename)
        merger.write(output_path)
        merger.close()  # CLOSE FIRST

        # Then cleanup
        cleanup_files(uploaded_files)

        download_url = url_for('download_file', filename=output_filename, _external=True)
        return jsonify({'success': True, 'download_url': download_url})

    except Exception as e:
        cleanup_files(uploaded_files)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['MERGED_FOLDER'], filename, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

    
