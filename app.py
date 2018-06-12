"""Flask app for user-searching API."""

from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify

from sqlalchemy.types import UserDefinedType

# Our API lets users query by mile; DB uses meters for filtering
MILE_TO_METER = 1609.34

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://localhost/api_challenge"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy()
db.app = app
db.init_app(app)

# Strategy on how to handle geospatial stuff:
#
# - use PostgreSQL extension "earthdistance"
#   (need to CREATE EXTENSION earthdistance in your db)
# - create simple EARTH SQLAlchemy column type
# - insert earth points into db w/ ``db.func.ll_to_earth(lat,long)``
# - add column properties onto location table so we can extract lat/lng from obj
# - use ``db.func.earth_distance(p1, p2)`` for finding distance in meters p1<->p2
#
# from https://stackoverflow.com/questions/37245931


class EARTH(UserDefinedType):
    """Earth location data type."""

    def get_col_spec(self, **kw):
        return 'EARTH'


class User(db.Model):
    """Site user."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.Text, nullable=False)


class Location(db.Model):
    """Site user location. A user can have many locations."""

    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.Text, nullable=False)
    location = db.deferred(db.Column(EARTH, nullable=False))

    # properties to extract lat/lng from location field
    latitude = db.column_property(
        db.func.latitude(*location.columns, type_=db.Float))
    longitude = db.column_property(
        db.func.longitude(*location.columns, type_=db.Float))

    # a user can have many locations
    user = db.relationship(User, backref="locations")


def parse_lat_lng(origin):
    """Parse comma-joined origin into separate lat/long.

    Return (lat,lng):

        >>> parse_lat_lng("50.5,110.2")
        (50.5, 110.2)

        >>> parse_lat_lng("50.5, 110.2")
        (50.5, 110.2)

    For any kind of invalid input, returns (None, None):

        >>> parse_lat_lng("50.5,110.2,99")
        (None, None)

        >>> parse_lat_lng("so much nope")
        (None, None)
    """

    try:
        lat, lng = origin.split(",", 2)
        lat = float(lat)
        lng = float(lng)
        return (lat, lng)
    except ValueError:
        return (None, None)


@app.route("/users")
def users():
    """API search route.

    Can provide any/all of these as params in URL:
    - gender (text: challenge suggested limiting to m/f, but fuck that cisnormativity)
    - min_age (int)
    - max_age (int)
    - origin (string of lat,lng)
    - dist (int, max distance in miles)

    Pagination can be provided with:
    - limit (int for max # rows returned, default: 5)
    - start (int for start row, default: 0)

    Invalid search params should be ignored.

    Route returns JSON describing result.
    """

    # Parse parameters from URL

    gender = request.args.get("gender")
    min_age = request.args.get("min_age", type=int)
    max_age = request.args.get("max_age", type=int)
    origin = request.args.get("origin")
    dist = request.args.get("dist", type=int)
    limit = request.args.get("limit", default=5, type=int)
    start = request.args.get("start", default=0, type=int)

    q = User.query
    metadata_query = {}

    # TODO: could add "links" in metadata for previous/next page

    # Filter based on provided params

    if gender:
        q = q.filter(User.gender == gender)
        metadata_query['gender'] = gender

    if min_age is not None:
        q = q.filter(User.age >= min_age)
        metadata_query['min_age'] = min_age

    if max_age is not None:
        q = q.filter(User.age <= max_age)
        metadata_query['max_age'] = max_age

    if origin and dist is not None:
        lat, lng = parse_lat_lng(origin)
        if lat is not None:
            pt = db.func.ll_to_earth(lat, lng)
            meters = int(dist) * MILE_TO_METER
            q = q.filter(
                User.locations.any(
                    db.func.earth_distance(Location.location, pt) < meters))
            metadata_query['origin'] = origin
            metadata_query['dist'] = dist

    # Count of num results before any pagination
    total_results = q.count()

    # Provide pagination

    q = q.limit(limit).offset(start)

    metadata_query["limit"] = limit
    metadata_query["start"] = start

    # Execute query, build JSON

    metadata = {"path": "/users", "query": metadata_query}
    results = []

    for user in q.all():
        features = [{
            "type": "feature",
            "properties": {
                "city": location.name,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [location.longitude, location.latitude],
            },
        } for location in user.locations]

        results.append({
            "type": "user",
            "locationHistory": {
                "type": "FeatureCollection",
                "features": features,
            },
            "properties": {
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "gender": user.gender,
            },
        })

    return jsonify({
        "metadata": metadata,
        "total_results": total_results,
        "num_results": len(results),
        "results": results
    })


if __name__ == "__main__":
    app.run(port=5001, debug=True)
