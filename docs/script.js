document.getElementById('postForm').addEventListener('submit', function(e) {
  e.preventDefault();
  addToQueue();
});

async function addToQueue() {
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
      mediaUrl = await uploadMedia(mediaFile);
    } catch (error) {
      showMessage('Failed to upload media. Please try again.', 'error');
      return;
    }
  }

  const postData = { text, scheduledTime, mediaType, mediaUrl };

  try {
    const response = await fetch('https://api.github.com/repos/YOUR_USERNAME/threads-auto-poster/contents/queue.json');
    const data = await response.json();
    let queue = JSON.parse(atob(data.content));
    
    postData.id = queue.length + 1;
    queue.push(postData);

    const updatedContent = btoa(JSON.stringify(queue, null, 2));
    
    await fetch('https://api.github.com/repos/YOUR_USERNAME/threads-auto-poster/contents/queue.json', {
      method: 'PUT',
      headers: {
        'Authorization': `token ${YOUR_GITHUB_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'Add new post to queue',
        content: updatedContent,
        sha: data.sha
      })
    });

    showMessage('Post added to queue successfully!', 'success');
    updateQueueList();
  } catch (error) {
    console.error('Error:', error);
    showMessage('Failed to add post to queue. Please try again.', 'error');
  }
}

async function uploadMedia(file) {
  const content = await readFileAsBase64(file);
  const fileName = `${Date.now()}-${file.name}`;
  
  const response = await fetch(`https://api.github.com/repos/YOUR_USERNAME/threads-media-storage/contents/${fileName}`, {
    method: 'PUT',
    headers: {
      'Authorization': `token ${YOUR_GITHUB_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: 'Upload media for Threads post',
      content: content
    })
  });

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
    const response = await fetch('https://raw.githubusercontent.com/YOUR_USERNAME/threads-auto-poster/main/queue.json');
    const queue = await response.json();
    
    const queueList = document.getElementById('queueList');
    queueList.innerHTML = '';
    queue.forEach(post => {
      const li = document.createElement('li');
      li.textContent = `${post.text} (${post.mediaType}, Scheduled: ${post.scheduledTime})`;
      if (post.mediaUrl) {
        li.textContent += ` - Media: ${post.mediaUrl}`;
      }
      queueList.appendChild(li);
    });
  } catch (error) {
      console.error('Error:', error);
  }
}

function showMessage(message, type) {
  const messageDiv = document.getElementById('message');
  messageDiv.textContent = message;
  messageDiv.className = type;
}

updateQueueList();
