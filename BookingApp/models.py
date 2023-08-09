from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError
from django.core.validators import MinValueValidator, MaxValueValidator



class Salon(models.Model):
    ERROR_CODES = (
        (0, 'Success'),
        (1, 'Geocoding Error'),
        (2, 'Geocoding Error - Timeout'),
        (3, 'Geocoding Error - Service Unavailable'),
        (4, 'Other Geocoding Error'),
        (6, 'other'),
    )
    FLUTTER_CATEGORY_CHOICES = (
        ('hairdresser', 'Hairdresser'),
        ('nails', 'Nails'),
        ('massage', 'Massage'),
        ('barber', 'Barber'),
        ('makeup', 'Makeup'),
        ('pedicure', 'Pedicure'),
        ('manicure', 'Manicure')
    )

    name = models.CharField(max_length=100)
    address_city = models.CharField(max_length=100)
    address_postal_code = models.CharField(max_length=20)
    address_street = models.CharField(max_length=100)
    address_number = models.CharField(max_length=10)
    location = models.PointField(default=Point(0, 0), srid=4326)
    about = models.TextField(max_length=200)
    avatar = models.URLField(max_length=60, null=True, blank=True, default='')
    phone_number = models.CharField(max_length=20, default='')
    distance_from_query = models.FloatField(null=True, blank=True, default='')
    error_code = models.PositiveSmallIntegerField(choices=ERROR_CODES, default=0, blank=True)
    flutter_category = models.CharField(max_length=30, choices=FLUTTER_CATEGORY_CHOICES, default='hairdresser')

    def geocode_address(self, address):
        geolocator = Nominatim(user_agent="BookingApp")
        try:
            location = geolocator.geocode(address)
            if location:
                return location.latitude, location.longitude, 0  # Error Code 0 - Success
        except GeocoderTimedOut:
            return None, None, 2  # Error Code 2 - Geocoding Error - Timeout
        except GeocoderUnavailable:
            return None, None, 3  # Error Code 3 - Geocoding Error - Service Unavailable
        except GeocoderServiceError:
            return None, None, 4  # Error Code 4 - Other Geocoding Error
        return None, None, 1  # Error Code 1 - Geocoding Error

    def save(self, *args, **kwargs):
        if not self.pk:
            address = f"{self.address_street} {self.address_number}, {self.address_postal_code} {self.address_city}"
            longitude, latitude, error_code = self.geocode_address(address)

            if latitude is not None and longitude is not None:
                self.location = Point(longitude, latitude, srid=4326)
            else:
                error_code = 6  # Error Code 1 - Geocoding Error

            self.error_code = error_code

        super().save(*args, **kwargs)

class Category(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='categories', null=True)
    name = models.CharField(max_length=100)

class Service(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='salon_categories', null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='services', null=True)
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default='')
    duration_temp = models.DurationField(default=timedelta(minutes=30))

class Review(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='reviews')
    user_id = models.CharField(max_length=100)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=500, default='')
    image_url = models.URLField(max_length=200, null=True, blank=True, default='')  # New image_url field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

def get_default_date():
    return timezone.now().date()

class FixedOperatingHours(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    day_of_week = models.IntegerField()  # 0: Monday, 1: Tuesday, ..., 6: Sunday
    open_time = models.TimeField()
    close_time = models.TimeField()
    time_slot_length = models.IntegerField(default=20)  # Length of the time slot in minutes

    class Meta:
        unique_together = ("salon", "day_of_week")

    def generate_time_slots(self):
        delta = timedelta(minutes=self.time_slot_length)
        
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
        
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() == self.day_of_week:
                # Combine date and time to create datetime objects
                time_from = datetime.combine(current_date, self.open_time)
                time_to = datetime.combine(current_date, self.close_time)

                while time_from + delta <= time_to:
                    GeneratedTimeSlots.objects.create(
                        salon=self.salon,
                        date=current_date,
                        time_from=time_from.time(),
                        time_to=(time_from + delta).time(),
                    )
                    time_from += delta

            current_date += timedelta(days=1)

        return GeneratedTimeSlots.objects.filter(salon=self.salon).order_by('date', 'time_from')

    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Call the "real" save() method.
        self.generate_time_slots()

class UnFixedOperatingHours(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    date = models.DateField()
    open_time = models.TimeField()
    close_time = models.TimeField()
    time_slot_length = models.IntegerField(default=20)  # Length of the time slot in minutes

    class Meta:
        unique_together = ("salon", "date")
    
    def generate_time_slots(self):
        delta = timedelta(minutes=self.time_slot_length)
        
        # Combine date and time to create datetime objects
        time_from = datetime.combine(self.date, self.open_time)
        time_to = datetime.combine(self.date, self.close_time)

        while time_from + delta <= time_to:
            GeneratedTimeSlots.objects.create(
                salon=self.salon,
                date=self.date,
                time_from=time_from.time(),
                time_to=(time_from + delta).time(),
            )
            time_from += delta

        return GeneratedTimeSlots.objects.filter(salon=self.salon, date=self.date).order_by('time_from')
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Call the "real" save() method.
        self.generate_time_slots()

class GeneratedTimeSlots(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    date = models.DateField()
    time_from = models.TimeField()
    time_to = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ("salon", "date", "time_from", "time_to")
        indexes = [
            models.Index(fields=['salon'], name='salon_idx'),
        ]

class TempTimeSlots(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    date = models.DateField()
    time_from = models.TimeField()
    time_to = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ("salon", "date", "time_from", "time_to")

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('P', 'Pending'),
        ('C', 'Confirmed'),
        ('F', 'Finished'),
        ('X', 'Cancelled'),
    )

    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    customer = models.CharField(max_length=255)  # Assuming the customer is a User
    services = models.ManyToManyField(Service)
    comment = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(choices=STATUS_CHOICES, default='P', max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    timeslots = models.ManyToManyField(GeneratedTimeSlots)

class Booking(models.Model):
    appointment = models.ForeignKey(Appointment, related_name='bookings', on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("appointment", "service")


