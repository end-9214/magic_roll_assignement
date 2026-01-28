import torch
import numpy as np
from PIL import Image
import cv2
from MODNet.src.models.modnet import MODNet


class BackgroundChanger:
    def __init__(self, ckpt_path, device="cuda"):
        self.device = device

        # Load MODNet
        self.model = MODNet(backbone_pretrained=False)
        state_dict = torch.load(ckpt_path, map_location=device)
        self.model.load_state_dict(state_dict, strict=False)

        self.model.to(device)
        self.model.eval()

        print("✅ MODNet loaded successfully")

    def replace_background(self, frame_bgr, bg_image):
        h, w = frame_bgr.shape[:2]

        # Convert BGR → RGB
        frame_rgb = frame_bgr[:, :, ::-1]

        # 🔹 Aspect-ratio preserving resize (VERY IMPORTANT)
        scale = 512 / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)

        img = Image.fromarray(frame_rgb).resize((new_w, new_h))
        img = np.array(img) / 255.0
        img = torch.from_numpy(img).permute(2, 0, 1).float().unsqueeze(0).to(self.device)

        # MODNet inference
        with torch.no_grad():
            pred = self.model(img, inference=True)

            matte = None
            if isinstance(pred, (tuple, list)):
                for item in pred:
                    if isinstance(item, torch.Tensor):
                        matte = item
                        break
            elif isinstance(pred, torch.Tensor):
                matte = pred

            if matte is None:
                raise RuntimeError("MODNet returned no valid matte tensor")

            matte = matte.squeeze().cpu().numpy()

        # Resize matte back to original size
        matte = cv2.resize(matte, (w, h))
        matte = np.clip(matte, 0, 1)

        # 🔹 Matte refinement (important for sharp subject)
        matte = cv2.erode(matte, None, iterations=1)
        matte = cv2.dilate(matte, None, iterations=1)

        # Expand to 3 channels
        matte_3c = np.repeat(matte[:, :, None], 3, axis=2)

        # 🔹 Gentle smoothing (NOT aggressive)
        matte_3c = cv2.GaussianBlur(matte_3c, (5, 5), 0)

        bg_resized = cv2.resize(bg_image, (w, h))

        # Alpha compositing
        out = frame_bgr * matte_3c + bg_resized * (1 - matte_3c)
        return out.astype(np.uint8)


# ======================================================
# High-level function: change background of a video
# ======================================================
def change_video_background(
    ckpt_path,
    input_video,
    output_video,
    bg_image_path,
    device="cpu"
):
    bg_changer = BackgroundChanger(
        ckpt_path=ckpt_path,
        device=device
    )

    bg_image = cv2.imread(bg_image_path)
    if bg_image is None:
        raise RuntimeError("Failed to load background image")

    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        raise RuntimeError("Failed to open input video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        output_video,
        fourcc,
        fps,
        (width, height)
    )

    print("🎥 Changing video background...")

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        out_frame = bg_changer.replace_background(frame, bg_image)
        writer.write(out_frame)

        frame_idx += 1
        if frame_idx % 30 == 0:
            print(f"Processed {frame_idx} frames")

    cap.release()
    writer.release()

    print("✅ Background replacement completed")
    print("📁 Output saved to:", output_video)


# ======================================================
# Example usage
# ======================================================
if __name__ == "__main__":
    CKPT_PATH = "MODNet/pretrained/modnet_photographic_portrait_matting.ckpt"
    INPUT_VIDEO = "output_video.mp4"
    OUTPUT_VIDEO = "output_bg_changed.mp4"
    BG_IMAGE_PATH = "background.jpg"

    change_video_background(
        ckpt_path=CKPT_PATH,
        input_video=INPUT_VIDEO,
        output_video=OUTPUT_VIDEO,
        bg_image_path=BG_IMAGE_PATH,
        device="cpu"  # switch to "cuda" if GPU available
    )
