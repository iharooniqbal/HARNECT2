document.addEventListener('DOMContentLoaded', () => {

  // ==========================
  // THEME TOGGLE
  // ==========================
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

  // ==========================
  // LIKE POST
  // ==========================
  window.likePost = function(event, filename, btn) {
      event.preventDefault();
      fetch(`/like_post/${filename}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
      })
      .then(res => res.json())
      .then(data => {
          if (data.error) return alert(data.error);
          if (data.liked) {
              btn.textContent = `💖 ${data.likes} Likes`;
              btn.classList.add('liked');
          } else {
              btn.textContent = `❤️ ${data.likes} Likes`;
              btn.classList.remove('liked');
          }
      })
      .catch(err => console.error(err));
  };

  // ==========================
  // SUBMIT COMMENT
  // ==========================
  window.submitComment = function(event, filename) {
      event.preventDefault();
      const form = event.target;
      const input = form.querySelector('input[name="comment"]');
      const text = input.value.trim();
      if (!text) return;

      fetch(`/comment_post/${filename}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ comment: text })
      })
      .then(res => res.json())
      .then(data => {
          if (data.error) return alert(data.error);

          const commentsDiv = document.getElementById(`comments-${filename}`);
          const p = document.createElement('p');
          const lastComment = data.comments[data.comments.length - 1];
          p.innerHTML = `<strong>@${lastComment.user}:</strong> ${lastComment.text}`;
          commentsDiv.appendChild(p);
          input.value = '';
      })
      .catch(err => console.error(err));
  };

  // ==========================
  // SHARE POST
  // ==========================
  window.sharePost = function(url) {
      navigator.clipboard.writeText(url)
          .then(() => alert('Post link copied to clipboard!'))
          .catch(err => console.error(err));
  };

  // ==========================
  // DELETE POST
  // ==========================
  window.deletePost = function(filename) {
      if (!confirm("Are you sure you want to delete this post?")) return;

      fetch(`/delete_post/${filename}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
      })
      .then(res => res.json())
      .then(data => {
          if (data.error) return alert(data.error);
          const el = document.getElementById(`post-${filename}`);
          if (el) el.remove();
      })
      .catch(err => console.error(err));
  };


  // ==========================
  // FOLLOW / UNFOLLOW
  // ==========================
  window.toggleFollow = function(profileUser, btn) {
      fetch(`/follow/${profileUser}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
      })
      .then(res => res.json())
      .then(data => {
          if (data.error) return alert(data.error);

          if (data.action === 'followed') {
              btn.textContent = 'Unfollow';
          } else {
              btn.textContent = 'Follow';
          }

          const followersSpan = document.getElementById('followersCount');
          if (followersSpan) followersSpan.textContent = `${data.followers_count} followers`;
      })
      .catch(err => console.error(err));
  };

});



// ===== STORY VIEWER LOGIC =====
const allStories = JSON.parse(document.getElementById("storiesData")?.textContent || "[]");
let currentStories = [];
let currentIndex = 0;
let progressInterval;

function openStories(username) {
  currentStories = allStories.filter(s => s.user === username);
  currentIndex = 0;
  document.getElementById("storyUser").innerText = '@' + username;
  document.getElementById("storyModal").style.display = "flex";
  showStory();
}

function showStory() {
  const story = currentStories[currentIndex];
  const container = document.getElementById("storyMediaContainer");
  container.innerHTML = "";

  if (!story) return closeStory();

  const isVideo = /\.(mp4|webm|ogg|avi)$/i.test(story.filename);
  const mediaPath = "/static/uploads/" + story.filename;

  if (isVideo) {
    const video = document.createElement("video");
    video.src = mediaPath;
    video.autoplay = true;
    video.controls = true;
    video.style.maxWidth = "300px";
    video.style.maxHeight = "400px";
    video.style.borderRadius = "12px";
    video.onended = nextStory;
    container.appendChild(video);
  } else {
    const img = document.createElement("img");
    img.src = mediaPath;
    img.style.maxWidth = "300px";
    img.style.maxHeight = "400px";
    img.style.borderRadius = "12px";
    container.appendChild(img);
    startProgress();
  }

  // Handle delete button visibility
  const deleteBtn = document.getElementById("deleteStoryBtn");
  if (story.user === window.loggedInUser) {
    deleteBtn.style.display = "inline-block";
  } else {
    deleteBtn.style.display = "none";
  }
}

function startProgress() {
  const progress = document.getElementById("progressBar");
  progress.style.width = "0%";
  clearInterval(progressInterval);
  let width = 0;
  progressInterval = setInterval(() => {
    if (width >= 100) {
      clearInterval(progressInterval);
      nextStory();
    } else {
      width++;
      progress.style.width = width + "%";
    }
  }, 50);
}

function nextStory() {
  currentIndex++;
  if (currentIndex < currentStories.length) {
    showStory();
  } else {
    closeStory();
  }
}

function prevStory() {
  currentIndex--;
  if (currentIndex >= 0) {
    showStory();
  } else {
    closeStory();
  }
}

function closeStory() {
  document.getElementById("storyModal").style.display = "none";
  clearInterval(progressInterval);
}

function deleteStory() {
  const story = currentStories[currentIndex];
  if (confirm("Are you sure you want to delete this story?")) {
    fetch(`/delete_story/${story.id}`, { method: "POST" })
      .then(res => res.json())
      .then(data => {
        alert(data.message);
        closeStory();
        location.reload();
      })
      .catch(err => console.error(err));
  }
}
