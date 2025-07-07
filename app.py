import imaplib
import email
from transformers import pipeline
import torch

# IMAP Configuration
IMAP_SERVER = "imap.gmail.com"
USERNAME = "your email"  # Replace with your email
PASSWORD = "your app password from email"


# Connect to IMAP
imap = imaplib.IMAP4_SSL(IMAP_SERVER)
imap.login(USERNAME, PASSWORD)
imap.select("INBOX")

# Fetch ALL emails (not just unread ones)
status, messages = imap.search(None, "ALL")  # ✅ This gets all emails

if not messages[0]:
    print("No emails found.")
    imap.logout()
    exit()

# Load summarization model
print("🚀 Loading summarization model...")
device = 0 if torch.cuda.is_available() else -1
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=device)

print("✅ Model loaded successfully!")

# Function to extract plain text from email
def extract_body(message):
    for part in message.walk():
        if part.get_content_type() == "text/plain":
            return part.get_payload(decode=True).decode(errors="ignore")
    return "No email content found."

# Process all emails
for num in messages[0].split():
    _, msg = imap.fetch(num, "(RFC822)")
    message = email.message_from_bytes(msg[0][1])

    subject = message["Subject"] or "No Subject"
    sender = message["From"]
    date = message["Date"]
    body = extract_body(message)[:1000]  # Limit text to first 1000 characters for speed

    print(f"\n📧Email from: {sender} - Subject: {subject}")

    # Summarize email content
    summary = summarizer(body, max_length=100, min_length=10, truncation=True)[0]["summary_text"]

    print(f"📜 Summary: {summary}")

# Close IMAP connection
imap.close()
imap.logout()
