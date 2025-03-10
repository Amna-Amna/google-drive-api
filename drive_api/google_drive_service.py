import os
import pickle
import json
import io
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from django.conf import settings
from django.urls import reverse
from requests_oauthlib.oauth2_session import OAuth2Session
import mimetypes

# Define the scopes for Google Drive API
# If modifying these scopes, delete the token.pickle file
SCOPES = [
    'https://www.googleapis.com/auth/drive.file'  # Only access to files created or opened by the app
]

def get_drive_service():
    """
    Creates and returns a Google Drive API service instance using a user-based OAuth flow.
    Stores and reuses token info in token.pickle, so users only log in once until token expires.
    """
    creds = None
    token_path = os.path.join(settings.BASE_DIR, 'token.pickle')

    try:
        # 1. Try loading existing credentials from token.pickle
        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            except (pickle.UnpicklingError, EOFError, ValueError) as e:
                os.remove(token_path)
                raise Exception("Authentication required. Token file was corrupted.")

        # 2. If no valid creds, do the user-auth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    # Refresh the existing token
                    creds.refresh(Request())
                except Exception as e:
                    # If refresh fails, delete token and force re-authentication
                    os.remove(token_path)
                    raise Exception("Authentication required. Token refresh failed.")
            else:
                raise Exception("Authentication required. Please visit the home page to authenticate.")

            # 3. Save the new credentials for future use
            try:
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                # If we can't save the token, still continue with the current credentials
                pass

        # 4. Build and return the Drive API service
        try:
            service = build('drive', 'v3', credentials=creds)
            # Test the connection
            service.files().list(pageSize=1).execute()
            return service
        except Exception as e:
            # If service creation or test fails, force re-authentication
            if os.path.exists(token_path):
                os.remove(token_path)
            raise Exception("Authentication required. Failed to create Drive service.")

    except Exception as e:
        # Clean up token file if anything goes wrong
        if os.path.exists(token_path):
            try:
                os.remove(token_path)
            except OSError:
                pass
        raise e

def get_auth_url(request):
    """
    Create and return the authorization URL for Google OAuth
    """
    try:
        # Load client secrets
        credentials_path = settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON
        
        # Create the flow with explicit redirect URI matching Google Cloud Console
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path,
            scopes=SCOPES,
            redirect_uri="http://127.0.0.1:8000/oauth2callback"
        )
        
        # Generate the authorization URL with additional parameters for test users
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',  # Forces re-consent to ensure refresh token
            # Additional parameters for test users
            login_hint=request.GET.get('email'),  # Pre-fill email if provided
        )
        
        # Store the state in the session
        request.session['oauth_state'] = state
        
        return auth_url
    except Exception as e:
        raise Exception(f"Failed to generate auth URL. If you're a test user, make sure you're added to the OAuth consent screen: {str(e)}")

def list_files(service, page_size=10, folder_id=None):
    """
    Lists files in Google Drive.
    Args:
        service: The Google Drive service instance
        page_size: Maximum number of files to return
        folder_id: Optional ID of the folder to list files from
    """
    try:
        query = f"'{folder_id}' in parents" if folder_id else None
        results = service.files().list(
            pageSize=page_size,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size)",
            orderBy="modifiedTime desc",
            q=query
        ).execute()
        return results.get('files', [])
    except Exception as e:
        raise Exception(f"Error listing files: {str(e)}")

def upload_file(service, file_path, folder_id=None):
    """
    Uploads a file to Google Drive.
    """
    try:
        file_name = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(file_path)[0]
        if mime_type is None:
            mime_type = 'application/octet-stream'

        file_metadata = {
            'name': file_name,
            'mimeType': mime_type
        }
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # Create MediaFileUpload instance with proper mimetype and chunking
        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True,
            chunksize=1024*1024  # 1MB chunks
        )

        # Create the file with metadata
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,mimeType,createdTime,modifiedTime,size,webContentLink,webViewLink'
        )

        # Execute the upload with progress handling
        response = None
        while response is None:
            status, response = file.next_chunk()

        return response

    except Exception as e:
        raise Exception(f"Error uploading file: {str(e)}")

def download_file(service, file_id, output_path=None):
    """
    Downloads a file from Google Drive.
    If output_path is None, returns file content as bytes.
    """
    try:
        # Get file metadata first
        file_metadata = service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get('name', 'downloaded_file')

        request = service.files().get_media(fileId=file_id)
        
        if not output_path:
            # Return as in-memory bytes
            fh = io.BytesIO()
        else:
            # Ensure the output directory exists
            if os.path.isdir(output_path):
                output_path = os.path.join(output_path, file_name)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fh = io.FileIO(output_path, mode='wb')

        # Download the file in chunks
        downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)
        done = False
        while not done:
            try:
                status, done = downloader.next_chunk()
            except Exception as e:
                if not output_path:
                    fh.close()
                raise Exception(f"Error during download: {str(e)}")

        if not output_path:
            content = fh.getvalue()
            fh.close()
            return content
        else:
            fh.close()
            return output_path

    except Exception as e:
        raise Exception(f"Error downloading file: {str(e)}")

def create_folder(service, folder_name, parent_folder_id=None):
    """
    Creates a folder in Google Drive.
    """
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_folder_id:
        file_metadata['parents'] = [parent_folder_id]

    folder = service.files().create(
        body=file_metadata,
        fields='id,name,mimeType,createdTime,webViewLink'
    ).execute()
    return folder
