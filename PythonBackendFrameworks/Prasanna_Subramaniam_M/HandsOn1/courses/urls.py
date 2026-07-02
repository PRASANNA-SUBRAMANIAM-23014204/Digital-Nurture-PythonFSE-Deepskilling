from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CourseViewSet, hello_view

router = DefaultRouter()
router.register(r'courses', CourseViewSet)

urlpatterns = [
    path("hello/", hello_view),
    path("", include(router.urls)),
]