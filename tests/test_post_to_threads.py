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


def mock_success_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.side_effect = [
        {'id': 'container_123'},   # create container
        {'id': 'thread_456'},      # publish
    ]
    return resp


def mock_fail_response():
    resp = MagicMock()
    resp.status_code = 500
    resp.text = 'Internal Server Error'
    return resp


class TestPostToThreads(unittest.TestCase):
    def _env(self):
        return {
            'THREADS_ACCESS_TOKEN': 'fake_token',
            'THREADS_USER_ID': '12345',
        }

    # --- post_to_threads() ---

    @patch('post_to_threads.requests.post')
    def test_successful_post_returns_true(self, mock_post):
        mock_post.return_value = mock_success_response()
        with patch.dict(os.environ, self._env()):
            result = poster.post_to_threads(make_post(1))
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 2)  # create + publish

    @patch('post_to_threads.requests.post')
    def test_container_creation_failure_returns_false(self, mock_post):
        mock_post.return_value = mock_fail_response()
        with patch.dict(os.environ, self._env()):
            result = poster.post_to_threads(make_post(1))
        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 1)  # only create, no publish

    @patch('post_to_threads.requests.post')
    def test_publish_failure_returns_false(self, mock_post):
        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {'id': 'container_123'}

        publish_resp = mock_fail_response()
        mock_post.side_effect = [create_resp, publish_resp]

        with patch.dict(os.environ, self._env()):
            result = poster.post_to_threads(make_post(1))
        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 2)

    # --- main() loop ---

    @patch('post_to_threads.requests.post')
    def test_main_publishes_all_due_posts(self, mock_post):
        """All overdue posts are published in a single run."""
        # Two successful post cycles (create + publish each)
        mock_post.side_effect = [
            _make_api_resp({'id': 'c1'}),
            _make_api_resp({'id': 't1'}),
            _make_api_resp({'id': 'c2'}),
            _make_api_resp({'id': 't2'}),
        ]

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            import json
            json.dump([make_post(1), make_post(2)], f)
            queue_path = f.name

        try:
            with patch.dict(os.environ, self._env()):
                with patch('post_to_threads.QueueManager') as MockQM:
                    qm = QueueManager(queue_path)
                    MockQM.return_value = qm
                    poster.main()

            reloaded = QueueManager(queue_path)
            self.assertEqual(reloaded.queue, [], "Queue should be empty after all posts published")
        finally:
            os.unlink(queue_path)

    @patch('post_to_threads.requests.post')
    def test_main_stops_on_first_failure(self, mock_post):
        """If a post fails, remaining due posts are left in the queue."""
        mock_post.return_value = mock_fail_response()

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            import json
            json.dump([make_post(1), make_post(2)], f)
            queue_path = f.name

        try:
            with patch.dict(os.environ, self._env()):
                with patch('post_to_threads.QueueManager') as MockQM:
                    qm = QueueManager(queue_path)
                    MockQM.return_value = qm
                    poster.main()

            reloaded = QueueManager(queue_path)
            self.assertEqual(len(reloaded.queue), 2, "Both posts should remain after failure")
        finally:
            os.unlink(queue_path)

    @patch('post_to_threads.requests.post')
    def test_main_no_due_posts_does_nothing(self, mock_post):
        """No API calls made when queue has no due posts."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            import json
            future = make_post(1, offset_minutes=+60)
            json.dump([future], f)
            queue_path = f.name

        try:
            with patch.dict(os.environ, self._env()):
                with patch('post_to_threads.QueueManager') as MockQM:
                    qm = QueueManager(queue_path)
                    MockQM.return_value = qm
                    poster.main()

            mock_post.assert_not_called()
        finally:
            os.unlink(queue_path)


def _make_api_resp(json_body):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_body
    return resp


if __name__ == '__main__':
    unittest.main()
