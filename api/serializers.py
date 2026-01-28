from rest_framework import serializers
from .models import FaceImage, VideoData, OutputVideo

from .utils import safe_file_url


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
        fields = (
            "id",
            "status",
            "progress",
            "created_at",
            "face_swapped_video",
            "background_changed_video",
            "final_video",
        )

    def get_face_swapped_video(self, obj):
        return safe_file_url(obj.face_swapped_video)

    def get_background_changed_video(self, obj):
        return safe_file_url(obj.background_changed_video)

    def get_final_video(self, obj):
        return safe_file_url(obj.final_video)


class VideoDataCreateSerializer(serializers.ModelSerializer):
    face_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
    )
    background_image = serializers.ImageField(required=False, allow_null=True)
    video_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = VideoData
        fields = (
            "id",
            "video_file",
            "video_url",
            "face_images",
            "background_image",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        face_images = validated_data.pop("face_images", [])
        background_image = validated_data.pop("background_image", None)
        video_url = validated_data.pop("video_url", None)
        video_file = validated_data.get("video_file")

        video = VideoData.objects.create(
            video_file=video_file,
            video_url=video_url,
            background_image=background_image,
        )

        for image in face_images:
            face = FaceImage.objects.create(image_file=image)
            video.face_images.add(face)

        OutputVideo.objects.create(
            video_data=video,
            status="queued",
            progress=0,
        )

        return video


class VideoDataResponseSerializer(serializers.ModelSerializer):
    video_file = serializers.SerializerMethodField()
    background_image = serializers.SerializerMethodField()
    output_videos = OutputVideoSerializer(many=True)

    class Meta:
        model = VideoData
        fields = (
            "id",
            "video_file",
            "video_url",
            "background_image",
            "created_at",
            "output_videos",
        )

    def get_video_file(self, obj):
        return safe_file_url(obj.video_file)

    def get_background_image(self, obj):
        return safe_file_url(obj.background_image)
