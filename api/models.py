from django.db import models


class FaceImage(models.Model):
    image_file = models.ImageField(upload_to="face_images/")


class VideoData(models.Model):
    video_url = models.URLField(max_length=500, null=True, blank=True)
    video_file = models.FileField(upload_to="videos/", null=True, blank=True)
    face_images = models.ManyToManyField("FaceImage", related_name="images")
    background_image = models.ImageField(
        upload_to="backgrounds/", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)


class OutputVideo(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    video_data = models.ForeignKey(
        VideoData, on_delete=models.CASCADE, related_name="output_videos"
    )
    audio_extracted = models.FileField(
        upload_to="extracted_audios/", null=True, blank=True
    )
    final_video = models.FileField(upload_to="output_videos/", null=True, blank=True)
    final_video_url = models.URLField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=50, default="queued", choices=STATUS_CHOICES)
    progress = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
