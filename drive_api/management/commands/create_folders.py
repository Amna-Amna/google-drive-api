from django.core.management.base import BaseCommand
from django.conf import settings
from drive_api.models import ProjectFolder
from drive_api.google_drive_service import get_drive_service, create_folder

class Command(BaseCommand):
    help = 'Creates the project folders (A through I) in Google Drive if they do not exist'

    def handle(self, *args, **options):
        try:
            # Get Google Drive service
            service = get_drive_service()
            
            # Get existing folders
            existing_folders = ProjectFolder.objects.all()
            existing_folder_names = {folder.name for folder in existing_folders}
            
            # Create missing folders
            for folder_name, _ in ProjectFolder.FOLDER_CHOICES:
                if folder_name not in existing_folder_names:
                    self.stdout.write(f"Creating folder {folder_name}...")
                    folder = create_folder(service, folder_name)
                    ProjectFolder.objects.create(
                        name=folder_name,
                        drive_id=folder['id']
                    )
                    self.stdout.write(self.style.SUCCESS(f"Successfully created folder {folder_name}"))
                else:
                    self.stdout.write(f"Folder {folder_name} already exists")
            
            self.stdout.write(self.style.SUCCESS("All project folders are ready"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating folders: {str(e)}")) 