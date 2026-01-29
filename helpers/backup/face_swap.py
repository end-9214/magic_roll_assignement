import cv2
import os
import subprocess
import logging
from tqdm import tqdm
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

logger = logging.getLogger(__name__)


class FaceSwapEngine:
    def __init__(
        self,
        swapper_model_path,
        providers=("CUDAExecutionProvider",),
        det_size=(640, 640),
    ):
        self.providers = list(providers)

        logger.info("Loading InsightFace models...")
        self.app = FaceAnalysis(name="buffalo_l", providers=self.providers)
        ctx_id = -1 if any("CPUExecutionProvider" in p for p in self.providers) else 0
        self.app.prepare(ctx_id=ctx_id, det_size=det_size)

        self.swapper = get_model(
            swapper_model_path,
            providers=self.providers
        )

        self.src_faces = []
        logger.info("Models loaded")

    def load_source_faces(self, source_image_paths):
        if isinstance(source_image_paths, str):
            source_image_paths = [source_image_paths]

        self.src_faces = []

        for path in source_image_paths:
            img = cv2.imread(path)
            if img is None:
                raise RuntimeError(f"Failed to load source image: {path}")

            faces = self.app.get(img)
            if not faces:
                raise RuntimeError(f"No face detected in source image: {path}")

            self.src_faces.append(faces[0])

        logger.info("Loaded %d source face(s)", len(self.src_faces))

    def merge_audio(self, video_no_audio, original_video, output_video):
        subprocess.run([
            "ffmpeg", "-y",
            "-i", video_no_audio,
            "-i", original_video,
            "-map", "0:v:0",
            "-map", "1:a?",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_video
        ], check=True)

    def swap_video(
        self,
        input_video,
        output_video,
        temp_video="temp_noaudio.mp4"
    ):
        if not self.src_faces:
            raise RuntimeError("Source faces not loaded")

        cap = cv2.VideoCapture(input_video)
        if not cap.isOpened():
            raise RuntimeError("Failed to open input video")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        writer = cv2.VideoWriter(
            temp_video,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height)
        )

        logger.info("Processing video with InsightFace face swap...")

        for _ in tqdm(range(total_frames)):
            ret, frame = cap.read()
            if not ret:
                break

            faces = self.app.get(frame)
            faces = sorted(faces, key=lambda f: f.bbox[0])

            for i, face in enumerate(faces):
                src_face = self.src_faces[i % len(self.src_faces)]
                frame = self.swapper.get(
                    frame,
                    face,
                    src_face,
                    paste_back=True
                )

            writer.write(frame)

        cap.release()
        writer.release()

        logger.info("Merging audio...")
        self.merge_audio(temp_video, input_video, output_video)


if __name__ == "__main__":
    SWAPPER_MODEL_PATH = "models/inswapper_128.onnx"

    SOURCE_FACES = [
        "face1.jpg"
    ]

    INPUT_VIDEO = "downloads/input.mp4"
    FINAL_VIDEO = "output_video.mp4"

    engine = FaceSwapEngine(
        swapper_model_path=SWAPPER_MODEL_PATH,
        providers=("CUDAExecutionProvider",)
    )

    engine.load_source_faces(SOURCE_FACES)

    engine.swap_video(
        input_video=INPUT_VIDEO,
        output_video=FINAL_VIDEO
    )
