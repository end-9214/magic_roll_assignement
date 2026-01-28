from django.urls import path
from .views import (
    ListAllVideosView, 
    VideoUploadView, 
    OutputVideoDetailView
)

urlpatterns = [
    path("videos/", VideoUploadView.as_view(), name="video-generation"),
    path("videos/details/<int:pk>/", OutputVideoDetailView.as_view(), name="video-detail"),
    path("videos/list/", ListAllVideosView.as_view(), name="list-all-videos"),
]
