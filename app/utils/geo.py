from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape
from shapely.geometry import Point


def make_coords(latitude: float, longitude: float) -> WKBElement:
    return from_shape(Point(longitude, latitude), srid=4326)
