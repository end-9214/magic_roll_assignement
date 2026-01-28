import cv2
import numpy as np
from rembg import new_session, remove
from tqdm import tqdm


def change_video_background_rembg(
    input_video,
    output_video,
    bg_image_path,
    model_name="isnet-general-use"
):
    bg = cv2.imread(bg_image_path)
    if bg is None:
        raise RuntimeError("Failed to load background image")

    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        raise RuntimeError("Failed to open input video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    bg = cv2.resize(bg, (width, height))

    writer = cv2.VideoWriter(
        output_video,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height)
    )

    session = new_session(model_name)

    print("Processing video with rembg (isnet-general-use)...")

    for _ in tqdm(range(total_frames)):
        ret, frame = cap.read()
        if not ret:
            break
        rgba = remove(frame, session=session)

        alpha = rgba[:, :, 3].astype(np.float32) / 255.0
        alpha = alpha[:, :, None]

        out = frame * alpha + bg * (1 - alpha)
        writer.write(out.astype(np.uint8))

    cap.release()
    writer.release()

    print("Background replacement completed")
    print("Output saved to:", output_video)


if __name__ == "__main__":
    change_video_background_rembg(
        input_video="downloads/input.mp4",
        output_video="output_bg_changed.mp4",
        bg_image_path="background2.jpg",
        model_name="isnet-general-use"
    )
