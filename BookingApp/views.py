from rest_framework.response import Response
from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.http import Http404, JsonResponse
from .models import Salon, Category, Service, Review, FixedOperatingHours, UnFixedOperatingHours, GeneratedTimeSlots, Appointment
from .serializers import SalonSerializer, ReadOnlySalonSerializer, ServiceSerializer, CategorySerializer, ReviewSerializer, FixedOperatingHoursSerializer, GeneratedTimeSlotsSerializer, UnFixedOperatingHoursSerializer, AppointmentSerializer
from .search import search_salons, search_by_keywords, search_by_address_radius

class SalonViewSet(viewsets.ModelViewSet):
    queryset = Salon.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ReadOnlySalonSerializer
        return SalonSerializer
    
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

class SalonSearchAPIView(APIView):
    def get(self, request):
        keywords = request.query_params.get('keywords', '')
        address = request.query_params.get('address', '')
        radius = request.query_params.get('radius', '')

        # Warunek sprawdzający, czy przynajmniej jeden parametr wyszukiwania jest podany
        if keywords and not address and not radius:
            salons = search_by_keywords(keywords)
        elif address and radius and not keywords:
            salons = search_by_address_radius(address, radius)
        elif keywords and address and radius:
            salons = search_salons(keywords, address, radius)
        else:
            # Jeżeli nie podano żadnego parametru, zwracamy wszystkie salony
            salons = Salon.objects.all()

        # Używamy JsonResponse, aby zwrócić dane JSON z poprawnym nagłówkiem Content-Type
        data = ReadOnlySalonSerializer(salons, many=True).data
        return JsonResponse(data, charset='utf-8', safe=False)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

class SalonReviews(APIView):
    def get_object(self, pk):
        try:
            return Salon.objects.get(pk=pk)
        except Salon.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        salon = self.get_object(pk)
        reviews = Review.objects.filter(salon=salon)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

class FixedOperatingHoursViewSet(viewsets.ModelViewSet):
    queryset = FixedOperatingHours.objects.all()
    serializer_class = FixedOperatingHoursSerializer

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):  # Check if the request is a list.
            serializer = self.get_serializer(data=request.data, many=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return super(FixedOperatingHoursViewSet, self).create(request, *args, **kwargs)


class UnFixedOperatingHoursViewSet(viewsets.ModelViewSet):
    queryset = UnFixedOperatingHours.objects.all()
    serializer_class = UnFixedOperatingHoursSerializer

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):  # Check if the request is a list.
            serializer = self.get_serializer(data=request.data, many=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return super(UnFixedOperatingHoursViewSet, self).create(request, *args, **kwargs)

class GeneratedTimeSlotsViewSet(viewsets.ModelViewSet):
    queryset = GeneratedTimeSlots.objects.all().order_by('salon', 'date', 'time_from')
    serializer_class = GeneratedTimeSlotsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['salon']
    ordering_fields = ['salon', 'date', 'time_from']

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        appointment = self.get_object()
        print(appointment)

        # Set the is_available field of each timeslot back to True
        for timeslot in appointment.timeslots.all():
            timeslot.is_available = True
            timeslot.save()

        # Call the parent class's destroy method to delete the appointment
        return super().destroy(request, *args, **kwargs)