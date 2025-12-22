// ================= THEME TOGGLE =================
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('themeToggle');
  const body = document.body;

  if (localStorage.getItem('theme') === 'dark') {
    body.classList.add('dark');
    if (themeToggle) themeToggle.textContent = '☀️';
  }

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      body.classList.toggle('dark');
      if (body.classList.contains('dark')) {
        themeToggle.textContent = '☀️';
        localStorage.setItem('theme', 'dark');
      } else {
        themeToggle.textContent = '🌙';
        localStorage.setItem('theme', 'light');
      }
    });
  }
});


// ================= STORY DATA =================
const allStories = JSON.parse(
  document.getElementById("storiesData")?.textContent || "[]"
);


// ================= STORY STATE =================
let currentStories = [];
let currentIndex = 0;
let progressInterval = null;


// ================= OPEN STORIES =================
function openStories(username) {
  currentStories = allStories.filter(s => s.username === username);
  currentIndex = 0;

  if (currentStories.length === 0) return;

  document.getElementById('storyModal').style.display = 'flex';
  showStory();
}


// ================= SHOW STORY =================
function showStory() {
  const content = document.getElementById('storyContent');
  const progressBar = document.getElementById('storyProgressBar');

  content.innerHTML = '';
  progressBar.style.width = '0%';
  clearInterval(progressInterval);

  const story = currentStories[currentIndex];
  if (!story) return closeStoryModal();

  const isVideo = /\.(mp4|webm|ogg|avi)$/i.test(story.url);

  if (isVideo) {
    const video = document.createElement('video');
    video.src = story.url;
    video.autoplay = true;
    video.controls = false;
    video.style.maxWidth = "300px";
    video.style.maxHeight = "420px";
    video.style.borderRadius = "14px";

    video.onended = nextStory;

    content.appendChild(video);
  } else {
    const img = document.createElement('img');
    img.src = story.url;
    img.style.maxWidth = "300px";
    img.style.maxHeight = "420px";
    img.style.borderRadius = "14px";
    img.style.objectFit = "cover";

    content.appendChild(img);
    startProgress();
  }

  enableTapControls();
}


// ================= STORY PROGRESS BAR =================
function startProgress() {
  const progressBar = document.getElementById('storyProgressBar');
  let width = 0;

  progressInterval = setInterval(() => {
    width += 1;
    progressBar.style.width = width + "%";

    if (width >= 100) {
      clearInterval(progressInterval);
      nextStory();
    }
  }, 50);
}


// ================= TAP CONTROLS =================
function enableTapControls() {
  const content = document.getElementById('storyContent');

  content.onclick = (e) => {
    const x = e.clientX;
    const width = window.innerWidth;

    if (x < width / 2) {
      prevStory();
    } else {
      nextStory();
    }
  };
}


// ================= NEXT STORY =================
function nextStory() {
  clearInterval(progressInterval);
  currentIndex++;

  if (currentIndex < currentStories.length) {
    showStory();
  } else {
    closeStoryModal();
  }
}


// ================= PREVIOUS STORY =================
function prevStory() {
  clearInterval(progressInterval);
  currentIndex--;

  if (currentIndex >= 0) {
    showStory();
  } else {
    closeStoryModal();
  }
}


// ================= CLOSE STORY MODAL =================
function closeStoryModal() {
  clearInterval(progressInterval);
  document.getElementById('storyModal').style.display = 'none';
  document.getElementById('storyContent').innerHTML = '';
}



// ================= LIKES =================
function likePost(event, postId, btn) {
    event.preventDefault();
    fetch(`/like/${postId}`)
        .then(() => {
            // Optionally toggle heart style
            if (btn.classList.contains('liked')) {
                btn.classList.remove('liked');
            } else {
                btn.classList.add('liked');
            }
            // Reload page or update count dynamically
            location.reload();
        })
        .catch(err => console.error(err));
}

// ================= COMMENTS =================
function submitComment(event, postId) {
    event.preventDefault();
    const form = event.target;
    const input = form.querySelector('input[name="comment"]');
    const comment = input.value.trim();
    if (!comment) return;

    fetch(`/comment/${postId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `comment=${encodeURIComponent(comment)}`
    })
    .then(() => {
        input.value = '';
        location.reload(); // Reload to show the new comment
    })
    .catch(err => console.error(err));
}

// ================= DELETE POST =================
function deletePost(postId, postElementId) {
    if (!confirm("Are you sure you want to delete this post?")) return;

    fetch(`/delete_post/${postId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const el = document.getElementById(postElementId);
                if (el) el.remove();
            } else {
                alert(data.error || "Could not delete post.");
            }
        })
        .catch(err => console.error(err));
}

// ================= DELETE COMMENT =================
function deleteComment(commentId, commentElementId) {
    if (!confirm("Delete this comment?")) return;

    fetch(`/delete_comment/${commentId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const el = document.getElementById(commentElementId);
                if (el) el.remove();
            } else {
                alert(data.error || "Could not delete comment.");
            }
        })
        .catch(err => console.error(err));
}

// ================= SHARE POST =================
function sharePost(url) {
    const fullUrl = window.location.origin + url;
    navigator.clipboard.writeText(fullUrl)
        .then(() => alert("Post URL copied to clipboard!"))
        .catch(err => alert("Could not copy link."));
}
