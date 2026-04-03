const GITHUB_USERNAME = 'ctrimm';
const REPO_NAME = 'threads-auto-poster';
const MEDIA_REPO_NAME = 'threads-media-storage';

function getToken() {
  return localStorage.getItem('github_token') || '';
}

document.getElementById('postForm').addEventListener('submit', function(e) {
  e.preventDefault();
  addToQueue();
});

document.getElementById('tokenInput').addEventListener('change', function() {
  localStorage.setItem('github_token', this.value);
  showMessage('Token saved.', 'success');
});

// Load saved token on page load
window.addEventListener('DOMContentLoaded', function() {
  const saved = getToken();
  if (saved) {
    document.getElementById('tokenInput').value = saved;
  }
  updateQueueList();
});

async function addToQueue() {
  const token = getToken();
  if (!token) {
    showMessage('Please enter your GitHub token in Settings above.', 'error');
    return;
  }

  const text = document.getElementById('postText').value;
  const scheduledTime = document.getElementById('scheduledTime').value;
  const mediaType = document.getElementById('mediaType').value;
  const mediaFile = document.getElementById('mediaFile').files[0];

  if (!text || !scheduledTime) {
    showMessage('Please enter both text and scheduled time.', 'error');
    return;
  }

  if (mediaType !== 'TEXT' && !mediaFile) {
    showMessage('Please provide a media file for Image or Video posts.', 'error');
    return;
  }

  let mediaUrl = '';
  if (mediaFile) {
    try {
      mediaUrl = await uploadMedia(mediaFile, token);
    } catch (error) {
      showMessage('Failed to upload media. Please try again.', 'error');
      return;
    }
  }

  const postData = { text, scheduledTime, mediaType, mediaUrl };

  try {
    const response = await fetch(`https://api.github.com/repos/${GITHUB_USERNAME}/${REPO_NAME}/contents/queue.json`, {
      headers: { 'Authorization': `token ${token}` }
    });
    const data = await response.json();
    let queue = JSON.parse(atob(data.content));

    postData.id = Date.now();
    queue.push(postData);

    const updatedContent = btoa(unescape(encodeURIComponent(JSON.stringify(queue, null, 2))));

    const putResponse = await fetch(`https://api.github.com/repos/${GITHUB_USERNAME}/${REPO_NAME}/contents/queue.json`, {
      method: 'PUT',
      headers: {
        'Authorization': `token ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'Add new post to queue',
        content: updatedContent,
        sha: data.sha
      })
    });

    if (!putResponse.ok) {
      throw new Error(`GitHub API error: ${putResponse.status}`);
    }

    showMessage('Post added to queue successfully!', 'success');
    updateQueueList();
  } catch (error) {
    console.error('Error:', error);
    showMessage('Failed to add post to queue. Please try again.', 'error');
  }
}

async function uploadMedia(file, token) {
  const content = await readFileAsBase64(file);
  const fileName = `${Date.now()}-${file.name}`;

  const response = await fetch(`https://api.github.com/repos/${GITHUB_USERNAME}/${MEDIA_REPO_NAME}/contents/${fileName}`, {
    method: 'PUT',
    headers: {
      'Authorization': `token ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: 'Upload media for Threads post',
      content: content
    })
  });

  if (!response.ok) {
    throw new Error(`Media upload failed: ${response.status}`);
  }

  const data = await response.json();
  return data.content.download_url;
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = error => reject(error);
    reader.readAsDataURL(file);
  });
}

async function updateQueueList() {
  try {
    const response = await fetch(`https://raw.githubusercontent.com/${GITHUB_USERNAME}/${REPO_NAME}/main/queue.json`);
    const queue = await response.json();

    const queueList = document.getElementById('queueList');
    queueList.innerHTML = '';

    if (queue.length === 0) {
      queueList.innerHTML = '<li>No posts scheduled.</li>';
      return;
    }

    queue.forEach(post => {
      const li = document.createElement('li');
      li.textContent = `${post.text} (${post.mediaType}, Scheduled: ${post.scheduledTime})`;
      if (post.mediaUrl) {
        li.textContent += ` - Media: ${post.mediaUrl}`;
      }
      queueList.appendChild(li);
    });
  } catch (error) {
    console.error('Error loading queue:', error);
  }
}

function showMessage(message, type) {
  const messageDiv = document.getElementById('message');
  messageDiv.textContent = message;
  messageDiv.className = type;
}
