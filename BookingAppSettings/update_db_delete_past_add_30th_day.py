from datetime import timedelta
from django.utils import timezone
from django.db.models import Exists, OuterRef
from .models import Salon, FixedOperatingHours, GeneratedTimeSlots

def generate_time_slots_for_next_month():
    now = timezone.now()

    # Delete all time slots that are in the past
    GeneratedTimeSlots.objects.filter(date__lt=now.date()).delete()

    # Get all salons that have any associated FixedOperatingHours
    salons_with_operating_hours = Salon.objects.filter(
        Exists(FixedOperatingHours.objects.filter(salon=OuterRef('pk')))
    )

    # Loop over these salons and generate time slots
    for salon in salons_with_operating_hours:
        for operating_hour in FixedOperatingHours.objects.filter(salon=salon):
            operating_hour.generate_time_slots(start_date=now + timedelta(days=29), end_date=now + timedelta(days=30))

    return "Time slots for the next month have been generated successfully"