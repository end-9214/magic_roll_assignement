from django.urls import path
from .views import VideoUploadAPIView, OutputVideoDetailAPIView

urlpatterns = [
    path("videos/", VideoUploadAPIView.as_view(), name="video-upload"),
    path("outputs/<int:pk>/", OutputVideoDetailAPIView.as_view(), name="output-detail"),
]
