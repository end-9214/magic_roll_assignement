# AI Transform Videos
An end-to-end  video content automation pipeline that takes viral videos as input, 
transforms them using AI (face/background replacement), and prepares them for publishing.

* I have tested this on Python 3.11

## Steps to get started -
### 1. create a new python environment 
```
python -m venv venv
venv/Scripts/activate
```
### 2. Setup the `.env` 
```
CLOUDFLARE_PUBLIC_URL = 
CLOUDFLARE_ACCOUNT_ID =  
CLOUDFLARE_BUCKET_NAME =
CLOUDFLARE_CLIENT_ACCESS_KEY = 
CLOUDFLARE_CLIENT_SECRET = 
BACKEND_URL=http://localhost:8000
```

### 3. Install all the requirements
```
pip install -r requirements.txt
```

### 4. Download the inswapper model
>> this inswapper model is to be saved in `/helpers/models/inswapper_128.onnx`

```powershell
cd helpers
Invoke-WebRequest `
  https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx `
  -OutFile models\inswapper_128.onnx
```

### 5. Migrate and start django backend
```
python manage.py migrate
python manage.py runserver
```
* now in separate terminal start our background queue
```
python manage.py background_queue
```

> you can import the postman collection into postman to start directly using the endpoints. or integrate them else where.

### 6. start the streamlit app and start transforming videos :D
```
streamlit run app.py
```


* Note : FFmpeg should be already installed, And if you want to use CUDA for processing make sure `onnxruntime-gpu` is intalled.


## My approach -

### 1. Youtube Video downloader
1. Takes a YT video link.
2. Uses `yt-dlp` to download the video.
> reference : `https://www.bing.com/videos/riverview/relatedvideo?q=yt+dlp+python+tutorial&&mid=4C91EA38076ADE46C4C04C91EA38076ADE46C4C0&FORM=VAMGZC`

### 2. AI part - Face Swapping and Background changing
1.  we first give our video, Face images, and background(optional)
2. we load the face detector, we have used Insightface -  FaceAnalysis `buffalo_l` model ; it finds faces in the image and gives us (face location, face size, face angle).
3. we load the face swapper model - here we have used insightface - `inswapper_128.onnx` model what it does is it takes the detected face and a source image and replaces the source image with the detected face and it keeps the expressions and angle.
4. now we load the background removal model - here we have used rembg's `isnet-general-use` model; what it does is - it separates a foreground person from the background and then changes the background with transparent. I previously used it in Professional Photoshoot of products at artizence and thought we can also use it here and it was quite okay.
5. Now is the main loop part -
   * we first detect the fame rate of the video so that its accurate for us to read how fast the video is. this is because if we set a default fps the video will look slow or might get faster. we also detect width and height so that every frame is of same size and height. and our video writer needs these for creating a valid video file and avoiding stretching and broken frames.And we counted total frames so that we can manage loop, show percentage and know when the video ends.
   * now we read the first frame of the video using `CV2` -> we let our `buffalo_1` model to detect faces in that frame, it detects where the face is, its angle and facial landmarks. Now for each detected face we take a source file (face image) and matches the face angle, expression, pose and size. Now face swapping is done using `inswapper_128` model. we move to background removal - `isnet-general-use` model detects foreground and background and we remove the background and transparent background is created. Now we add a new background to that frame - we use numpy and opencv for this - we resize the background image to the video size and then foreground person is placed on the background. 
   * Now after the above process we save the frame and this frame is written into a new file. using opencv Videowriter. and in this video theres no audio yet because open cv only handle video and not audio. audio is ignored during frame processing. 
   * we move to the next frame and this same loop is repeated till the last frame.
   * now when every frame is processed successfully - we use `ffmpeg` to restore the audio - we extract the audio from the original video and merge it into the processed audio. 
   * Our final video is completed.


### 3. Backend part
1. we created necessary models to store video data, face image and output video data in the database.
2. we created necessary nested serializers and Views and we made minimal views only for parsing the requests and we made the main logic in serializers - for creation logic like overriding the create() to pop fields and create Video data, creating face image instances and linking them, creating the initial output also. We also created helper functions to return final video file URL.
3. We created a django management command that will run continously and process the outputvideo jobs in the database. we first poll the OutputVideo objects to get the objects with status == "queued" (oldest first) and for each job we change status to "processing", prepare inputs like face images, video file, background image and run the transformation engine (includes both face swap and background changer) and save results and these saved results in the end are uploaded to cloudflare and its public url is saved in the database.


### 4. Streamlit app -
1. We created two tabs one for creating transformation videos - POST request
2. 2nd tab is for showing results and past jobs too.

### 5. Backup 
> i created separate use cases of the face swapper and background changer for testing and saved them in the backup folder.

### 6. Trade offs 
* `inswapper_128.onnx` does fully model these things like ears, hair and sometimes it even overlays the face over hands and any objects that comes infront of the face.
* `isnet` its great for single images, but in videos its causing edge flicker. 

### 7. How close you think your output is to being indistinguishable from a real, unedited video?
* right now it looks 100% edited as for background changer i have just used an image and images are static.
* but if i got more time i could use videos for backgrounds as that might just be one short process of reading the backgrund video also frame by frame and overlaying the foreground frame on that background frame and if background video is short we loop it again and if its long we trim it to match the forground video.

### 8. Architecture -
![Architecture Diagram](/architecture/archi.PNG)



### references
1. for craeting django commands - https://www.geeksforgeeks.org/python/custom-django-management-commands/
2. For using Swapper i used references from this repo - https://github.com/haofanwang/inswapper/blob/main/swapper.py
3. I had already used rembg for photos and used references from this - https://github.com/danielgatis/rembg
4. this also comes in handy - https://dev.to/soldatov-ss/part-1-django-rest-framework-when-and-when-not-to-override-serializers-and-viewsets-11a7
