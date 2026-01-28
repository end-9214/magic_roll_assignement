import yt_dlp
import os

def download_youtube(url, output_path="downloads"):
    os.makedirs(output_path, exist_ok=True)

    ydl_opts = {
        "outtmpl": f"{output_path}/%(title)s.%(ext)s",
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4"
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

if __name__ == "__main__":
    url = input("Enter YouTube video or Shorts URL: ")
    download_youtube(url)
