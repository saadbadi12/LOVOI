from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt

import requests
from django.conf import settings


AGENCY_ADDRESS = getattr(settings, 'AGENCY_ADDRESS', 'Casablanca, Morocco')
AGENCY_LATITUDE = Decimal(str(getattr(settings, 'AGENCY_LATITUDE', 33.5731)))
AGENCY_LONGITUDE = Decimal(str(getattr(settings, 'AGENCY_LONGITUDE', -7.5898)))
DELIVERY_PRICE_PER_KM = Decimal(str(getattr(settings, 'DELIVERY_PRICE_PER_KM', '5.00')))


def _haversine_km(origin, destination):
    lat1, lon1 = map(float, origin)
    lat2, lon2 = map(float, destination)
    radius_km = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return Decimal(str(2 * radius_km * asin(sqrt(a))))


def get_distance(origin, destination):
    """
    Return distance in km.

    If GOOGLE_MAPS_API_KEY is configured, this uses Google Distance Matrix for
    address strings. If origin/destination are coordinate tuples, it uses a
    local haversine fallback.
    """
    if isinstance(origin, (tuple, list)) and isinstance(destination, (tuple, list)):
        return _haversine_km(origin, destination).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    if not api_key:
        raise ValueError('GOOGLE_MAPS_API_KEY is not configured.')

    response = requests.get(
        'https://maps.googleapis.com/maps/api/distancematrix/json',
        params={
            'origins': origin,
            'destinations': destination,
            'key': api_key,
            'units': 'metric',
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    element = payload['rows'][0]['elements'][0]
    if element.get('status') != 'OK':
        raise ValueError("Impossible de calculer la distance pour cette adresse.")

    km = Decimal(str(element['distance']['value'])) / Decimal('1000')
    return km.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_delivery_quote(address=None, latitude=None, longitude=None, price_per_km=None):
    price_per_km = Decimal(str(price_per_km or DELIVERY_PRICE_PER_KM))

    if latitude and longitude:
        distance_km = get_distance(
            (AGENCY_LATITUDE, AGENCY_LONGITUDE),
            (Decimal(str(latitude)), Decimal(str(longitude))),
        )
    elif address:
        distance_km = get_distance(AGENCY_ADDRESS, address)
    else:
        raise ValueError("Adresse de livraison obligatoire.")

    fee = (distance_km * price_per_km).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return {
        'distance_km': distance_km,
        'fee': fee,
        'price_per_km': price_per_km,
    }
