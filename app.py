import os
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

# Resolve paths relative to this file so the app works from any CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, 'queue.json')

import sys
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))
from queue_manager import QueueManager

app = Flask(__name__, static_folder='docs', static_url_path='')


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
    data = request.get_json()
    if not data or not data.get('text') or not data.get('scheduledTime'):
        return jsonify({'error': 'text and scheduledTime are required'}), 400

    qm = QueueManager(QUEUE_FILE)
    post = {
        'id': int(time.time() * 1000),
        'text': data['text'],
        'scheduledTime': data['scheduledTime'],
        'mediaType': data.get('mediaType', 'TEXT'),
        'mediaUrl': data.get('mediaUrl', ''),
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

    try:
        import boto3
    except ImportError:
        return jsonify({'error': 'boto3 not installed — run: pip install boto3'}), 500

    key = f"threads-media/{int(time.time() * 1000)}-{file.filename}"
    s3 = boto3.client('s3', region_name=region)
    s3.upload_fileobj(
        file, bucket, key,
        ExtraArgs={'ContentType': file.content_type},
    )
    url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
    return jsonify({'url': url})


# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=5000)
