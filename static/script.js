// /================= THEME TOGGLE =================
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

// ================= STORY VIEWER (INSTAGRAM FULL) =================

const allStories = JSON.parse(
  document.getElementById("storiesData")?.textContent || "[]"
);

let currentStories = [];
let currentIndex = 0;
let progressInterval = null;


// Open user stories
function openStories(username) {
  currentStories = allStories.filter(s => s.username === username);
  currentIndex = 0;

  if (currentStories.length === 0) return;

  document.getElementById('storyModal').style.display = 'flex';
  showStory();
}


// Show ONE story
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


// Progress bar for images
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
  }, 50); // ~5 seconds
}


// Tap controls (left / right)
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


// Next story
function nextStory() {
  clearInterval(progressInterval);
  currentIndex++;

  if (currentIndex < currentStories.length) {
    showStory();
  } else {
    closeStoryModal();
  }
}


// Previous story
function prevStory() {
  clearInterval(progressInterval);
  currentIndex--;

  if (currentIndex >= 0) {
    showStory();
  } else {
    closeStoryModal();
  }
}


// Close modal
function closeStoryModal() {
  clearInterval(progressInterval);
  document.getElementById('storyModal').style.display = 'none';
  document.getElementById('storyContent').innerHTML = '';
}
