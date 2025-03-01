# app.py (Flask backend)
import os
import pickle
import base64
from flask import Flask, request, redirect, jsonify, session, render_template
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.errors import HttpError
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import subprocess
from datetime import datetime, timedelta
import pytz
import shutil
import sys
from io import StringIO
from contextlib import redirect_stdout

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app = Flask(__name__)
app.secret_key = "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"

GOOGLE_API_KEY = "AIzaSyD5tZR02ryMjdV3unPEqHzlNFUZuPtSPyk"  # Replace with your actual API key
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Updated SCOPES to include modifying emails
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',  # Required for modifying labels
    'https://www.googleapis.com/auth/gmail.labels'   # Required for managing labels
]
CLIENT_SECRETS_FILE = "credentials.json"

@app.route("/chat", methods=['POST'])
def chat():
    from agent import EmailAnalyzer, llm, json_data  # Import here to defer initialization
    message = request.json.get('message')
    output_buffer = StringIO()
    analyzer = EmailAnalyzer(llm, json_data)
    code = analyzer.get_code_from_llm(message)
    with redirect_stdout(output_buffer):
        analyzer.execute_code(code)

    response = output_buffer.getvalue()
    
    return jsonify({
        'code': code,
        'response': response if response else "No results found."
    })

def get_credentials():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            return None
    return creds

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'credentials' in request.files:
            credentials_file = request.files['credentials']
            credentials_file.save("credentials.json")
            return "Credentials uploaded successfully!"
        else:
            return "No credentials file uploaded.", 400
    return render_template("deep.html")

@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/callback"
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    return redirect(auth_url)

@app.route("/callback")
def callback():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/callback"
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    # Save the credentials for subsequent use
    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)

    # Redirect to the home page after login
    return redirect("/")  # Changed from "/emails" to "/"

@app.route("/emails")
def get_emails():
    creds = get_credentials()
    if not creds:
        return redirect("/login")

    now = datetime.now(pytz.UTC)
    yesterday = now - timedelta(days=2)
    query = f"after:{int(yesterday.timestamp())}"

    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", q=query).execute()
    messages = results.get("messages", [])

    email_data = []

    for msg in messages:
        msg_detail = service.users().messages().get(userId="me", id=msg["id"]).execute()
        headers = msg_detail.get("payload", {}).get("headers", [])

        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender_full = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

        email_id = ""
        if "<" in sender_full and ">" in sender_full:
            email_id = sender_full[sender_full.find("<") + 1:sender_full.find(">")]
        else:
            email_id = sender_full

        received_date = datetime.fromtimestamp(int(msg_detail['internalDate']) / 1000, pytz.UTC)

        if received_date >= yesterday:
            body_text = ""
            payload = msg_detail.get("payload", {})

            if "parts" in payload:
                for part in payload["parts"]:
                    mime_type = part.get("mimeType", "")
                    if mime_type == "text/plain":
                        data = part["body"].get("data", "")
                        if data:
                            decoded_bytes = base64.urlsafe_b64decode(data.encode("utf-8"))
                            body_text = decoded_bytes.decode("utf-8", errors="replace")
                            break
            elif "body" in payload:
                data = payload["body"].get("data", "")
                if data:
                    decoded_bytes = base64.urlsafe_b64decode(data.encode("utf-8"))
                    body_text = decoded_bytes.decode("utf-8", errors="replace")

            email_data.append({
                "id": msg["id"],
                "subject": subject,
                "sender": sender_full,
                "email_id": email_id,
                "body": body_text
            })

    with open("emails.json", "w", encoding="utf-8") as outfile:
        json.dump(email_data, outfile, indent=2)

    session["email_data"] = email_data
    return jsonify(email_data)

@app.route("/clean_emails")
def clean_emails_route():
    subprocess.run(["python", "cleaner.py"])
    with open("emails.json", "r", encoding="utf-8") as f:
      data = json.load(f)
    return jsonify(data)

@app.route("/analyze_emails")
def analyze_emails_route():
    subprocess.run(["python", "analyser.py"])
    subprocess.run(["python", "combine_summary.py"])
    with open("emails.json", "r", encoding="utf-8") as f:
      data = json.load(f)
    return jsonify(data)

@app.route("/delete_email", methods=["POST"])
def delete_email():
    creds = get_credentials()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    message_id = data.get("message_id")

    if not message_id:
        return jsonify({"error": "Message ID is required"}), 400

    try:
        service = build("gmail", "v1", credentials=creds)
        service.users().messages().delete(userId="me", id=message_id).execute()
        return jsonify({
            "status": "success", 
            "message": f"Email with ID {message_id} has been deleted"
        }), 200

    except HttpError as error:
        error_details = {
            403: "Permission denied. Check your scopes.",
            404: "Message not found.",
            500: "Internal server error"
        }
        error_message = error_details.get(error.resp.status, "An unknown error occurred")
        return jsonify({
            "status": "error", 
            "message": error_message,
            "details": str(error)
        }), error.resp.status

# New route to move emails to specific labels
@app.route("/move_email", methods=["POST"])
def move_email():
    creds = get_credentials()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    message_id = data.get("message_id")
    label = data.get("label")  # e.g., "TRASH", "SPAM", "IMPORTANT", "INBOX", etc.

    if not message_id or not label:
        return jsonify({"error": "Message ID and label are required"}), 400

    try:
        service = build("gmail", "v1", credentials=creds)
        
        # Modify the email's labels
        if label == "TRASH":
            service.users().messages().trash(userId="me", id=message_id).execute()
        elif label == "SPAM":
            service.users().messages().trash(userId="me", id=message_id).execute()
            service.users().messages().untrash(userId="me", id=message_id).execute()
            service.users().messages().spam(userId="me", id=message_id).execute()
        elif label == "IMPORTANT":
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": ["IMPORTANT"]}
            ).execute()
        elif label == "ARCHIVE":
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["INBOX"]}
            ).execute()
        else:
            return jsonify({"error": "Invalid label"}), 400

        return jsonify({
            "status": "success", 
            "message": f"Email with ID {message_id} has been moved to {label}"
        }), 200

    except HttpError as error:
        error_details = {
            403: "Permission denied. Check your scopes.",
            404: "Message not found.",
            500: "Internal server error"
        }
        error_message = error_details.get(error.resp.status, "An unknown error occurred")
        return jsonify({
            "status": "error", 
            "message": error_message,
            "details": str(error)
        }), error.resp.status

if __name__ == "__main__":
    app.run(debug=True, port=8000)