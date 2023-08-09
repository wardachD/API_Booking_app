from datetime import timedelta
from rest_framework import serializers
from .models import Salon, Category, Service, Review, GeneratedTimeSlots, FixedOperatingHours, UnFixedOperatingHours, Appointment

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ('id', 'salon', 'category', 'title', 'description', 'price', 'duration_minutes')

class CategorySerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, required=False)

    class Meta:
        model = Category
        fields = ('id', 'salon', 'name', 'services')

    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        category_instance = Category.objects.create(**validated_data)

        for service_data in services_data:
            Service.objects.create(category=category_instance, **service_data)

        return category_instance

class SalonSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, required=False)

    class Meta:
        model = Salon
        fields = ('id', 'name', 'address_city', 'address_postal_code', 'address_street', 'address_number', 'location',
                  'about', 'avatar', 'phone_number', 'distance_from_query', 'error_code', 'flutter_category', 'categories')

    def create(self, validated_data):
        categories_data = validated_data.pop('categories', [])
        salon = Salon.objects.create(**validated_data)

        for category_data in categories_data:
            services_data = category_data.pop('services', [])
            category = Category.objects.create(salon=salon, **category_data)

            for service_data in services_data:
                Service.objects.create(salon=salon, category=category, **service_data)

        return salon
    # ... reszta kodu (funkcja update itp.)


    def update(self, instance, validated_data):
        categories_data = validated_data.pop('categories', [])  # Default to empty list if 'categories' is missing
        instance.name = validated_data.get('name', instance.name)
        instance.address_city = validated_data.get('address_city', instance.address_city)
        instance.address_postal_code = validated_data.get('address_postal_code', instance.address_postal_code)
        instance.address_street = validated_data.get('address_street', instance.address_street)
        instance.address_number = validated_data.get('address_number', instance.address_number)
        instance.location = validated_data.get('location', instance.location)
        instance.about = validated_data.get('about', instance.about)
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.distance_from_query = validated_data.get('distance_from_query', instance.distance_from_query)
        instance.error_code = validated_data.get('error_code', instance.error_code)
        instance.flutter_category = validated_data.get('flutter_category', instance.flutter_category)
        instance.save()

        for category_data in categories_data:
            category_id = category_data.get('id', None)
            if category_id is None:
                services_data = category_data.pop('services', [])  # Default to empty list if 'services' is missing
                salon_instance = instance
                category = Category.objects.create(salon=salon_instance, **category_data)

                for service_data in services_data:
                    Service.objects.create(salon=instance, category=category, **service_data)
            else:
                try:
                    category = Category.objects.get(id=category_id, salon=instance)
                except Category.DoesNotExist:
                    continue

                category.name = category_data.get('name', category.name)
                category.save()

                for service_data in category_data.get('services', []):
                    service_id = service_data.get('id', None)
                    if service_id is None:
                        Service.objects.create(salon=instance, category=category, **service_data)
                    else:
                        try:
                            service = Service.objects.get(id=service_id, category=category)
                        except Service.DoesNotExist:
                            continue

                        service.title = service_data.get('title', service.title)
                        service.description = service_data.get('description', service.description)
                        service.price = service_data.get('price', service.price)
                        service.duration_minutes = service_data.get('duration_minutes', service.duration_minutes)
                        service.save()

        return instance

class ReadOnlySalonSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    class Meta:
        model = Salon
        fields = ('id','name', 'address_city', 'address_postal_code', 'address_street', 'address_number', 'location',
                  'about','avatar', 'phone_number', 'distance_from_query', 'error_code', 'flutter_category', 'categories')

    def create(self, validated_data):
        categories_data = validated_data.pop('categories')
        salon = Salon.objects.create(**validated_data)

        for category_data in categories_data:
            services_data = category_data.pop('services')
            category = Category.objects.create(salon=salon, **category_data)

            for service_data in services_data:
                Service.objects.create(salon=salon, category=category, **service_data)

        return salon
    
class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('id', 'salon', 'user_id', 'rating', 'comment', 'image_url', 'created_at', 'updated_at')
        
class FixedOperatingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixedOperatingHours
        fields = '__all__'

class UnFixedOperatingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnFixedOperatingHours
        fields = '__all__'

class GeneratedTimeSlotsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedTimeSlots
        fields = ['salon', 'date', 'time_from', 'time_to', 'is_available']


class AppointmentSerializer(serializers.ModelSerializer):
    services = serializers.PrimaryKeyRelatedField(many=True, queryset=Service.objects.all())
    timeslots = serializers.PrimaryKeyRelatedField(many=True, queryset=GeneratedTimeSlots.objects.all())
    total_amount = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    status = serializers.CharField(default='P', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'salon', 'customer', 'services', 'total_amount','comment', 'status', 'created_at', 'timeslots']

    def create(self, validated_data):
        services = validated_data.pop('services')
        timeslots = validated_data.pop('timeslots')
        
        salon = validated_data.get('salon')
        customer = validated_data.get('customer')
        comment = validated_data.get('comment')

        # Checking if the salon ID exists
        if not Salon.objects.filter(id=salon.id).exists():
            raise serializers.ValidationError("The specified salon does not exist.")

        # Checking if the services correspond to the correct salon
        if not all(service.salon.id == salon.id for service in services):
            raise serializers.ValidationError("One or more services do not belong to the specified salon.")

        # Checking if the timeslots correspond to the correct salon
        if not all(timeslot.salon.id == salon.id for timeslot in timeslots):
            raise serializers.ValidationError("One or more timeslots do not belong to the specified salon.")

        # Checking if all timeslots are available
        if not all(timeslot.is_available for timeslot in timeslots):
            raise serializers.ValidationError("One or more of the specified timeslots are not available.")

        # Calculate total duration and price
        total_duration = timedelta()
        total_amount = 0
        for service in services:
            total_duration += service.duration_temp
            total_amount += service.price
        
        print('total_duration', total_duration)

        # total_duration = sum(service.duration_temp for service in services)
        # total_amount = sum(service.price for service in services)

        # Get the slot length from FixedOperatingHours or UnFixedOperatingHours
        try:
            slot_length = FixedOperatingHours.objects.get(salon=salon).time_slot_length
        except FixedOperatingHours.DoesNotExist:
            slot_length = UnFixedOperatingHours.objects.get(salon=salon).time_slot_length

        # Calculate how many time slots are needed
        total_timeslots_needed = int(total_duration.total_seconds() / 60) // slot_length
        print('total timeslots needed',total_timeslots_needed)
        print('len timeslots',len(timeslots))
        print('timeslots', timeslots)
        if total_duration % timedelta(minutes=slot_length):
            total_timeslots_needed += 1

        # Checking if calculated amount of timeslots corresponds to given timeslots in request
        if total_timeslots_needed != len(timeslots):
            raise serializers.ValidationError("The number of timeslots does not match the total duration of the services.")

        # Check if given timeslots are in one day
        if len(set(timeslot.date for timeslot in timeslots)) != 1:
            raise serializers.ValidationError("All timeslots must be on the same day.")

        # check if end time of all given timeslots or timeslot doesn't exceed operating hours time
        timeslots_sorted = sorted(timeslots, key=lambda x: x.time_from)
        last_timeslot_end_time = timeslots_sorted[-1].time_to
        try:
            closing_time = FixedOperatingHours.objects.get(salon=salon, day_of_week=timeslots_sorted[0].date.weekday()).close_time
        except FixedOperatingHours.DoesNotExist:
            closing_time = UnFixedOperatingHours.objects.get(salon=salon, date=timeslots_sorted[0].date).close_time
        if last_timeslot_end_time > closing_time:
            raise serializers.ValidationError("The end time of the appointment exceeds the operating hours of the salon.")

        # At this point, all the checks are passed, we can now create the appointment
        appointment = Appointment.objects.create(
            salon=salon,
            customer=customer,
            comment=comment,
            total_amount=total_amount,
            status='P',  # 'P' for Pending
        )

        # Attach the services and timeslots to the appointment
        for service in services:
            appointment.services.add(service)
        for timeslot in timeslots:
            timeslot.is_available = False
            timeslot.save()
            appointment.timeslots.add(timeslot)

        return appointment