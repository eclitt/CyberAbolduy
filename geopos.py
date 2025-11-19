import math

def is_in_radius_meters(center_lat, center_lon, point_lat, point_lon, radius_meters):
    # Радиус Земли в метрах
    R = 6371000
    
    # Разницы в радианах
    d_lat = math.radians(point_lat - center_lat)
    d_lon = math.radians(point_lon - center_lon)
    
    # Формула гаверсинусов
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(center_lat)) * math.cos(math.radians(point_lat)) * math.sin(d_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance <= radius_meters