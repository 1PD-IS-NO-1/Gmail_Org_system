import os
import pickle
import base64
from flask import Flask, request, redirect, jsonify, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest
from langchain_google_genai import ChatGoogleGenerativeAI
import json
from datetime import datetime, timedelta
import email.utils
import pytz
from googleapiclient.errors import HttpError
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app = Flask(__name__)
app.secret_key = "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"

# Set up OAuth 2.0 flow
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CLIENT_SECRETS_FILE = "credentials.json"

GOOGLE_API_KEY = "paste api key here."  # Replace with your actual API key
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

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

@app.route("/")
def index():
    return redirect("/login")

@app.route("/login")
def login():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return jsonify({"error": "Please upload credentials.json first."}), 400

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

    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)

    return redirect("/emails")

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


# Add this function to your existing code
@app.route("/delete_email", methods=["POST"])
def delete_email():
    # Get credentials
    creds = get_credentials()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    # Get message ID from the request
    data = request.get_json()
    message_id = data.get("message_id")

    if not message_id:
        return jsonify({"error": "Message ID is required"}), 400

    try:
        # Build Gmail service
        service = build("gmail", "v1", credentials=creds)

        # Attempt to delete the email
        service.users().messages().delete(userId="me", id=message_id).execute()
        
        return jsonify({
            "status": "success", 
            "message": f"Email with ID {message_id} has been deleted"
        }), 200

    except HttpError as error:
        # Handle specific Gmail API errors
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