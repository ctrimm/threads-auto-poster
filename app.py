import os
import re
import sys
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

load_dotenv()

# Resolve paths relative to this file so the app works from any CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, 'queue.json')

sys.path.insert(0, os.path.join(BASE_DIR, 'src'))
from queue_manager import QueueManager

app = Flask(__name__, static_folder='docs', static_url_path='')

# Reject request bodies larger than 50 MB (guards the upload endpoint)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_MEDIA_TYPES = {'TEXT', 'IMAGE', 'VIDEO'}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'video/mp4', 'video/quicktime', 'video/webm',
}
MAX_TEXT_LENGTH = 500
_ISO_DATETIME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$')


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return send_from_directory('docs', 'index.html')


# ---------------------------------------------------------------------------
# Queue API
# ---------------------------------------------------------------------------

@app.route('/queue', methods=['GET'])
def get_queue():
    qm = QueueManager(QUEUE_FILE)
    return jsonify(qm.queue)


@app.route('/queue', methods=['POST'])
def add_to_queue():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    text = data.get('text', '')
    scheduled_time = data.get('scheduledTime', '')
    media_type = data.get('mediaType', 'TEXT')
    media_url = data.get('mediaUrl', '')

    # --- Validate ---
    if not isinstance(text, str) or not text.strip():
        return jsonify({'error': 'text is required'}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({'error': f'text must be {MAX_TEXT_LENGTH} characters or fewer'}), 400

    if not isinstance(scheduled_time, str) or not _ISO_DATETIME_RE.match(scheduled_time):
        return jsonify({'error': 'scheduledTime must be a valid datetime (YYYY-MM-DDTHH:MM)'}), 400

    if media_type not in ALLOWED_MEDIA_TYPES:
        return jsonify({'error': f'mediaType must be one of {sorted(ALLOWED_MEDIA_TYPES)}'}), 400

    if media_url and not isinstance(media_url, str):
        return jsonify({'error': 'mediaUrl must be a string'}), 400
    if media_url and not media_url.startswith(('http://', 'https://')):
        return jsonify({'error': 'mediaUrl must be an http/https URL'}), 400

    qm = QueueManager(QUEUE_FILE)
    post = {
        'id': int(time.time() * 1000),
        'text': text.strip(),
        'scheduledTime': scheduled_time,
        'mediaType': media_type,
        'mediaUrl': media_url,
    }
    qm.queue.append(post)
    qm.sort_queue()
    qm.save_queue()
    return jsonify({'ok': True, 'id': post['id']}), 201


@app.route('/queue/<int:post_id>', methods=['DELETE'])
def delete_from_queue(post_id):
    qm = QueueManager(QUEUE_FILE)
    qm.remove_post(post_id)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Config (tells the UI whether optional features are available)
# ---------------------------------------------------------------------------

@app.route('/config')
def get_config():
    return jsonify({
        's3_enabled': bool(os.environ.get('AWS_S3_BUCKET')),
    })


# ---------------------------------------------------------------------------
# Media upload (only active when S3 env vars are present)
# ---------------------------------------------------------------------------

@app.route('/upload', methods=['POST'])
def upload_media():
    bucket = os.environ.get('AWS_S3_BUCKET')
    region = os.environ.get('AWS_REGION', 'us-east-1')

    if not bucket:
        return jsonify({'error': 'S3 not configured — set AWS_S3_BUCKET in .env'}), 400

    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'error': 'No file provided'}), 400

    # Validate MIME type against our allowlist (don't trust the browser value)
    if file.content_type not in ALLOWED_MIME_TYPES:
        return jsonify({'error': 'File type not allowed. Use JPEG, PNG, GIF, WebP, MP4, MOV, or WebM.'}), 400

    # Sanitise filename to prevent path traversal
    safe_name = secure_filename(file.filename)
    if not safe_name:
        return jsonify({'error': 'Invalid filename'}), 400

    try:
        import boto3
    except ImportError:
        return jsonify({'error': 'boto3 not installed — run: pip install boto3'}), 500

    key = f"threads-media/{int(time.time() * 1000)}-{safe_name}"
    s3 = boto3.client('s3', region_name=region)
    s3.upload_fileobj(
        file, bucket, key,
        ExtraArgs={'ContentType': file.content_type},
    )
    url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
    return jsonify({'url': url})


# ---------------------------------------------------------------------------

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='127.0.0.1', port=5000, debug=debug)
