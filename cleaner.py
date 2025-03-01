import os
import json
import re
import html

def clean_text_basic(text: str) -> str:
    """Basic cleaning for email bodies"""
    # Replace Windows-style newlines and spaces
    text = text.replace("\r\n", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def clean_text_ssb(text):
    """Advanced cleaning including HTML and formatting"""
    if not isinstance(text, str):
        return text

    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove extra dashes
    text = re.sub(r'-{2,}', '-', text)
    
    # Preserve emails in angle brackets but remove extra quotes around names
    text = re.sub(r'^"(.*?)"\s*(<.*?>)$', r'\1 \2', text)
    text = re.sub(r'(?<!<)"(.*?)"(?!>)', r'\1', text)
    
    # Ensure emails are correctly formatted
    text = re.sub(r'\s*<([^<>]+)>', r' <\1>', text)
    
    # Remove unnecessary newlines and excess spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def process_text_by_length(text: str) -> str:
    """Process text based on word count requirements"""
    words = text.split()
    word_count = len(words)
    
    if 200 < word_count <= 500:
        return " ".join(words[:200])
    elif word_count > 500:
        first_part = " ".join(words[:100])
        last_part = " ".join(words[-200:])
        return f"{first_part} [...] {last_part}"
    return text

def clean_emails(input_file="emails.json"):
    """Main function to clean email data"""
    
    # Check if input file exists
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Could not find the file: {input_file}")

    # Load the email data
    with open(input_file, "r", encoding="utf-8") as infile:
        email_data = json.load(infile)

    # Process each email
    for email_record in email_data:
        # First pass: Clean body text
        raw_body = email_record.get("body", "")
        
        # Apply body cleaning steps
        cleaned_body = clean_text_basic(raw_body)
        cleaned_body = re.sub(r"(http|https)://\S+|www\.\S+", "", cleaned_body)
        cleaned_body = clean_text_basic(cleaned_body)
        cleaned_body = process_text_by_length(cleaned_body)
        
        # Update body
        email_record["body"] = cleaned_body
        
        # Second pass: Clean all fields with SSB cleaner
        for key, value in email_record.items():
            email_record[key] = clean_text_ssb(value)

    # Write back to the same file
    with open(input_file, "w", encoding="utf-8") as outfile:
        json.dump(email_data, outfile, indent=2, ensure_ascii=False)

    print(f"✅ Processed and cleaned {len(email_data)} email entries.")
    print(f"✅ Updated file saved to {input_file}")
    
    return email_data

if __name__ == "__main__":
    # Process emails.json and update it with cleaned content
    cleaned_data = clean_emails("emails.json")