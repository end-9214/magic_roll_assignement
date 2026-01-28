from django.urls import path
from .views import (
    ListAllVideosView, 
    VideoUploadView, 
    OutputVideoDetailView
)

urlpatterns = [
    path("videos/", VideoUploadView.as_view(), name="video-upload"),
    path("outputs/<int:pk>/", OutputVideoDetailView.as_view(), name="output-detail"),
    path("outputs/", ListAllVideosView.as_view(), name="list-all-videos"),
]
