import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from queue_manager import QueueManager


def make_post(post_id, text, offset_minutes):
    """Create a post dict scheduled offset_minutes from now (negative = past)."""
    scheduled = datetime.now() + timedelta(minutes=offset_minutes)
    return {
        'id': post_id,
        'text': text,
        'scheduledTime': scheduled.isoformat(),
        'mediaType': 'TEXT',
        'mediaUrl': '',
    }


class TestQueueManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        self.tmp.write('[]')
        self.tmp.close()
        self.qm = QueueManager(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    # --- load / save ---

    def test_load_empty_queue(self):
        self.assertEqual(self.qm.queue, [])

    def test_load_missing_file_returns_empty(self):
        qm = QueueManager('/tmp/does_not_exist_xyz.json')
        self.assertEqual(qm.queue, [])

    def test_save_and_reload(self):
        post = make_post(1, 'Hello', -5)
        self.qm.queue.append(post)
        self.qm.save_queue()

        reloaded = QueueManager(self.tmp.name)
        self.assertEqual(len(reloaded.queue), 1)
        self.assertEqual(reloaded.queue[0]['text'], 'Hello')

    # --- get_next_post ---

    def test_get_next_post_returns_overdue(self):
        self.qm.queue = [make_post(1, 'due', -1)]
        self.assertIsNotNone(self.qm.get_next_post())

    def test_get_next_post_ignores_future(self):
        self.qm.queue = [make_post(1, 'future', +60)]
        self.assertIsNone(self.qm.get_next_post())

    def test_get_next_post_returns_none_when_empty(self):
        self.assertIsNone(self.qm.get_next_post())

    def test_get_next_post_picks_earliest_overdue(self):
        self.qm.queue = [
            make_post(1, 'older', -10),
            make_post(2, 'newer', -2),
        ]
        # get_next_post iterates in order; first overdue post in list is returned
        result = self.qm.get_next_post()
        self.assertEqual(result['id'], 1)

    # --- remove_post ---

    def test_remove_post_removes_correct_item(self):
        self.qm.queue = [make_post(1, 'a', -5), make_post(2, 'b', -5)]
        self.qm.remove_post(1)
        self.assertEqual(len(self.qm.queue), 1)
        self.assertEqual(self.qm.queue[0]['id'], 2)

    def test_remove_post_nonexistent_id_is_noop(self):
        self.qm.queue = [make_post(1, 'a', -5)]
        self.qm.remove_post(999)
        self.assertEqual(len(self.qm.queue), 1)

    # --- sort_queue ---

    def test_sort_queue_orders_by_scheduled_time(self):
        self.qm.queue = [
            make_post(1, 'second', -1),
            make_post(2, 'first', -10),
        ]
        self.qm.sort_queue()
        self.assertEqual(self.qm.queue[0]['id'], 2)
        self.assertEqual(self.qm.queue[1]['id'], 1)

    # --- resilience ---

    def test_load_malformed_json_returns_empty(self):
        with open(self.tmp.name, 'w') as f:
            f.write('this is not json {{{')
        qm = QueueManager(self.tmp.name)
        self.assertEqual(qm.queue, [])

    def test_load_non_list_json_returns_empty(self):
        with open(self.tmp.name, 'w') as f:
            f.write('{"key": "value"}')
        qm = QueueManager(self.tmp.name)
        self.assertEqual(qm.queue, [])


if __name__ == '__main__':
    unittest.main()
