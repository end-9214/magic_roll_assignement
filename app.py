import streamlit as st
from dotenv import load_dotenv
import os
import requests
load_dotenv()

video_id = None

BACKEND_URL = os.getenv("BACKEND_URL")
VIDEO_GENERATION_ENDPOINT = f"{BACKEND_URL}/api/videos/"
LIST_VIDEOS_ENDPOINT = f"{BACKEND_URL}/api/videos/list/"
DETAIL_VIDEO_ENDPOINT = f"{BACKEND_URL}/api/videos/details/{video_id}/"


def fetch_videos_list():
    list_response = requests.get(LIST_VIDEOS_ENDPOINT)
    if list_response.status_code == 200:
        videos = list_response.json()
        for video in videos:
            st.subheader(f"Video ID: {video['id']}")
            st.write(f"Created At: {video['created_at']}")
            st.write(f"Video URL: {video['final_video_url'] or 'N/A'}")
            st.write(f"Status: {video['status']}")
            st.write(f"Progress: {video['progress']}%")

st.title("Magic Roll Assignment")
st.write("welcome to face swapper and background changer! :D")

youtube_link = st.text_input("Enter YouTube Video Link:")
face_images = st.file_uploader("Upload Face Images:", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
bg_image = st.file_uploader("Upload Background Image:", type=["png", "jpg", "jpeg"])

if st.button("Process Video"):
    if not youtube_link or not face_images:
        st.error("Please provide either a YouTube link and a face image.")
    else:
        files = []
        for img in face_images:
            filename = img.name
            file_bytes = img.read()
            content_type = img.type
            files.append(
                ('face_images', (filename, file_bytes, content_type))
            )

        data = {'video_url': youtube_link}
        if bg_image:
            files.append(
                ('background_image', (bg_image.name, bg_image.read(), bg_image.type))
            )
        response = requests.post(VIDEO_GENERATION_ENDPOINT, data=data, files=files)
        if response.status_code == 201:
            st.success("Video processing started successfully!")
            video_id = response.json().get("id")

            if video_id != None:
                st.write(f"Video ID: {video_id}")

            else:
                st.error("Failed to retrieve video ID.")

            # st.write(response.json())
        else:
            st.error("Failed to start video processing.")

if st.button("Refresh Video List"):
    fetch_videos_list()

        