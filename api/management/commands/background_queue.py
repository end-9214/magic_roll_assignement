import os
import time
import traceback
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from api.models import OutputVideo
from helpers.yt_downloader import download_youtube
from helpers.composite import FaceSwapBackgroundEngine


class Command(BaseCommand):
    help = "Process queued videos"

    def handle(self, *args, **options):
        project_root = getattr(settings, "BASE_DIR", os.getcwd())
        model_path = getattr(
            settings,
            "SWAPPER_MODEL_PATH",
            os.path.join(project_root, "helpers", "models", "inswapper_128.onnx"),
        )
        fallback_background = os.path.join(project_root, "helpers", "background2.jpg")

        self.stdout.write("Worker running...")

        while True:
            pending_jobs = OutputVideo.objects.filter(status="queued").order_by(
                "created_at"
            )

            if not pending_jobs.exists():
                time.sleep(3)
                continue

            for job in pending_jobs:
                try:
                    job.status = "processing"
                    job.progress = 0
                    job.save(update_fields=["status", "progress"])

                    video_data = job.video_data

                    if video_data.video_url and not video_data.video_file:
                        try:
                            downloaded_path = download_youtube(
                                video_data.video_url,
                                output_path=os.path.join(
                                    settings.MEDIA_ROOT, "downloads"
                                ),
                            )
                            if downloaded_path and os.path.exists(downloaded_path):
                                with open(downloaded_path, "rb") as f:
                                    video_data.video_file.save(
                                        os.path.basename(downloaded_path),
                                        File(f),
                                        save=True,
                                    )
                        except Exception as e:
                            job.status = "failed"
                            job.progress = 0
                            job.save(update_fields=["status", "progress"])
                            self.stderr.write(f"Download failed for job {job.id}: {e}")
                            continue

                    if not video_data.video_file or not os.path.exists(
                        video_data.video_file.path
                    ):
                        job.status = "failed"
                        job.save(update_fields=["status"])
                        self.stderr.write(f"Missing input video for job {job.id}")
                        continue

                    face_paths = [
                        face.image_file.path for face in video_data.face_images.all()
                    ]
                    if not face_paths:
                        job.status = "failed"
                        job.save(update_fields=["status"])
                        self.stderr.write(f"No face images for job {job.id}")
                        continue

                    background_path = (
                        video_data.background_image.path
                        if video_data.background_image
                        and os.path.exists(video_data.background_image.path)
                        else fallback_background
                    )

                    if not os.path.exists(background_path):
                        job.status = "failed"
                        job.save(update_fields=["status"])
                        self.stderr.write(f"Background missing for job {job.id}")
                        continue

                    processing_root = os.path.join(settings.MEDIA_ROOT, "processing")
                    os.makedirs(processing_root, exist_ok=True)

                    output_name = f"processed_{video_data.id}_{int(time.time())}.mp4"
                    temp_video_path = os.path.join(
                        processing_root, f"temp_noaudio_{job.id}.mp4"
                    )
                    final_video_path = os.path.join(processing_root, output_name)

                    engine = FaceSwapBackgroundEngine(
                        swapper_model_path=str(model_path),
                        bg_image_path=background_path,
                        providers=("CPUExecutionProvider",),
                    )

                    engine.load_source_faces(face_paths)

                    def update_progress(percent, frame_index, total_frames):
                        job.progress = max(0, min(100, percent))
                        job.save(update_fields=["progress"])

                    engine.process_video(
                        input_video=video_data.video_file.path,
                        output_video=final_video_path,
                        temp_video=temp_video_path,
                        progress_callback=update_progress,
                    )

                    if os.path.exists(final_video_path):
                        with open(final_video_path, "rb") as f:
                            job.final_video.save(output_name, File(f), save=True)

                    job.status = "completed"
                    job.progress = 100
                    job.save(update_fields=["status", "progress"])
                    self.stdout.write(f"Completed job {job.id}")

                except Exception:
                    try:
                        job.status = "failed"
                        job.save(update_fields=["status"])
                    except Exception:
                        pass
                    traceback.print_exc()

            time.sleep(1)
