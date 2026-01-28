import os
import cv2
import subprocess
import logging
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

        logger.info("Loading InsightFace models (ONCE)...")
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
                raise ValueError(f"Failed to load source image: {path}")

            faces = self.app.get(img)
            if not faces:
                raise ValueError(f"No face detected in source image: {path}")

            self.src_faces.append(faces[0])

        if not self.src_faces:
            raise ValueError("No valid source faces loaded")

        logger.info("Loaded %d source face(s)", len(self.src_faces))

    def run_ffmpeg(self, cmd):
        subprocess.run(cmd, check=True)


    def get_video_fps(self, video_path):
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        rate = result.stdout.strip()
        if "/" in rate:
            num, den = rate.split("/")
            return float(num) / float(den)

        return float(rate)

    def swap_video(
        self,
        input_video,
        output_video,
        work_dir="./work",
    ):
        if not self.src_faces:
            raise RuntimeError("Source faces not loaded")

        frames_dir = os.path.join(work_dir, "frames")
        out_frames_dir = os.path.join(work_dir, "frames_out")
        no_audio_video = os.path.join(work_dir, "video_noaudio.mp4")

        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(out_frames_dir, exist_ok=True)

        fps = self.get_video_fps(input_video)
        logger.info("Detected input FPS: %s", fps)

        logger.info("Extracting frames...")
        self.run_ffmpeg([
            "ffmpeg", "-y",
            "-i", input_video,
            "-vsync", "0",
            f"{frames_dir}/frame_%06d.png"
        ])

        frame_files = sorted(os.listdir(frames_dir))
        if not frame_files:
            raise RuntimeError("No frames extracted")

        logger.info("Swapping faces...")
        for i, fname in enumerate(frame_files):
            frame_path = os.path.join(frames_dir, fname)
            frame = cv2.imread(frame_path)
            if frame is None:
                continue

            faces = self.app.get(frame)

            faces = sorted(faces, key=lambda f: f.bbox[0])

            for idx, face in enumerate(faces):
                src_face = self.src_faces[idx % len(self.src_faces)]
                frame = self.swapper.get(
                    frame,
                    face,
                    src_face,
                    paste_back=True
                )

            cv2.imwrite(os.path.join(out_frames_dir, fname), frame)

            if i % 50 == 0:
                logger.debug("Processed %d/%d frames", i, len(frame_files))

        logger.info("Rebuilding video...")
        self.run_ffmpeg([
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", f"{out_frames_dir}/frame_%06d.png",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            no_audio_video
        ])

        logger.info("Merging audio...")
        self.run_ffmpeg([
            "ffmpeg", "-y",
            "-i", no_audio_video,
            "-i", input_video,
            "-map", "0:v:0",
            "-map", "1:a?",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_video
        ])

        logger.info("Video processed successfully! Output: %s", output_video)


if __name__ == "__main__":
    SWAPPER_MODEL_PATH = "models/inswapper_128.onnx"

    SOURCE_FACES = [
        "face1.jpg"
    ]

    INPUT_VIDEO = "downloads/input.mp4"
    FINAL_VIDEO = "output_video.mp4"
    WORK_DIR = "./work"

    engine = FaceSwapEngine(
        swapper_model_path=SWAPPER_MODEL_PATH,
        providers=("CUDAExecutionProvider",)
    )

    engine.load_source_faces(SOURCE_FACES)

    engine.swap_video(
        input_video=INPUT_VIDEO,
        output_video=FINAL_VIDEO,
        work_dir=WORK_DIR
    )