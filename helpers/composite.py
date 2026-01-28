import cv2
import numpy as np
import subprocess
import logging
from tqdm import tqdm
from rembg import new_session, remove
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
import onnxruntime as ort

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("FaceSwapBackgroundEngine")


class FaceSwapBackgroundEngine:
    def __init__(
        self,
        swapper_model_path,
        bg_image_path=None,
        providers=None,
        det_size=(640, 640),
        rembg_model="isnet-general-use",
    ):
        if providers is None:
            available = ort.get_available_providers()
            if "CUDAExecutionProvider" in available:
                self.providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                log.info("CUDA detected, using GPU")
            else:
                self.providers = ["CPUExecutionProvider"]
                log.info("CUDA not available, using CPU")
        else:
            self.providers = list(providers)
            log.info("Using providers: %s", self.providers)

        self.background_enabled = bg_image_path is not None
        self.background_image = None

        if self.background_enabled:
            self.background_image = cv2.imread(bg_image_path)
            if self.background_image is None:
                raise RuntimeError("Unable to load background image")
            log.info("Background replacement enabled")
        else:
            log.info("Background replacement disabled")

        ctx_id = 0 if "CUDAExecutionProvider" in self.providers else -1

        log.info("Loading InsightFace models")
        self.face_app = FaceAnalysis(name="buffalo_l", providers=self.providers)
        self.face_app.prepare(ctx_id=ctx_id, det_size=det_size)

        self.face_swapper = get_model(
            swapper_model_path,
            providers=self.providers,
        )

        self.rembg_session = None
        if self.background_enabled:
            log.info("Loading background removal model")
            self.rembg_session = new_session(rembg_model)

        self.source_faces = []
        log.info("Engine initialized")

    def load_source_faces(self, image_paths):
        if isinstance(image_paths, str):
            image_paths = [image_paths]

        self.source_faces = []

        for path in image_paths:
            image = cv2.imread(path)
            if image is None:
                raise RuntimeError(f"Unable to load source image: {path}")

            detected_faces = self.face_app.get(image)
            if not detected_faces:
                raise RuntimeError(f"No face found in source image: {path}")

            self.source_faces.append(detected_faces[0])

        log.info("Loaded %d source faces", len(self.source_faces))

    def merge_audio_tracks(self, silent_video, original_video, final_video):
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                silent_video,
                "-i",
                original_video,
                "-map",
                "0:v:0",
                "-map",
                "1:a?",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                final_video,
            ],
            check=True,
        )

    def process_video(
        self,
        input_video,
        output_video,
        temp_video="temp_noaudio.mp4",
        progress_callback=None,
    ):
        if not self.source_faces:
            raise RuntimeError("Source faces not loaded")

        capture = cv2.VideoCapture(input_video)
        if not capture.isOpened():
            raise RuntimeError("Unable to open input video")

        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

        if self.background_enabled:
            resized_background = cv2.resize(
                self.background_image, (frame_width, frame_height)
            )

        writer = cv2.VideoWriter(
            temp_video,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (frame_width, frame_height),
        )

        frame_index = 0

        for _ in tqdm(range(total_frames)):
            success, frame = capture.read()
            if not success:
                break

            detected_faces = self.face_app.get(frame)
            detected_faces = sorted(detected_faces, key=lambda f: f.bbox[0])

            for idx, detected_face in enumerate(detected_faces):
                source_face = self.source_faces[idx % len(self.source_faces)]
                frame = self.face_swapper.get(
                    frame,
                    detected_face,
                    source_face,
                    paste_back=True,
                )

            if self.background_enabled:
                rgba_frame = remove(frame, session=self.rembg_session)
                alpha_mask = rgba_frame[:, :, 3].astype(np.float32) / 255.0
                alpha_mask = alpha_mask[:, :, None]
                frame = frame * alpha_mask + resized_background * (1 - alpha_mask)
                frame = frame.astype(np.uint8)

            writer.write(frame)

            frame_index += 1
            if progress_callback and total_frames > 0 and frame_index % 10 == 0:
                try:
                    percent = int((frame_index / total_frames) * 100)
                    progress_callback(percent, frame_index, total_frames)
                except Exception:
                    pass

        capture.release()
        writer.release()

        self.merge_audio_tracks(temp_video, input_video, output_video)

        if progress_callback:
            try:
                progress_callback(100, total_frames, total_frames)
            except Exception:
                pass


if __name__ == "__main__":
    MODEL_PATH = "models/inswapper_128.onnx"
    SOURCE_IMAGES = ["face1.jpg"]
    INPUT_VIDEO_PATH = "downloads/input.mp4"
    OUTPUT_VIDEO_PATH = "output_faceswap_only.mp4"

    processor = FaceSwapBackgroundEngine(
        swapper_model_path=MODEL_PATH,
        bg_image_path=None,
    )

    processor.load_source_faces(SOURCE_IMAGES)

    processor.process_video(
        input_video=INPUT_VIDEO_PATH,
        output_video=OUTPUT_VIDEO_PATH,
    )
