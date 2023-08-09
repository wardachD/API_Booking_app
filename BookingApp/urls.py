from django.urls import path, include
from .views import SalonViewSet, CategoryViewSet, ServiceViewSet, GeneratedTimeSlotsViewSet, SalonSearchAPIView, ReviewViewSet, SalonReviews, FixedOperatingHoursViewSet, UnFixedOperatingHoursViewSet, GeneratedTimeSlotsViewSet, AppointmentViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'reviews', ReviewViewSet)
router.register(r'fixed-operating-hours', FixedOperatingHoursViewSet)
router.register(r'unfixed-operating-hours', UnFixedOperatingHoursViewSet)
router.register(r'generatedtimeslots', GeneratedTimeSlotsViewSet)
router.register(r'appointments', AppointmentViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('salons/', SalonViewSet.as_view({'get': 'list', 'post': 'create'}), name='salons-list'),
    path('salons/<int:pk>/', SalonViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='salons-detail'),
    path('search/', SalonSearchAPIView.as_view(), name='salon-search'),
    path('salons/<int:pk>/reviews/', SalonReviews.as_view(), name='salon-reviews'),
]