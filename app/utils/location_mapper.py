from geoalchemy2.shape import to_shape


def location_to_response(location):
    point = to_shape(location.coordinates)

    return {
        "id": location.id,
        "name": location.name,
        "type": location.type,
        "coordinates": f"{point.x},{point.y}",
        "timezone": location.timezone,
        "description": location.description,
    }
