# Threads Auto-Poster

Schedule and automatically post content to Threads. Runs entirely on your local machine — no GitHub Actions, no tokens in the browser.

## How it works

- A lightweight Flask web app (served at `localhost:5000`) lets you write posts and pick a scheduled time.
- Posts are saved to `queue.json`.
- A cron job runs `src/post_to_threads.py` on a schedule, checks the queue, and publishes anything that's due.
- Media uploads are text-only by default. S3 support is available optionally (see below).

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/ctrimm/threads-auto-poster.git
cd threads-auto-poster
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your Threads API credentials:

```
THREADS_ACCESS_TOKEN=your_threads_access_token_here
THREADS_USER_ID=your_threads_user_id_here
```

> Get these from the [Meta Developer Portal](https://developers.facebook.com/apps/) after creating a Threads app.

### 4. Start the web UI

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### 5. Set up the cron job

Run `crontab -e` and add a line to post every hour:

```
0 * * * * cd /path/to/threads-auto-poster && python src/post_to_threads.py >> /tmp/threads-poster.log 2>&1
```

Replace `/path/to/threads-auto-poster` with the absolute path to where you cloned the repo.

The script loads `.env` automatically, so no extra env setup is needed in the crontab.

## Optional: S3 media uploads

By default the app is text-only. To enable image/video uploads via an S3 bucket:

1. Uncomment `boto3>=1.26.0` in `requirements.txt` and run `pip install boto3`.

2. Add the following to your `.env`:

   ```
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   AWS_REGION=us-east-1
   AWS_S3_BUCKET=your-bucket-name
   ```

3. The IAM user needs `s3:PutObject` permission on the bucket. Make sure the bucket (or a CloudFront distribution in front of it) serves files publicly so the Threads API can fetch them.

4. Restart `python app.py` — a file upload button will appear in the UI automatically.

## Optional: Claude Code session hook

If you use Claude Code, a `SessionStart` hook is included that reads the queue and prompts Claude to ask whether you'd like to add a new post at the start of every session.

```bash
# Make the hook executable
chmod +x .claude/hooks/session-start.sh

# Verify it works (requires python3)
CLAUDE_PROJECT_DIR=$(pwd) .claude/hooks/session-start.sh
```

## Running tests

```bash
python -m pytest tests/ -v
```

## Files

```
app.py                        Local Flask server
src/
  post_to_threads.py          Posts due items from the queue to Threads
  queue_manager.py            Reads/writes queue.json
tests/
  test_queue_manager.py
  test_post_to_threads.py
docs/
  index.html                  Web UI
  script.js
  style.css
.claude/
  hooks/session-start.sh      Claude Code session hook
  settings.json
.env.example                  Credentials template
queue.json                    The post queue (auto-created)
requirements.txt
```

## License

MIT
