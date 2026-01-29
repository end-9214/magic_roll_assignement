
from django.db import transaction
from .models import OutputVideo

def create_output_job(video_data):
    """
    Create OutputVideo job for the given VideoData instance.
    """
    with transaction.atomic():
        job = OutputVideo.objects.create(
            video_data=video_data,
            status="queued",
            progress=0,
        )
    return job
