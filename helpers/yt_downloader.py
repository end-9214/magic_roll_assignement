import yt_dlp
import os


def download_youtube(url, output_path="downloads"):
    os.makedirs(output_path, exist_ok=True)

    ydl_opts = {
        "outtmpl": f"{output_path}/%(title)s.%(ext)s",
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.lower().endswith(".mp4"):
            mp4_candidate = os.path.splitext(filename)[0] + ".mp4"
            if os.path.exists(mp4_candidate):
                filename = mp4_candidate
        return filename


if __name__ == "__main__":
    url = input("Enter YouTube video or Shorts URL: ")
    print(download_youtube(url))
