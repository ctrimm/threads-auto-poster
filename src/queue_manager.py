import json
from datetime import datetime

class QueueManager:
  def __init__(self, queue_file):
    self.queue_file = queue_file
    self.queue = self.load_queue()

  def load_queue(self):
    try:
      with open(self.queue_file, 'r') as f:
        return json.load(f)
    except FileNotFoundError:
      return []

  def save_queue(self):
    with open(self.queue_file, 'w') as f:
      json.dump(self.queue, f, indent=2)

  def get_next_post(self):
    now = datetime.now().isoformat()
    for post in self.queue:
      if post['scheduledTime'] <= now:
        return post
    return None

  def remove_post(self, post_id):
    self.queue = [post for post in self.queue if post['id'] != post_id]
    self.save_queue()

  def sort_queue(self):
    self.queue.sort(key=lambda x: x['scheduledTime'])
    self.save_queue()

if __name__ == "__main__":
  manager = QueueManager('queue.json')
  manager.sort_queue()
