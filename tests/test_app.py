import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point app at a temp queue file before importing
_tmp_queue = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
_tmp_queue.write('[]')
_tmp_queue.close()

import app as flask_app
flask_app.QUEUE_FILE = _tmp_queue.name


class TestQueueAPI(unittest.TestCase):
    def setUp(self):
        flask_app.app.config['TESTING'] = True
        self.client = flask_app.app.test_client()
        # Reset queue before each test
        with open(_tmp_queue.name, 'w') as f:
            f.write('[]')

    @classmethod
    def tearDownClass(cls):
        os.unlink(_tmp_queue.name)

    def _post(self, payload):
        return self.client.post(
            '/queue',
            data=json.dumps(payload),
            content_type='application/json',
        )

    # --- Happy path ---

    def test_add_valid_text_post(self):
        res = self._post({'text': 'Hello Threads!', 'scheduledTime': '2099-01-01T10:00'})
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('id', data)

    def test_get_queue_returns_list(self):
        res = self.client.get('/queue')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.get_json(), list)

    def test_delete_post(self):
        add = self._post({'text': 'to delete', 'scheduledTime': '2099-01-01T10:00'})
        post_id = add.get_json()['id']
        res = self.client.delete(f'/queue/{post_id}')
        self.assertEqual(res.status_code, 200)

    # --- Input validation ---

    def test_missing_text_rejected(self):
        res = self._post({'scheduledTime': '2099-01-01T10:00'})
        self.assertEqual(res.status_code, 400)

    def test_empty_text_rejected(self):
        res = self._post({'text': '   ', 'scheduledTime': '2099-01-01T10:00'})
        self.assertEqual(res.status_code, 400)

    def test_text_too_long_rejected(self):
        res = self._post({'text': 'x' * 501, 'scheduledTime': '2099-01-01T10:00'})
        self.assertEqual(res.status_code, 400)

    def test_missing_scheduled_time_rejected(self):
        res = self._post({'text': 'Hello'})
        self.assertEqual(res.status_code, 400)

    def test_invalid_scheduled_time_format_rejected(self):
        res = self._post({'text': 'Hello', 'scheduledTime': 'not-a-date'})
        self.assertEqual(res.status_code, 400)

    def test_invalid_media_type_rejected(self):
        res = self._post({'text': 'Hello', 'scheduledTime': '2099-01-01T10:00', 'mediaType': 'GIF'})
        self.assertEqual(res.status_code, 400)

    def test_non_http_media_url_rejected(self):
        res = self._post({
            'text': 'Hello',
            'scheduledTime': '2099-01-01T10:00',
            'mediaUrl': 'javascript:alert(1)',
        })
        self.assertEqual(res.status_code, 400)

    def test_valid_media_types_accepted(self):
        for mt in ('TEXT', 'IMAGE', 'VIDEO'):
            res = self._post({
                'text': 'Hello',
                'scheduledTime': '2099-01-01T10:00',
                'mediaType': mt,
                'mediaUrl': 'https://example.com/file.jpg' if mt != 'TEXT' else '',
            })
            self.assertEqual(res.status_code, 201, f"Expected 201 for mediaType={mt}")

    def test_no_json_body_rejected(self):
        res = self.client.post('/queue', data='not json', content_type='text/plain')
        self.assertEqual(res.status_code, 400)

    # --- Config endpoint ---

    def test_config_returns_s3_flag(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AWS_S3_BUCKET', None)
            res = self.client.get('/config')
            self.assertFalse(res.get_json()['s3_enabled'])

    def test_config_s3_enabled_when_bucket_set(self):
        with patch.dict(os.environ, {'AWS_S3_BUCKET': 'my-bucket'}):
            res = self.client.get('/config')
            self.assertTrue(res.get_json()['s3_enabled'])

    # --- Upload endpoint (no S3 configured) ---

    def test_upload_without_s3_config_returns_400(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AWS_S3_BUCKET', None)
            res = self.client.post('/upload', data={'file': (b'data', 'photo.jpg')})
            self.assertEqual(res.status_code, 400)


if __name__ == '__main__':
    unittest.main()
