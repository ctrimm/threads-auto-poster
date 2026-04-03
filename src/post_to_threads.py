import os
import requests
import json
from queue_manager import QueueManager

def post_to_threads(post):
  access_token = os.environ['THREADS_ACCESS_TOKEN']
  user_id = os.environ['THREADS_USER_ID']

  # Step 1: Create a media container
  create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"

  payload = {
    "access_token": access_token,
    "media_type": post['mediaType'],
    "text": post['text']
  }

  if post['mediaType'] in ['IMAGE', 'VIDEO']:
    payload[f"{post['mediaType'].lower()}_url"] = post['mediaUrl']

  create_response = requests.post(create_url, data=payload)

  if create_response.status_code != 200:
    print(f"Failed to create Threads container: {create_response.text}")
    return False

  creation_id = create_response.json().get('id')
  if not creation_id:
    print(f"No creation_id in response: {create_response.text}")
    return False

  # Step 2: Publish the container
  publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"

  publish_response = requests.post(publish_url, data={
    "access_token": access_token,
    "creation_id": creation_id
  })

  if publish_response.status_code == 200:
    print("Successfully posted to Threads")
    return True
  else:
    print(f"Failed to publish to Threads: {publish_response.text}")
    return False

def main():
  queue_manager = QueueManager('queue.json')
  next_post = queue_manager.get_next_post()

  if next_post:
    success = post_to_threads(next_post)
    if success:
      queue_manager.remove_post(next_post['id'])
      queue_manager.save_queue()

if __name__ == "__main__":
  main()
