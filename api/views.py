from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser


from .serializers import (
    VideoDataCreateSerializer,
    VideoDataResponseSerializer,
    OutputVideoSerializer,
)
from .models import OutputVideo
from .services import create_output_job


class VideoUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = VideoDataCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        video = serializer.save()
        create_output_job(video)
        resp = VideoDataResponseSerializer(video, context={"request": request})
        return Response(resp.data, status=status.HTTP_201_CREATED)


class OutputVideoDetailView(APIView):
    def get(self, request, pk):
        obj = OutputVideo.objects.filter(pk=pk).first()
        if not obj:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OutputVideoSerializer(obj, context={"request": request})
        return Response(serializer.data)


class ListAllVideosView(APIView):
    def get(self, request):
        videos = OutputVideo.objects.all().order_by("-created_at")
        serializer = OutputVideoSerializer(videos, many=True, context={"request": request})
        return Response(serializer.data)