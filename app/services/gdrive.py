import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from loguru import logger
from app.config import config

# If modifying these scopes, delete the token file.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def _get_credentials():
    logger.info("Getting Google Drive credentials")
    drive_cfg = config.google_drive or {}
    creds_path = drive_cfg.get('credentials_file')
    token_path = drive_cfg.get('token_file', 'token.json')

    if not creds_path or not os.path.exists(creds_path):
        logger.error(f"Google Drive credentials file not found: {creds_path}")
        raise FileNotFoundError(f"Google Drive credentials file not found: {creds_path}")

    creds = None
    # Load existing token if available
    if os.path.exists(token_path):
        logger.info(f"Loading token from {token_path}")
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        logger.info("No valid credentials, initiating login flow")
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())
        else:
            logger.info("Starting OAuth flow to obtain new credentials")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
            logger.info(f"Saved new token to {token_path}")

    logger.info("Google Drive credentials obtained successfully")
    return creds

def upload_file(file_path: str) -> str:
    """
    Uploads a file to Google Drive and returns a shareable link.
    """
    logger.info(f"Starting upload of file: {file_path}")
    creds = _get_credentials()
    service = build('drive', 'v3', credentials=creds)

    drive_cfg = config.google_drive or {}
    folder_id = drive_cfg.get('folder_id')
    file_metadata = {'name': os.path.basename(file_path)}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(file_path, resumable=True)
    logger.info("Uploading media to Drive")
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')
    logger.info(f"File uploaded; Drive file ID: {file_id}")

    # Make the file readable by anyone with the link
    try:
        service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'},
        ).execute()
        logger.info("Public share permission set successfully")
    except Exception as e:
        logger.warning(f"Could not set public permission: {e}")

    link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    logger.info(f"Shareable link generated: {link}")
    return link
