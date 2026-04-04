import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import post_to_threads as poster
from queue_manager import QueueManager


def make_post(post_id, offset_minutes=-5):
    scheduled = datetime.now() + timedelta(minutes=offset_minutes)
    return {
        'id': post_id,
        'text': f'Post {post_id}',
        'scheduledTime': scheduled.isoformat(),
        'mediaType': 'TEXT',
        'mediaUrl': '',
    }


def _api_resp(json_body, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_body
    resp.text = str(json_body)
    return resp


ENV = {
    'THREADS_ACCESS_TOKEN': 'fake_token',
    'THREADS_USER_ID': '12345',
}


class TestPostToThreads(unittest.TestCase):

    # --- post_to_threads() ---

    @patch('post_to_threads.requests.post')
    def test_successful_post_returns_true(self, mock_post):
        mock_post.side_effect = [
            _api_resp({'id': 'container_1'}),
            _api_resp({'id': 'thread_1'}),
        ]
        with patch.dict(os.environ, ENV):
            result = poster.post_to_threads(make_post(1))
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 2)

    @patch('post_to_threads.requests.post')
    def test_container_creation_failure_returns_false(self, mock_post):
        mock_post.return_value = _api_resp({}, status=500)
        with patch.dict(os.environ, ENV):
            result = poster.post_to_threads(make_post(1))
        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 1)

    @patch('post_to_threads.requests.post')
    def test_publish_failure_returns_false(self, mock_post):
        mock_post.side_effect = [
            _api_resp({'id': 'container_1'}),
            _api_resp({}, status=500),
        ]
        with patch.dict(os.environ, ENV):
            result = poster.post_to_threads(make_post(1))
        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 2)

    # --- main() loop ---

    @patch('post_to_threads.requests.post')
    def test_main_publishes_all_due_posts(self, mock_post):
        mock_post.side_effect = [
            _api_resp({'id': 'c1'}), _api_resp({'id': 't1'}),
            _api_resp({'id': 'c2'}), _api_resp({'id': 't2'}),
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([make_post(1), make_post(2)], f)
            queue_path = f.name

        try:
            with patch.dict(os.environ, ENV):
                with patch('post_to_threads.QUEUE_FILE', queue_path):
                    poster.main()

            self.assertEqual(QueueManager(queue_path).queue, [])
        finally:
            os.unlink(queue_path)

    @patch('post_to_threads.requests.post')
    def test_main_stops_on_first_failure(self, mock_post):
        mock_post.return_value = _api_resp({}, status=500)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([make_post(1), make_post(2)], f)
            queue_path = f.name

        try:
            with patch.dict(os.environ, ENV):
                with patch('post_to_threads.QUEUE_FILE', queue_path):
                    poster.main()

            self.assertEqual(len(QueueManager(queue_path).queue), 2)
        finally:
            os.unlink(queue_path)

    @patch('post_to_threads.requests.post')
    def test_main_no_due_posts_does_nothing(self, mock_post):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([make_post(1, offset_minutes=+60)], f)
            queue_path = f.name

        try:
            with patch.dict(os.environ, ENV):
                with patch('post_to_threads.QUEUE_FILE', queue_path):
                    poster.main()

            mock_post.assert_not_called()
        finally:
            os.unlink(queue_path)


if __name__ == '__main__':
    unittest.main()
