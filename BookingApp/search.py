from django.contrib.postgres.search import TrigramSimilarity
from django.db import connection
from django.db.models.query import Prefetch
from geopy.geocoders import Nominatim
from django.contrib.gis.geos import Point
from django.db.models import TextField, Q
from django.db.models.functions import Cast
from .models import Salon, Category, Service

## -------------------------------------------------------> 
## By Keywords, address and radius

def search_salons(keywords, address, radius):
    print("search salon [1]")
    defaultRadius = 15

    if keywords == '':
        salons = Salon.objects.all()
    else:
        salons = Salon.objects.annotate(
            similarity_name=TrigramSimilarity('name', keywords),
            similarity_address_city=TrigramSimilarity('address_city', keywords),
            similarity_about=TrigramSimilarity('about', keywords),
            similarity_categories=TrigramSimilarity(Cast('categories', TextField()), keywords),
            similarity_salon_categories=TrigramSimilarity(Cast('salon_categories', TextField()), keywords)
        ).filter(
            Q(similarity_name__gte=0.1) |
            Q(similarity_address_city__gte=0.1) |
            Q(similarity_about__gte=0.1) |
            Q(similarity_categories__gte=0.1) |
            Q(similarity_salon_categories__gte=0.1)
        ).distinct()  # Dodajemy metodę distinct()

    print(salons)

    if address:
        print("search salon [2]")
        point = get_point_from_address(address)
        # Tworzenie zapytania SQL z użyciem kursora
        cursor = connection.cursor()
        cursor.execute(
                '''
                SELECT id, location, ST_Distance(
                    location,
                    ST_SetSRID(ST_MakePoint(%s, %s)::geography, 4326)
                ) AS distance
                FROM [yours_postgresql_db]
                WHERE ST_DWithin(
                    location,
                    ST_SetSRID(ST_MakePoint(%s, %s)::geography, 4326),
                    %s
                )
                ''',
                [point.x, point.y, point.x, point.y, radius]
        )
        salon_ids = []
        salon_distances = {}
        for row in cursor.fetchall():
            salon_id = row[0]
            salon_ids.append(salon_id)
            distance_m = row[2]
            salon_distances[salon_id] = distance_m  # Convert back to meters

        salons = salons.filter(id__in=salon_ids).distinct()  # Dodajemy metodę distinct() po raz drugi
        print("search salon [3]")
        # Aktualizacja pola distance_from_query dla każdego salonu
        for salon in salons:
            salon.distance_from_query = salon_distances[salon.id]
            salon.save()  # Zapis wartości do modelu
    print("search salon [4]")
    return salons.order_by('-similarity_name')


# Reszta funkcji pozostaje bez zmian


## By Keywords, address and radius
## -------------------------------------------------------> 


## By Keywords
def search_by_keywords(keywords):

    if keywords == '':
        salons_results = Salon.objects.all()
    else:
        salons = Salon.objects.annotate(
            similarity_name=TrigramSimilarity('name', keywords),
            similarity_address_city=TrigramSimilarity('address_city', keywords),
            similarity_about=TrigramSimilarity('about', keywords),
            similarity_categories=TrigramSimilarity(Cast('categories', TextField()), keywords),
            similarity_salon_categories=TrigramSimilarity(Cast('salon_categories', TextField()), keywords)
        ).filter(
            Q(similarity_name__gte=0.1) |
            Q(similarity_address_city__gte=0.1) |
            Q(similarity_about__gte=0.1) |
            Q(similarity_categories__gte=0.1) |
            Q(similarity_salon_categories__gte=0.1)
        ).distinct() 

    salon_results = salons.filter(id__in=salons).distinct()
    
    # Pobieranie powiązanych kategorii i usług dla wyników z modelu Salon
    salon_results = salon_results.prefetch_related(
        Prefetch('categories', queryset=Category.objects.all()),
        Prefetch('salon_categories', queryset=Service.objects.all())
    )

    return salon_results


## By Keywords
## -------------------------------------------------------> 

## -------------------------------------------------------> 

## By Address

def search_by_address_radius(address, radius):
    if address:
        point = get_point_from_address(address)
        # Tworzenie zapytania SQL z użyciem kursora
        cursor = connection.cursor()
        cursor.execute(
                '''
                SELECT id, location, ST_Distance(
                    location,
                    ST_SetSRID(ST_MakePoint(%s, %s)::geography, 4326)
                ) AS distance
                FROM [yours_postgresql_db]
                WHERE ST_DWithin(
                    location,
                    ST_SetSRID(ST_MakePoint(%s, %s)::geography, 4326),
                    %s
                )
                ''',
                [point.x, point.y, point.x, point.y, radius]
        )
        salon_ids = []
        salon_distances = {}
        for row in cursor.fetchall():
            salon_id = row[0]
            salon_ids.append(salon_id)
            distance_m = row[2]
            salon_distances[salon_id] = distance_m  # Convert back to meters

        salons = Salon.objects.filter(id__in=salon_ids)
        print("search salon [3]")
        # Aktualizacja pola distance_from_query dla każdego salonu
        for salon in salons:
            salon.distance_from_query = salon_distances[salon.id]
            salon.save()  # Zapis wartości do modelu

    return salons


## -------------------------------------------------------> 

## -------------------------------------------------------> 
## Get point from address

def get_point_from_address(address):
    geolocator = Nominatim(user_agent='[yours_geolocator_id]')
    location = geolocator.geocode(address)
    if location:
        point = Point(float(location.latitude), float(location.longitude), srid=4326)
        print(point)
        return point
    return None

