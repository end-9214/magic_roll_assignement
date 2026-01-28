import os
import cv2
import subprocess
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model


class FaceSwapEngine:
    def __init__(
        self,
        swapper_model_path,
        providers=("CUDAExecutionProvider",),
        det_size=(640, 640),
    ):
        self.providers = list(providers)

        print("🔹 Loading InsightFace models (ONCE)...")
        self.app = FaceAnalysis(name="buffalo_l", providers=self.providers)
        self.app.prepare(ctx_id=0, det_size=det_size)

        self.swapper = get_model(
            swapper_model_path,
            providers=self.providers
        )

        self.src_faces = []
        print("✅ Models loaded")

    # --------------------------------------------------
    # Load ONE or MULTIPLE source face images
    # --------------------------------------------------
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

        print(f"✅ Loaded {len(self.src_faces)} source face(s)")

    # --------------------------------------------------
    def _run_ffmpeg(self, cmd):
        subprocess.run(cmd, check=True)

    # --------------------------------------------------
    def swap_video(
        self,
        input_video,
        output_video,
        work_dir="./work",
        fps=60
    ):
        if not self.src_faces:
            raise RuntimeError("Source faces not loaded")

        frames_dir = os.path.join(work_dir, "frames")
        out_frames_dir = os.path.join(work_dir, "frames_out")
        no_audio_video = os.path.join(work_dir, "video_noaudio.mp4")

        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(out_frames_dir, exist_ok=True)

        # 1️⃣ Extract frames
        print("🎬 Extracting frames...")
        self._run_ffmpeg([
            "ffmpeg", "-y",
            "-i", input_video,
            "-vsync", "0",
            f"{frames_dir}/frame_%06d.png"
        ])

        frame_files = sorted(os.listdir(frames_dir))
        if not frame_files:
            raise RuntimeError("No frames extracted")

        # 2️⃣ Face swap per frame
        print("🔁 Swapping faces...")
        for i, fname in enumerate(frame_files):
            frame_path = os.path.join(frames_dir, fname)
            frame = cv2.imread(frame_path)
            if frame is None:
                continue

            faces = self.app.get(frame)

            # Sort faces left → right for temporal consistency
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
                print(f"Processed {i}/{len(frame_files)} frames")

        # 3️⃣ Rebuild video (no audio)
        print("🎞 Rebuilding video...")
        self._run_ffmpeg([
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", f"{out_frames_dir}/frame_%06d.png",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            no_audio_video
        ])

        # 4️⃣ Merge original audio
        print("🔊 Merging audio...")
        self._run_ffmpeg([
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

        print("🎉 Video processed successfully!")
        print("📁 Output:", output_video)


# ======================================================
# Example usage
# ======================================================
if __name__ == "__main__":
    SWAPPER_MODEL_PATH = "models/inswapper_128.onnx"

    # One face → everyone
    # SOURCE_FACES = ["face1.jpg"]

    # Multiple faces → multiple people
    SOURCE_FACES = [
        "face1.jpg"
    ]

    INPUT_VIDEO = "downloads/input.mp4"
    FINAL_VIDEO = "output_video.mp4"
    WORK_DIR = "./work"
    FPS = 60

    engine = FaceSwapEngine(
        swapper_model_path=SWAPPER_MODEL_PATH,
        providers=("CUDAExecutionProvider",)
    )

    engine.load_source_faces(SOURCE_FACES)

    engine.swap_video(
        input_video=INPUT_VIDEO,
        output_video=FINAL_VIDEO,
        work_dir=WORK_DIR,
        fps=FPS
    )
