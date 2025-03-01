import os
import json
import time
import re
from langchain_google_genai import ChatGoogleGenerativeAI

GOOGLE_API_KEY = "AIzaSyD5tZR02ryMjdV3unPEqHzlNFUZuPtSPyk"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

def summarize_emails_with_local_merge(
    input_file="email_summary_action.json",
    batch_size=20,
    sleep_seconds=2,
    model_name="gemini-1.5-flash"
):
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Could not find the file: {input_file}")


    with open(input_file, "r", encoding="utf-8") as infile:
        stored_email_data = json.load(infile)

    summarized_emails = []

    for batch_start in range(0, len(stored_email_data), batch_size):
        batch = stored_email_data[batch_start : batch_start + batch_size]
        if not batch:
            continue

        batch_lines = []
        for idx, record in enumerate(batch, start=1):
            sender = record.get("sender", "Unknown Sender")
            subject = record.get("subject", "No Subject")
            body = record.get("body", "").strip()
            if body:
                batch_lines.append(
                    f"Email {idx}:\nSender: {sender}\nSubject: {subject}\nBody: {body}\n"
                )
            else:
                batch_lines.append(
                    f"Email {idx}:\nSender: {sender}\nSubject: {subject}\n(No body)\n"
                )

        batch_text = "\n\n".join(batch_lines)

        prompt = f"""
You have {len(batch)} emails, each with a sender, subject, and possibly a body.
Some emails may have no body; in that case, summarize based on subject and sender alone.

Return exactly a JSON array of summary strings (one summary per email) in the same order:
[
  "summary1",
  "summary2",
  ...
]
No trailing commas, no extra keys, no additional text.

Emails:
{batch_text}
"""

        # Invoke the ChatGoogleGenerativeAI model
        llm = ChatGoogleGenerativeAI(model= "gemini-1.5-flash", google_api_key=GOOGLE_API_KEY)
        response = llm.invoke(prompt)
        raw_content = response.content.strip()

        # Clean up the response
        fence_pattern = r"```(?:json)?(.*?)```"
        raw_content = re.sub(fence_pattern, r"\1", raw_content, flags=re.DOTALL).strip()

        trailing_comma_pattern = r",\s*\]"
        raw_content = re.sub(trailing_comma_pattern, "]", raw_content)

        try:
            batch_summaries = json.loads(raw_content)
        except json.JSONDecodeError:
            print("Could not decode JSON for this batch. Raw LLM response was:\n")
            print(raw_content)
            print("Falling back to a placeholder summary for each email...\n")
            batch_summaries = ["Summary not available (fallback)"] * len(batch)

        if not isinstance(batch_summaries, list):
            print("LLM returned JSON that isn't a list! Using fallback for entire batch.")
            batch_summaries = ["Summary not available (fallback)"] * len(batch)
        elif len(batch_summaries) < len(batch):
            leftover = len(batch) - len(batch_summaries)
            print(
                f"LLM returned fewer summaries ({len(batch_summaries)}) than {len(batch)}. "
                f"Adding fallback for the remaining {leftover}."
            )
            batch_summaries += ["Summary not available (fallback)"] * leftover
        elif len(batch_summaries) > len(batch):
            print(
                f"LLM returned more summaries ({len(batch_summaries)}) than {len(batch)}. "
                f"Truncating to the first {len(batch)}."
            )
            batch_summaries = batch_summaries[: len(batch)]

        for email_record, summary_text in zip(batch, batch_summaries):
            merged_record = {**email_record}  # Copy all original fields
            merged_record["summary"] = summary_text
            summarized_emails.append(merged_record)

        print(f"Processed batch {batch_start // batch_size + 1}, sleeping {sleep_seconds}s...")
        time.sleep(sleep_seconds)

    # Update the input file with the summarized data
    with open(input_file, "w", encoding="utf-8") as outfile:
        json.dump(summarized_emails, outfile, indent=2)

    return summarized_emails

# ------------------ Example Usage ----------------
if __name__ == "__main__":
    results = summarize_emails_with_local_merge(
        input_file="emails.json",
        batch_size=20,
        sleep_seconds=2,
        model_name="gemini-pro"
    )
    print(f"Updated emails.json with summaries. Total: {len(results)} emails processed.")