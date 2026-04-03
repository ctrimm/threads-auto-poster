import os
import sys

from dotenv import load_dotenv
import requests

# Resolve project root relative to this file so cron jobs work from any CWD
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from queue_manager import QueueManager

QUEUE_FILE = os.path.join(PROJECT_ROOT, 'queue.json')


def post_to_threads(post):
    access_token = os.environ['THREADS_ACCESS_TOKEN']
    user_id = os.environ['THREADS_USER_ID']

    # Step 1: Create a media container
    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"

    payload = {
        "access_token": access_token,
        "media_type": post['mediaType'],
        "text": post['text'],
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
        "creation_id": creation_id,
    })

    if publish_response.status_code == 200:
        print(f"Published: {post['text'][:60]}")
        return True
    else:
        print(f"Failed to publish to Threads: {publish_response.text}")
        return False


def main():
    queue_manager = QueueManager(QUEUE_FILE)
    published = 0

    while True:
        next_post = queue_manager.get_next_post()
        if not next_post:
            break
        success = post_to_threads(next_post)
        if success:
            queue_manager.remove_post(next_post['id'])
            published += 1
        else:
            # Stop on failure to avoid hammering the API with a broken post
            break

    print(f"Published {published} post(s) this run.")


if __name__ == "__main__":
    main()
