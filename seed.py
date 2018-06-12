"""Seed database with data from CSV.

CSV contains one row per *location* (despite name of 'users.csv'); create one
user by de-duplicating on user_id, and one location per row.
"""

import csv
from app import db, User, Location

db.create_all()

# keep track of users added, so we skip adding second time
user_ids = set()

with open("challenge/users.csv") as f:
    for row in csv.DictReader(f):
        if row['user_id'] not in user_ids:
            user = User(
                id=row['user_id'],
                name=row['user_name'],
                age=row['user_age'],
                gender=row['user_gender'])
            db.session.add(user)
            user_ids.add(row['user_id'])

        location = Location(
            user_id=row['user_id'],
            name=row['last_location'],
            location=db.func.ll_to_earth(row['lat'], row['long']))

        db.session.add(location)

db.session.commit()
