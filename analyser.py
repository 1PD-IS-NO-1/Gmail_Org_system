from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
import json
import time
import os

GOOGLE_API_KEY = "AIzaSyD5tZR02ryMjdV3unPEqHzlNFUZuPtSPyk"  # Add your GOOGLE API key here
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


import re  # Add this import at the top of your script

def data_with_categor_action_batch_single_prompt(
    emails_json_path="emails.json",
    batch_size=20,
    sleep_seconds=2
):
    """
    Process emails in batches, categorize them, and suggest actions using an LLM.
    """
    # 1) Check if the file exists
    if not os.path.isfile(emails_json_path):
        raise FileNotFoundError(f"Could not find the file: {emails_json_path}")

    # 2) Load the email data
    with open(emails_json_path, "r", encoding="utf-8") as infile:
        stored_email_data = json.load(infile)

    processed_emails = []

    # 3) Process the data in chunks of 'batch_size'
    for i in range(0, len(stored_email_data), batch_size):
        batch = stored_email_data[i : i + batch_size]
        if not batch:
            continue

        batch_list_str = ""
        for idx, email_record in enumerate(batch, start=1):
            subject = email_record.get("subject", "No Subject")
            sender = email_record.get("sender", "Unknown Sender")
            email_id = email_record.get("id", "No ID")
            batch_list_str += f"Email {idx}:\n ID: {email_id}\n Subject: {subject}\n Sender: {sender}\n\n"

        # Here is the prompt body for the entire batch
        prompt = f"""
You are an AI assistant helping a user who is a student at the Indian Institute of Information Technology (IIIT).
They receive various types of emails: academic (from professors or regarding student work), club announcements,
personal emails, social media notifications, promotional newsletters, or spam. 

Here is a batch of emails (each has an ID, Subject, and Sender). Carefully analyze them, one by one,
and decide on a category and a suggested action for each email.

Possible categories (pick the most appropriate one):
- Academic/professors
- Club
- Work
- Personal
- Social/subscription
- Promotional
- spam/others

Possible actions (pick exactly one for each email):
- Flag (for important emails)
- Read Later
- Archive (for old but important emails)
- Unsubscribe (for newsletters, spam)
- Delete (for unnecessary emails)
- Schedule Meeting

Here are the emails:

{batch_list_str}

Return the result as valid JSON in the EXACT format:
[
  {{
    "id": "...",
    "subject": "...",
    "sender": "...",
    "category": "...",
    "action": "..."
  }},
  ...
]

Example:
[
  {{
    "id": "1954be4298bc7003",
    "subject": "Re: Details required for Aadhaar based Biometric Registration of students - reg.",
    "sender": "IIITL Scholarship",
    "category": "Academic/professors",
    "action": "Flag"
  }},
  {{
    "id": "1954bd2d97d7908c",
    "subject": "“data scientist”: Marktine Technology Solutions Pvt Ltd - Data Scientist",
    "sender": "LinkedIn Job Alerts",
    "category": "Work",
    "action": "Read Later"
  }}
]

One JSON object per email in the same order. Each email should be considered independently, 
so do not give the same category/action to all unless it is truly appropriate.
"""

        # Initialize the LLM once per batch
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=GOOGLE_API_KEY
        )

        response = llm.invoke(prompt)
        print("Raw LLM Response:", response.content)  # Debugging: Print the raw response

        # Preprocess the response to remove triple backticks
        response_content = response.content.strip()
        if response_content.startswith("```json") and response_content.endswith("```"):
            response_content = response_content[7:-3].strip()  # Remove ```json and ```

        try:
            batch_result = json.loads(response_content)  # Parse the cleaned response
            if isinstance(batch_result, list):
                for item in batch_result:
                    # Find the corresponding email in the original data
                    original_email = next(
                        (e for e in batch if e["id"] == item["id"]), 
                        None
                    )
                    
                    if original_email:
                        processed_emails.append({
                            "id": item["id"],
                            "subject": item["subject"],
                            "sender": item["sender"],
                            "category": item.get("category", "Other"),
                            "action": item.get("action", "Read Later"),
                            "email_id": original_email.get("email_id", ""),
                            "body": original_email.get("body", "")
                        })
            else:
                print("LLM returned non-list JSON, using fallback.")
                processed_emails.extend(_fallback_parse(batch))
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing JSON: {e}")
            print(f"Response content: {response_content}")
            processed_emails.extend(_fallback_parse(batch))

        # 5) Sleep between batches
        print(f"Completed batch {i//batch_size + 1}, sleeping {sleep_seconds}s...")
        time.sleep(sleep_seconds)

    # 6) Write the combined processed data to "processed.json"
    with open("emails.json", "w", encoding="utf-8") as outfile:
        json.dump(processed_emails, outfile, indent=2)
    return processed_emails

def _fallback_parse(batch):
    """
    Fallback if the LLM's JSON was invalid or not parseable.
    We'll just mark each email with category = 'Other' and action = 'Read Later'.
    """
    fallback_results = []
    for email_record in batch:
        fallback_results.append({
            "id": email_record.get("id", "No ID"),
            "subject": email_record.get("subject", "No Subject"),
            "sender": email_record.get("sender", "Unknown Sender"),
            "category": "Other",
            "action": "Read Later",
            "email_id": email_record.get("email_id", ""),
            "body": email_record.get("body", "")
        })
    return fallback_results  # Ensure this function returns the list


# ------------------------------------
# Example Usage 
# ------------------------------------
if __name__ == "__main__":
    result = data_with_categor_action_batch_single_prompt(
        emails_json_path="emails.json",
        batch_size=20,      # 20 emails at a time
        sleep_seconds=2    # Wait 2 seconds between batches
    )
    print(f"Processed {len(result)} emails in total. Results in 'emails.json'.")