import sqlite3

# Connect to HARNECT DB
conn = sqlite3.connect("harnect.db")
c = conn.cursor()

# ---------------------------
# Delete all posts, likes, comments
# ---------------------------
c.execute("DELETE FROM likes")
c.execute("DELETE FROM comments")
c.execute("DELETE FROM posts")

# Reset auto-increment IDs for posts, likes, comments
c.execute("DELETE FROM sqlite_sequence WHERE name='posts'")
c.execute("DELETE FROM sqlite_sequence WHERE name='likes'")
c.execute("DELETE FROM sqlite_sequence WHERE name='comments'")

# ---------------------------
# Delete all feedback
# ---------------------------
c.execute("DELETE FROM feedback")
c.execute("DELETE FROM sqlite_sequence WHERE name='feedback'")

conn.commit()
conn.close()

print("HARNECT DB reset complete! All posts, likes, comments, and feedback deleted.")
