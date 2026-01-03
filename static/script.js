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


// ================= STORY EDIT AND DELETE BTN =================
document.querySelectorAll('.story')
.forEach(story => { // Auto disappear after 10 seconds (for demo) 
    setTimeout(() => story.remove(), 86400000);
    });

function deleteStory(storyId, btn) {
  if (!confirm("Delete this story?")) return;

  fetch(`/delete_story/${storyId}`, {
    method: "POST"
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      btn.closest(".story").remove();
    } else {
      alert(data.error || "Error deleting story");
    }
  })
  .catch(err => console.error(err));
}



// ================= LIKES =================
function likePost(event, postId, btn) {
    event.preventDefault();

    // Optimistic toggle
    const isLiked = btn.classList.contains('liked');
    btn.classList.toggle('liked');
    let likeCount = parseInt(btn.dataset.likeCount || 0);
    likeCount += isLiked ? -1 : 1;
    btn.dataset.likeCount = likeCount;
    btn.textContent = `❤️ ${likeCount} Likes`;

    // Send update to backend
    fetch(`/like/${postId}`, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            // Sync just in case server differs
            btn.classList.toggle('liked', data.liked);
            btn.dataset.likeCount = data.like_count;
            btn.textContent = `❤️ ${data.like_count} Likes`;
        })
        .catch(err => {
            console.error(err);
            // Revert UI if error
            btn.classList.toggle('liked', isLiked);
            btn.dataset.likeCount = isLiked ? likeCount + 1 : likeCount - 1;
            btn.textContent = `❤️ ${btn.dataset.likeCount} Likes`;
        });
}
setInterval(async () => {
    const posts = document.querySelectorAll('.like-btn');
    for (let btn of posts) {
        const postId = btn.dataset.postId;
        const res = await fetch(`/like-count/${postId}`);
        const data = await res.json();
        btn.dataset.likeCount = data.like_count;
        btn.textContent = `❤️ ${data.like_count} Likes`;
        btn.classList.toggle('liked', data.user_liked);
    }
}, 5000); // every 5 seconds

// ================= COMMENTS =================
function submitComment(event, postId) {
    event.preventDefault();
    const form = event.target;
    const input = form.querySelector('input[name="comment"]');
    const commentText = input.value.trim();
    if (!commentText) return;

    fetch(`/comment/${postId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `comment=${encodeURIComponent(commentText)}`
    })
    .then(res => res.json())
    .then(data => {
        // Clear input
        input.value = '';

        // Add new comment dynamically
         const commentsDiv = document.getElementById(`comments-${postId}`);
         const div = document.createElement('div');
         div.className = 'comment';
         div.id = `comment-${data.id}`;
         // Add inner content without onclick
          div.innerHTML = `
          <strong>@${data.username}:</strong>
          <span class="comment-text">${data.text}</span>
          <button class="edit-btn">✏️</button>
          <button class="delete-btn">🗑️</button>
          `;

          // Append to comments container
          commentsDiv.appendChild(div);

          // Attach event listeners
         div.querySelector('.edit-btn').addEventListener('click', () => editComment(data.id));
         div.querySelector('.delete-btn').addEventListener('click', () => deleteComment(data.id, `comment-${data.id}`));

          // Update comment count
         const commentBtn = form.querySelector('button');
         const count = commentsDiv.querySelectorAll('.comment').length;
         commentBtn.textContent = `💬 Comment (${count})`;
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

// ================= SHARE POST =================
function sharePost(url) {
    const fullUrl = window.location.origin + url;
    navigator.clipboard.writeText(fullUrl)
        .then(() => alert("Post URL copied to clipboard!"))
        .catch(err => alert("Could not copy link."));
}


/* ==============================
   HARNECT ANIMATIONS CONTROLLER
============================== */

/* PAGE TRANSITION */
document.querySelectorAll("a").forEach(link => {
  if (link.target === "_blank") return;

  link.addEventListener("click", e => {
    const page = document.querySelector(".page");
    if (!page) return;

    e.preventDefault();
    page.classList.add("page-exit");

    setTimeout(() => {
      window.location = link.href;
    }, 250);
  });
});

/* LIKE BUTTON */
document.querySelectorAll(".like-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    btn.classList.toggle("liked");
  });
});

/* DELETE POST / VIDEO */
document.querySelectorAll(".delete-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    const post = e.target.closest(".post");
    if (!post) return;

    post.classList.add("deleting");
    setTimeout(() => post.remove(), 250);
  });
});

/* STORY OPEN / CLOSE */
document.querySelectorAll(".story-circle").forEach(story => {
  story.addEventListener("click", () => {
    const modal = document.querySelector(".story-modal");
    if (!modal) return;

    modal.style.display = "flex";
  });
});

document.querySelectorAll(".close-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const modal = document.querySelector(".story-modal");
    if (!modal) return;

    modal.classList.add("deleting");
    setTimeout(() => {
      modal.style.display = "none";
      modal.classList.remove("deleting");
    }, 250);
  });
});

/* UPLOAD SUCCESS */
document.querySelectorAll(".upload-form").forEach(form => {
  form.addEventListener("submit", () => {
    form.classList.add("upload-success");
  });
});

/* PROFILE PIC UPDATE */
const profilePicInput = document.querySelector("#profilePicInput");
if (profilePicInput) {
  profilePicInput.addEventListener("change", () => {
    document.querySelector(".profile-pic")?.classList.add("updated");
  });
}

/* BIO UPDATE */
document.querySelectorAll(".edit-bio-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelector(".profile-info p")?.classList.add("updated");
  });
});

/* FEEDBACK ADD / EDIT / DELETE */
document.querySelectorAll(".feedback-item").forEach(item => {
  item.addEventListener("dblclick", () => {
    item.classList.add("edited");
    setTimeout(() => item.classList.remove("edited"), 300);
  });
});

document.querySelectorAll(".delete-feedback").forEach(btn => {
  btn.addEventListener("click", e => {
    const item = e.target.closest(".feedback-item");
    if (!item) return;

    item.classList.add("deleting");
    setTimeout(() => item.remove(), 250);
  });
});

/* EXPLORE SEARCH RESULT ANIMATION */
document.querySelectorAll(".explore-item").forEach(item => {
  item.style.animation = "fadeSlideUp .35s ease";
});

/*edit and delete comment*/

function deleteComment(commentId) {
  if (!confirm("Delete this comment?")) return;

  fetch(`/delete_comment/${commentId}`, {
    method: "POST"
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      document.getElementById(`comment-${commentId}`).remove();
    } else {
      alert(data.error || "Error deleting comment");
    }
  });
}


function editComment(commentId) {
  const commentDiv = document.getElementById(`comment-${commentId}`);
  const oldText = commentDiv.querySelector(".comment-text").innerText;

  const newText = prompt("Edit your comment:", oldText);
  if (!newText || newText.trim() === oldText) return;

  fetch(`/edit_comment/${commentId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: `text=${encodeURIComponent(newText)}`
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      commentDiv.querySelector(".comment-text").innerText = data.text;
    } else {
      alert(data.error || "Error editing comment");
    }
  });
}


