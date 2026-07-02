from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Course, Enrollment
from .serializers import CourseSerializer, EnrollmentSerializer


def hello_view(request):
    return HttpResponse("Course Management API is running")


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    @action(detail=True, methods=["get"])
    def students(self, request, pk=None):
        enrollments = Enrollment.objects.filter(course=pk)
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)