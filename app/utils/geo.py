from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2.shape import from_shape
from shapely import MultiPolygon, Polygon
from shapely.geometry import Point, shape


def make_coords(latitude: float, longitude: float) -> WKBElement:
    return from_shape(Point(longitude, latitude), srid=4326)


def featurecollection_to_wkt_element(data: dict) -> WKTElement:
    """FeatureCollection to WKTElement(MULTIPOLYGON, 4326)."""
    geometries = []
    for feature in data["features"]:
        geom = shape(feature["geometry"])
        if isinstance(geom, Polygon):
            geometries.append(geom)
        elif isinstance(geom, MultiPolygon):
            geometries.extend(geom.geoms)
        else:
            raise TypeError(f"Unsupported: {geom.geom_type}")

    if not geometries:
        raise ValueError("Empty FeatureCollection")

    multi = MultiPolygon(geometries)
    return WKTElement(multi.wkt, srid=4326)
