import os
import shutil
import tempfile
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from api.models import OutputVideo
from helpers.face_swap import FaceSwapEngine


class Command(BaseCommand):
    help = "Long-running worker: process queued videos (run in background/terminal)"

    def handle(self, *args, **options):
        model_path = getattr(settings, "SWAPPER_MODEL_PATH", None)
        if not model_path:
            base = getattr(settings, "BASE_DIR", os.getcwd())
            model_path = os.path.join(base, "models", "inswapper_128.onnx")

        # initialize engine once
        try:
            self.stdout.write("Initializing face-swap engine...")
            engine = FaceSwapEngine(swapper_model_path=model_path, providers=("CPUExecutionProvider",))
        except Exception as e:
            self.stderr.write(f"Failed to initialize engine: {e}")
            return

        self.stdout.write("Worker started, polling for queued videos...")
        while True:
            qs = OutputVideo.objects.filter(status="queued").order_by("created_at")
            if not qs.exists():
                time.sleep(5)
                continue

            for ov in qs:
                ov.status = "processing"
                ov.save()
                vd = ov.video_data

                work_dir = tempfile.mkdtemp(prefix=f"proc_{ov.id}_")
                try:
                    input_video_path = vd.video_file.path
                    source_face_paths = [f.image_file.path for f in vd.face_images.all()]

                    # load source faces for this job (fast compared to model load)
                    engine.load_source_faces(source_face_paths)

                    final_path = os.path.join(work_dir, f"output_{ov.id}.mp4")
                    engine.swap_video(input_video=input_video_path, output_video=final_path, work_dir=work_dir)

                    with open(final_path, "rb") as f:
                        django_file = File(f)
                        ov.final_video.save(os.path.basename(final_path), django_file, save=False)

                    ov.status = "completed"
                    ov.save()
                    self.stdout.write(f"Processed OutputVideo id={ov.id}")

                except Exception as e:
                    ov.status = "failed"
                    ov.save()
                    self.stderr.write(f"Failed id={ov.id}: {e}")

                finally:
                    try:
                        shutil.rmtree(work_dir)
                    except Exception:
                        pass