import os
import pickle
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.contrib import messages
from django.utils.dateparse import parse_datetime
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

from .models import DriveFile, ProjectFolder
from .google_drive_service import (
    get_drive_service, list_files, upload_file, 
    download_file, create_folder, SCOPES, get_auth_url
)

def home(request):
    """Home view that displays the list of folders"""
    try:
        # Get project folders
        folders = ProjectFolder.objects.all()
        
        # Prepare context for rendering
        context = {
            'folders': folders,
        }
        return render(request, 'drive_api/home.html', context)
        
    except Exception as e:
        # If authentication is required, generate the auth URL
        if "Authentication required" in str(e):
            auth_url = get_auth_url(request)
            return render(request, 'drive_api/home.html', {
                'folders': [],
                'auth_url': auth_url
            })
        
        messages.error(request, f"Error fetching folders from Google Drive: {str(e)}")
        return render(request, 'drive_api/home.html', {'folders': []})

def folder_contents(request, folder_name):
    """View for displaying contents of a specific folder"""
    try:
        # Get Google Drive service
        service = get_drive_service()
        
        # Get the folder
        folder = get_object_or_404(ProjectFolder, name=folder_name)
        
        # Get files in the folder
        files = list_files(service, folder_id=folder.drive_id)
        
        # Prepare context for rendering
        context = {
            'folder': folder,
            'files': files,
        }
        return render(request, 'drive_api/folder_contents.html', context)
        
    except Exception as e:
        messages.error(request, f"Error fetching files from folder {folder_name}: {str(e)}")
        return redirect('home')

def upload_file_view(request, folder_name):
    """View for uploading files to a specific folder"""
    folder = get_object_or_404(ProjectFolder, name=folder_name)
    
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            uploaded_file = request.FILES['file']
            
            # Use the configured temp directory
            temp_file_path = os.path.join(settings.TEMP_UPLOAD_DIR, uploaded_file.name)
            
            try:
                # Save the file temporarily with proper error handling
                with open(temp_file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                        destination.flush()  # Ensure data is written to disk
                
                # Upload to Google Drive
                service = get_drive_service()
                file_info = upload_file(service, temp_file_path, folder.drive_id)
                
                if file_info and file_info.get('id'):
                    # Save file info to database only if upload was successful
                    DriveFile.objects.create(
                        name=file_info.get('name', ''),
                        drive_id=file_info.get('id', ''),
                        mime_type=file_info.get('mimeType', ''),
                        created_time=parse_datetime(file_info.get('createdTime')) or datetime.now(),
                        modified_time=parse_datetime(file_info.get('modifiedTime')),
                        size=int(file_info.get('size', 0)) if file_info.get('size') else None,
                        web_view_link=file_info.get('webViewLink', ''),
                        web_content_link=file_info.get('webContentLink', ''),
                        folder=folder
                    )
                    messages.success(request, f"File '{uploaded_file.name}' successfully uploaded to folder {folder.name}.")
                else:
                    raise Exception("Upload failed - no file ID received")
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError:
                        pass  # Ignore cleanup errors
            
        except Exception as e:
            messages.error(request, f"Error uploading file: {str(e)}")
        
        return redirect('home')
    
    return render(request, 'drive_api/upload.html', {'folder': folder})

def download_file_view(request, file_id):
    """View for downloading a file from Google Drive"""
    temp_file_path = None
    try:
        service = get_drive_service()
        
        # Get file metadata to get the name
        file_metadata = service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get('name', 'downloaded_file')
        
        # Use the configured temp directory
        temp_file_path = os.path.join(settings.TEMP_DOWNLOAD_DIR, file_name)
        
        # Download the file
        download_file(service, file_id, temp_file_path)
        
        # Serve the file
        response = FileResponse(open(temp_file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        # Delete the temp file after the response is sent
        response._resource_closers.append(lambda: os.remove(temp_file_path) if os.path.exists(temp_file_path) else None)
        
        return response
        
    except Exception as e:
        # Clean up temp file if something goes wrong
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        messages.error(request, f"Error downloading file: {str(e)}")
        return redirect('home')

def create_folder_view(request):
    """View for creating a folder in Google Drive"""
    if request.method == 'POST':
        try:
            folder_name = request.POST.get('folder_name')
            parent_folder_id = request.POST.get('parent_folder_id')  # Optional parent folder
            
            if folder_name:
                service = get_drive_service()
                folder = create_folder(service, folder_name, parent_folder_id)
                
                messages.success(request, f"Folder '{folder_name}' created successfully in Google Drive.")
            else:
                messages.error(request, "Folder name is required.")
                
        except Exception as e:
            messages.error(request, f"Error creating folder: {str(e)}")
            
        return redirect('home')
    
    return render(request, 'drive_api/create_folder.html')

def oauth2callback(request):
    """Handle the OAuth 2.0 callback from Google"""
    try:
        # Get the authorization code and state from the request
        code = request.GET.get('code')
        error = request.GET.get('error')
        state = request.GET.get('state')
        stored_state = request.session.pop('oauth_state', None)
        
        if error:
            messages.error(request, f"Authorization failed: {error}")
            return redirect('home')
            
        if not code:
            messages.error(request, "No authorization code received from Google.")
            return redirect('home')
        
        # Verify the state matches to prevent CSRF attacks
        if state != stored_state:
            messages.error(request, "State mismatch. Authentication failed for security reasons.")
            return redirect('home')
            
        # Create flow instance with explicit redirect URI
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
            scopes=SCOPES,
            state=state
        )
        flow.redirect_uri = "http://127.0.0.1:8000/oauth2callback"
        
        try:
            # Exchange the authorization code for credentials
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Validate credentials by making a test API call
            service = build('drive', 'v3', credentials=credentials)
            service.files().list(pageSize=1).execute()
            
            # Save credentials to token.pickle only if validation succeeds
            token_path = settings.GOOGLE_OAUTH_TOKEN_PATH
            with open(token_path, 'wb') as token:
                pickle.dump(credentials, token)
            os.chmod(token_path, 0o600)  # Set proper file permissions
                
            messages.success(request, "Successfully authenticated with Google Drive!")
            
        except Exception as e:
            messages.error(request, f"Failed to validate credentials: {str(e)}")
            # Clean up any partial token file
            if os.path.exists(settings.GOOGLE_OAUTH_TOKEN_PATH):
                os.remove(settings.GOOGLE_OAUTH_TOKEN_PATH)
            
    except Exception as e:
        messages.error(request, f"Authentication error: {str(e)}")
        # Clean up any partial token file
        if os.path.exists(settings.GOOGLE_OAUTH_TOKEN_PATH):
            os.remove(settings.GOOGLE_OAUTH_TOKEN_PATH)
        
    return redirect('home')
