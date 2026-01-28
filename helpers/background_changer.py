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

        # BGR → RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # 🔹 High-resolution inference
        ref_size = 1024
        scale = ref_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)

        img = Image.fromarray(frame_rgb).resize((new_w, new_h), Image.BICUBIC)
        img = np.array(img).astype(np.float32) / 255.0

        # Normalize for MODNet
        img = (img - 0.5) / 0.5

        img = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(self.device)

        # MODNet inference
        with torch.no_grad():
            pred = self.model(img, inference=True)

            # ✅ Correct matte extraction
            if isinstance(pred, (tuple, list)):
                matte = pred[-1]   # (semantic, detail, matte)
            elif isinstance(pred, torch.Tensor):
                matte = pred
            else:
                raise RuntimeError(f"Unexpected MODNet output type: {type(pred)}")

            if matte is None or not isinstance(matte, torch.Tensor):
                raise RuntimeError("MODNet did not return a valid matte tensor")

            matte = matte.squeeze().cpu().numpy()

        # Resize matte back to original frame size
        matte = cv2.resize(matte, (w, h), interpolation=cv2.INTER_LINEAR)
        matte = np.clip(matte, 0, 1)

        # =====================================================
        # 🔥 CRITICAL FIX: Matte confidence boost
        # Removes transparency / ghosting
        # =====================================================
        matte = np.power(matte, 0.5)   # boost foreground confidence

        # Strengthen solid foreground, keep soft edges
        fg_mask = matte > 0.15
        matte[fg_mask] = np.minimum(1.0, matte[fg_mask] * 1.3)

        # Expand to 3 channels
        matte_3c = matte[:, :, None]

        bg_resized = cv2.resize(bg_image, (w, h))

        # Alpha compositing
        out = frame_bgr * matte_3c + bg_resized * (1 - matte_3c)

        return out.astype(np.uint8)


def change_video_background(
    ckpt_path,
    input_video,
    output_video,
    bg_image_path,
    device="cpu"
):
    bg_changer = BackgroundChanger(ckpt_path, device)

    bg_image = cv2.imread(bg_image_path)
    if bg_image is None:
        raise RuntimeError("Failed to load background image")

    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        raise RuntimeError("Failed to open input video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = cv2.VideoWriter(
        output_video,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
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


if __name__ == "__main__":
    change_video_background(
        ckpt_path="MODNet/pretrained/modnet_photographic_portrait_matting.ckpt",
        input_video="output_video.mp4",
        output_video="output_bg_changed.mp4",
        bg_image_path="background.jpg",
        device="cpu"  # change to "cuda" if available
    )
