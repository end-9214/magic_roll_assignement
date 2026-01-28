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

if "videos" not in st.session_state:
    st.session_state.videos = []

if "selected_video_id" not in st.session_state:
    st.session_state.selected_video_id = None


def fetch_videos_list():
    response = requests.get(LIST_VIDEOS_ENDPOINT)
    if response.status_code == 200:
        return response.json()
    return []


st.title("Magic Roll Assignment")
st.write("welcome to face swapper and background changer! :D")
tab1, tab2 = st.tabs(["Generate Video", "View Videos List"])

with tab1:
    st.header("Generate Video")
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

with tab2:
    st.header("Videos List")

    if st.button("Refresh Video List"):
        st.session_state.videos = fetch_videos_list()

    if st.session_state.videos:
        video_map = {
            f"ID: {v['id']} | Status: {v['status']}": v["id"]
            for v in st.session_state.videos
        }

        selected_label = st.selectbox(
            "Select a video to view details",
            options=list(video_map.keys())
        )

        st.session_state.selected_video_id = video_map[selected_label]

    if st.session_state.selected_video_id:
        detail_url = f"{BACKEND_URL}/api/videos/details/{st.session_state.selected_video_id}/"
        detail_response = requests.get(detail_url)

        if detail_response.status_code == 200:
            video = detail_response.json()

            st.subheader(f"Video Details (ID: {video['id']})")
            st.write(f"Status: {video['status']}")
            st.write(f"Progress: {video['progress']}%")
            st.write(f"Created At: {video['created_at']}")
            if video['status'] == 'completed' and video.get('final_video_url'):
                st.write(video['final_video_url'])
            elif video['status'] == 'failed':
                st.error("Video processing failed.")






        