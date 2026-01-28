from rest_framework import serializers
from django.core.files import File
from .models import FaceImage, VideoData, OutputVideo


class FaceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceImage
        fields = ("id", "image_file")


class OutputVideoSerializer(serializers.ModelSerializer):
    face_swapped_video = serializers.SerializerMethodField()
    background_changed_video = serializers.SerializerMethodField()
    final_video = serializers.SerializerMethodField()

    class Meta:
        model = OutputVideo
        fields = ("id", "status", "created_at", "face_swapped_video", "background_changed_video", "final_video")

    def _url(self, field):
        if not field:
            return None
        try:
            return field.url
        except Exception:
            return None

    def get_face_swapped_video(self, obj):
        return self._url(obj.face_swapped_video)

    def get_background_changed_video(self, obj):
        return self._url(obj.background_changed_video)

    def get_final_video(self, obj):
        return self._url(obj.final_video)


class VideoDataCreateSerializer(serializers.ModelSerializer):
    # accept multiple face images in a single upload (multipart form)
    face_images = serializers.ListField(child=serializers.ImageField(), write_only=True)
    background_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = VideoData
        fields = ("id", "video_file", "face_images", "background_image", "created_at")
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        face_images = validated_data.pop("face_images", [])
        background_image = validated_data.pop("background_image", None)

        video = VideoData.objects.create(video_file=validated_data["video_file"],
                                         background_image=background_image)

        saved_faces = []
        for img in face_images:
            fi = FaceImage.objects.create(image_file=img)
            saved_faces.append(fi)
            video.face_images.add(fi)

        # create an OutputVideo record in 'queued' state; files will be filled by background worker
        out = OutputVideo.objects.create(video_data=video, status="queued")

        return video


class VideoDataResponseSerializer(serializers.ModelSerializer):
    video_file = serializers.SerializerMethodField()
    background_image = serializers.SerializerMethodField()
    output_videos = OutputVideoSerializer(many=True)

    class Meta:
        model = VideoData
        fields = ("id", "video_file", "background_image", "created_at", "output_videos")

    def _url(self, field):
        if not field:
            return None
        try:
            return field.url
        except Exception:
            return None

    def get_video_file(self, obj):
        return self._url(obj.video_file)

    def get_background_image(self, obj):
        return self._url(obj.background_image)