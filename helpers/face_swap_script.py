import os
import cv2
import subprocess
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

# ================== CONFIG ==================
INPUT_VIDEO = "/content/input.mp4"
SOURCE_FACE_IMG = "/content/face.avif"
WORK_DIR = "/content/work"
FRAMES_DIR = f"{WORK_DIR}/frames"
OUT_FRAMES_DIR = f"{WORK_DIR}/frames_out"

NO_AUDIO_VIDEO = "/content/video_noaudio.mp4"
FINAL_VIDEO = "/content/output_final.mp4"

FPS = 60  # match input video

# ================== SETUP ==================
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(OUT_FRAMES_DIR, exist_ok=True)

# ================== STEP 1: EXTRACT FRAMES (AV1 SAFE) ==================
print("🔹 Extracting frames using FFmpeg...")

subprocess.run([
    "ffmpeg", "-y",
    "-i", INPUT_VIDEO,
    "-vsync", "0",
    f"{FRAMES_DIR}/frame_%06d.png"
], check=True)

frame_files = sorted(os.listdir(FRAMES_DIR))
assert len(frame_files) > 0, "❌ No frames extracted"
print(f"✅ Extracted {len(frame_files)} frames")

# ================== STEP 2: LOAD MODELS ==================
print("🔹 Loading InsightFace models...")

app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

swapper = get_model(
    "/root/.insightface/models/inswapper_128.onnx",
    providers=["CUDAExecutionProvider"]
)

# ================== STEP 3: LOAD SOURCE FACE ==================
src_img = cv2.imread(SOURCE_FACE_IMG)
src_faces = app.get(src_img)
assert len(src_faces) > 0, "❌ No face found in source image"
src_face = src_faces[0]

print("✅ Source face loaded")

# ================== STEP 4: FACE SWAP ON FRAMES ==================
print("🔹 Swapping faces on frames...")

for i, fname in enumerate(frame_files):
    frame_path = os.path.join(FRAMES_DIR, fname)
    out_path = os.path.join(OUT_FRAMES_DIR, fname)

    frame = cv2.imread(frame_path)

    faces = app.get(frame)
    for face in faces:
        frame = swapper.get(frame, face, src_face, paste_back=True)

    cv2.imwrite(out_path, frame)

    if i % 50 == 0:
        print(f"Processed {i}/{len(frame_files)} frames")

print("✅ Face swapping completed")

# ================== STEP 5: BUILD VIDEO FROM FRAMES ==================
print("🔹 Building video (no audio)...")

subprocess.run([
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", f"{OUT_FRAMES_DIR}/frame_%06d.png",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    NO_AUDIO_VIDEO
], check=True)

print("✅ Video (no audio) created")

# ================== STEP 6: MERGE ORIGINAL AUDIO ==================
print("🔹 Merging original audio...")

subprocess.run([
    "ffmpeg", "-y",
    "-i", NO_AUDIO_VIDEO,
    "-i", INPUT_VIDEO,
    "-map", "0:v:0",
    "-map", "1:a?",
    "-c:v", "copy",
    "-c:a", "aac",
    "-shortest",
    FINAL_VIDEO
], check=True)

print("🎉 FINAL VIDEO READY:", FINAL_VIDEO)
