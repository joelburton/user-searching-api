User Searching API
==================

A Flask-based application for searching users.

Requirements
------------

- Python 3
- Python Virtualenv
- PostgreSQL

Installation
------------

1. Create a Python virtual environment and install the requirements::

    python3 -m virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

2. Create the database and add the "earthdistance" extension (ships w/PostgreSQL)::

    createdb api_challenge
    psql -c "CREATE EXTENSION earthdistance CASCADE" api_challenge

3. Seed the database from the provided CSV file::

    python seed.py

4. Start server::

    python app.py

Testing
-------

Test using curl at the command line::

  curl http://localhost:5001/users?dist=100\ 
       \&origin=37.774929,-122.419416\&gender=f\&limit=1\&min_age=10
