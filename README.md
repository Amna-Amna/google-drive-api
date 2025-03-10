# Google Drive API Project

A Django application that integrates with Google Drive API to manage files in specific folders.

## Features

- Automatic creation of folders A through I
- File upload to specific folders
- File download from Google Drive
- Google Drive authentication
- File listing by folder

## Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Drive API enabled
- Google OAuth 2.0 credentials

## Setup

1. Clone the repository:
```bash
git clone https://github.com/Amna-Amna/google-drive-api.git
cd google-drive-api
```

2. Create and activate a virtual environment:
```bash
python -m venv env
# On Windows
env\Scripts\activate
# On Unix or MacOS
source env/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
- Copy `.env.example` to `.env`
- Update the values in `.env` with your configuration

5. Set up Google Drive API:
- Go to Google Cloud Console
- Create a new project or select an existing one
- Enable the Google Drive API
- Create OAuth 2.0 credentials
- Download the credentials and save as `credentials.json` in the project root

6. Run migrations:
```bash
python manage.py migrate
```

7. Create project folders:
```bash
python manage.py create_folders
```

8. Run the development server:
```bash
python manage.py runserver
```

9. Visit http://127.0.0.1:8000/ in your browser

## Usage

1. When you first visit the site, you'll need to authenticate with Google Drive
2. After authentication, you'll see the folders A through I
3. Each folder has an "Upload File" button
4. Click the button to upload files to that specific folder
5. Files can be downloaded or opened directly in Google Drive

## Project Structure

- `drive_api/`: Main application directory
  - `management/commands/`: Custom management commands
  - `models.py`: Database models
  - `views.py`: View functions
  - `urls.py`: URL routing
  - `google_drive_service.py`: Google Drive API integration

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 