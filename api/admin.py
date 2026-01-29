from django.contrib import admin
from .models import OutputVideo, VideoData, FaceImage

# Register your models here.
admin.site.register(VideoData)
admin.site.register(FaceImage)
admin.site.register(OutputVideo)