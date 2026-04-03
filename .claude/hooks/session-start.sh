#!/bin/bash
set -euo pipefail

QUEUE_FILE="${CLAUDE_PROJECT_DIR:-$(pwd)}/queue.json"

# Parse queue count and next scheduled post using python
QUEUE_INFO=$(python3 - <<'PYEOF'
import json, sys, os
from datetime import datetime, timezone

queue_file = os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()), 'queue.json')

try:
    with open(queue_file) as f:
        queue = json.load(f)
except Exception:
    queue = []

count = len(queue)
now = datetime.now().isoformat()

upcoming = [p for p in queue if p.get('scheduledTime', '') > now]
overdue   = [p for p in queue if p.get('scheduledTime', '') <= now]

if upcoming:
    next_post = sorted(upcoming, key=lambda x: x['scheduledTime'])[0]
    next_info = f"Next post scheduled for {next_post['scheduledTime']}: \"{next_post['text'][:60]}{'...' if len(next_post['text']) > 60 else ''}\""
else:
    next_info = "No upcoming posts scheduled."

overdue_info = f"{len(overdue)} post(s) are overdue and will be published on the next hourly run." if overdue else ""

print(f"TOTAL={count}")
print(f"NEXT={next_info}")
print(f"OVERDUE={overdue_info}")
PYEOF
)

TOTAL=$(echo "$QUEUE_INFO" | grep '^TOTAL=' | cut -d= -f2)
NEXT=$(echo "$QUEUE_INFO" | grep '^NEXT=' | cut -d= -f2-)
OVERDUE=$(echo "$QUEUE_INFO" | grep '^OVERDUE=' | cut -d= -f2-)

PROMPT="This is the Threads Auto-Poster project. Before doing anything else, give the user a quick queue status update:
- There are currently ${TOTAL} post(s) in the Threads queue.
- ${NEXT}
${OVERDUE:+- ${OVERDUE}}

Then ask the user: 'Would you like to add a new post to the Threads queue, or is there something else I can help you with?'"

echo "{\"prompt\": $(python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" <<< "$PROMPT")}"
