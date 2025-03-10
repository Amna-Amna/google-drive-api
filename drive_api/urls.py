from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('folder/<str:folder_name>/', views.folder_contents, name='folder_contents'),
    path('upload/<str:folder_name>/', views.upload_file_view, name='upload_file'),
    path('download/<str:file_id>/', views.download_file_view, name='download_file'),
    path('create-folder/', views.create_folder_view, name='create_folder'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
]