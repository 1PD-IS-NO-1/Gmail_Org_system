# Gmail_Org
Gmail_Org is a simple Python script that organizes your Gmail inbox into folders based on the sender's domain. It uses the Gmail API to fetch messages and the Google Drive API to create folders.

## Features

- Organizes your Gmail inbox into folders based on the sender's domain.
- Supports both Gmail and Google Workspace accounts.
- Can be run as a standalone script or integrated into a larger application.

## Installation

1. Install the required Python packages:
   ```
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```


2. Create a Google Cloud project and enable the Gmail API and Google Drive API.
3. Create credentials for your project and download the JSON file.
4. Replace `credentials.json` with your downloaded credentials file.
5. Run the script with your Gmail account credentials.

## Usage

1. Replace `credentials.json` with your downloaded credentials file.
2. Run the script with your Gmail account credentials:
   ```
   python app2.py
   ```

## Notes

- The script will prompt you to enter your Gmail account credentials.
- The script will create folders in your Google Drive based on the sender's domain.
- The script will move messages from your Gmail inbox to the corresponding folders.
- The script will not delete any messages from your Gmail inbox.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Project UI
