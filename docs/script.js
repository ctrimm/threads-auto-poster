let s3Enabled = false;

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

async function init() {
  try {
    const res = await fetch('/config');
    const config = await res.json();
    s3Enabled = config.s3_enabled;

    if (s3Enabled) {
      document.getElementById('uploadSection').style.display = 'block';
      document.getElementById('urlHelp').textContent = '(or paste a URL directly)';
    }
  } catch (_) {
    // config endpoint unreachable — server probably not running yet
  }

  await updateQueueList();
}

// ---------------------------------------------------------------------------
// Character counter
// ---------------------------------------------------------------------------

document.getElementById('postText').addEventListener('input', function () {
  document.getElementById('charCount').textContent = `${this.value.length} / 500`;
});

// ---------------------------------------------------------------------------
// Form submit
// ---------------------------------------------------------------------------

document.getElementById('postForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;

  try {
    const text = document.getElementById('postText').value.trim();
    const scheduledTime = document.getElementById('scheduledTime').value;
    const mediaFile = document.getElementById('mediaFile').files[0];
    let mediaUrl = document.getElementById('mediaUrl').value.trim();

    // If a file was chosen and S3 is available, upload it first
    if (mediaFile && s3Enabled) {
      mediaUrl = await uploadToS3(mediaFile);
      if (!mediaUrl) return; // uploadToS3 already showed an error
    }

    const mediaType = mediaUrl
      ? detectMediaType(mediaUrl, mediaFile)
      : 'TEXT';

    const res = await fetch('/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, scheduledTime, mediaType, mediaUrl }),
    });

    if (!res.ok) {
      const err = await res.json();
      showMessage(err.error || 'Failed to add post.', 'error');
      return;
    }

    showMessage('Post added to queue!', 'success');
    document.getElementById('postForm').reset();
    document.getElementById('charCount').textContent = '0 / 500';
    await updateQueueList();
  } finally {
    btn.disabled = false;
  }
});

// ---------------------------------------------------------------------------
// S3 upload
// ---------------------------------------------------------------------------

async function uploadToS3(file) {
  const status = document.getElementById('uploadStatus');
  status.textContent = 'Uploading…';

  const form = new FormData();
  form.append('file', file);

  const res = await fetch('/upload', { method: 'POST', body: form });
  const data = await res.json();

  if (!res.ok) {
    showMessage(data.error || 'Upload failed.', 'error');
    status.textContent = '';
    return null;
  }

  status.textContent = 'Uploaded.';
  return data.url;
}

// ---------------------------------------------------------------------------
// Queue display
// ---------------------------------------------------------------------------

async function updateQueueList() {
  const list = document.getElementById('queueList');

  try {
    const res = await fetch('/queue');
    const queue = await res.json();

    list.innerHTML = '';

    if (queue.length === 0) {
      list.innerHTML = '<li class="empty">No posts scheduled.</li>';
      return;
    }

    queue.forEach(post => {
      const li = document.createElement('li');

      const info = document.createElement('span');
      const when = new Date(post.scheduledTime).toLocaleString();
      info.textContent = `${when} — ${post.text}`;
      if (post.mediaUrl) {
        info.textContent += ` [${post.mediaType}]`;
      }

      const del = document.createElement('button');
      del.textContent = 'Remove';
      del.className = 'delete-btn';
      del.addEventListener('click', () => removePost(post.id));

      li.appendChild(info);
      li.appendChild(del);
      list.appendChild(li);
    });
  } catch (err) {
    console.error('Could not load queue:', err);
  }
}

async function removePost(id) {
  await fetch(`/queue/${id}`, { method: 'DELETE' });
  await updateQueueList();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function detectMediaType(url, file) {
  const mime = file ? file.type : '';
  if (mime.startsWith('video/') || /\.(mp4|mov|avi|webm)$/i.test(url)) return 'VIDEO';
  if (mime.startsWith('image/') || /\.(jpg|jpeg|png|gif|webp)$/i.test(url)) return 'IMAGE';
  return 'TEXT';
}

function showMessage(text, type) {
  const div = document.getElementById('message');
  div.textContent = text;
  div.className = type;
  setTimeout(() => { div.textContent = ''; div.className = ''; }, 4000);
}

// ---------------------------------------------------------------------------

init();
