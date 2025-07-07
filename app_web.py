from flask import Flask, render_template, request, redirect, url_for, session
import imaplib
import email
from email.header import decode_header
from transformers import pipeline
import torch

# Flask App Setup
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Load AI Email Summarizer Model
device = 0 if torch.cuda.is_available() else -1
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=device)

# Email Configuration
IMAP_SERVER = "imap.gmail.com"
EMAILS_PER_PAGE = 5

# Login Page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_user = request.form["email"]
        email_pass = request.form["password"]
        session["email"] = email_user
        session["password"] = email_pass
        return redirect(url_for("dashboard"))
    return render_template("login.html")

# Extract plain text from email
def extract_body(message):
    for part in message.walk():
        if part.get_content_type() == "text/plain":
            return part.get_payload(decode=True).decode(errors="ignore")
    return "No content found."

# Dashboard with Email Fetching and Pagination
@app.route("/dashboard")
def dashboard():
    email_user = session.get("email")
    email_pass = session.get("password")
    fetch_type = request.args.get("fetch", "ALL")  # "ALL" or "UNSEEN"
    page = int(request.args.get("page", 1))

    if not email_user or not email_pass:
        return redirect(url_for("login"))

    try:
        # Connect to Email
        imap = imaplib.IMAP4_SSL(IMAP_SERVER)
        imap.login(email_user, email_pass)
        imap.select("INBOX")

        # Fetch Emails
        status, messages = imap.search(None, fetch_type)
        email_ids = messages[0].split()
        email_ids = email_ids[::-1]  # Reverse to get newest emails first

        # Pagination
        total_emails = len(email_ids)
        total_pages = (total_emails + EMAILS_PER_PAGE - 1) // EMAILS_PER_PAGE
        start_idx = (page - 1) * EMAILS_PER_PAGE
        end_idx = start_idx + EMAILS_PER_PAGE
        email_subset = email_ids[start_idx:end_idx]

        email_summaries = []
        for num in email_subset:
            _, msg = imap.fetch(num, "(RFC822)")
            message = email.message_from_bytes(msg[0][1])

            # Decode the subject
            raw_subject = message["Subject"]
            if raw_subject:
                decoded_subject = decode_header(raw_subject)
                # Combine decoded parts into a single string
                subject = ""
                for part, encoding in decoded_subject:
                    if isinstance(part, bytes):
                        # Decode bytes using specified encoding or UTF-8 as fallback
                        subject += part.decode(encoding or "utf-8", errors="ignore")
                    else:
                        # Part is already a string
                        subject += part
            else:
                subject = "No Subject"

            sender = message["From"]
            body = extract_body(message)[:1000]  # Limit text for performance
            summary = summarizer(body, max_length=100, min_length=10, truncation=True)[0]["summary_text"]

            email_summaries.append({
                "sender": sender,
                "subject": subject,
                "summary": summary
            })

        imap.close()
        imap.logout()

        return render_template("dashboard.html", email=email_user, emails=email_summaries, total_pages=total_pages,
                               current_page=page, fetch_type=fetch_type)

    except Exception as e:
        return render_template("dashboard.html", email=email_user, emails=[], error=str(e), total_pages=1,
                               current_page=1, fetch_type=fetch_type)

if __name__ == "__main__":
    app.run(debug=True)