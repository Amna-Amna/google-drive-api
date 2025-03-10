from django.db import models

class ProjectFolder(models.Model):
    """
    Model to track the main project folders (A through I)
    """
    FOLDER_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
        ('F', 'F'),
        ('G', 'G'),
        ('H', 'H'),
        ('I', 'I'),
    ]
    
    name = models.CharField(max_length=1, choices=FOLDER_CHOICES, unique=True)
    drive_id = models.CharField(max_length=100, unique=True)
    created_time = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Folder {self.name}"
    
    class Meta:
        ordering = ['name']

class DriveFile(models.Model):
    """
    Model to track files uploaded to or downloaded from Google Drive
    """
    name = models.CharField(max_length=255)
    drive_id = models.CharField(max_length=100, unique=True)
    mime_type = models.CharField(max_length=100)
    created_time = models.DateTimeField()
    modified_time = models.DateTimeField(null=True, blank=True)
    size = models.BigIntegerField(null=True, blank=True)  # Size in bytes
    web_view_link = models.URLField(max_length=500, null=True, blank=True)
    web_content_link = models.URLField(max_length=500, null=True, blank=True)
    folder = models.ForeignKey(ProjectFolder, on_delete=models.CASCADE, related_name='files', null=True, blank=True)
    
    def __str__(self):
        return self.name
        
    class Meta:
        ordering = ['-modified_time']
