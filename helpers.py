import requests

from flask import redirect, render_template, session
from functools import wraps
from datetime import datetime


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def usd(value):
    """Format value as USD."""
    try:
        value = float(value)
    except ValueError:
        raise ValueError(f"Cannot format non-numeric value as USD: {value}")
    return f"${value:,.2f}"


def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """Format ISO datetime strings into a readable format."""
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S').strftime(format)

def fetch_flight_price(origin, destination, departure_date):
    """Fetch the latest price for a specific flight."""
    try:
        response = fetch_flights(origin, departure_date, 1)

        # Ensure the response is valid and contains flights
        if not response or "error" in response:
            print(f"Error fetching flight price: {response.get('error', 'Unknown error')}")
            return None

        # Find the matching flight and return its price
        for flight in response:
            if (
                flight["itineraries"][0]["segments"][0]["departure"]["iataCode"] == origin
                and flight["itineraries"][0]["segments"][-1]["arrival"]["iataCode"] == destination
            ):
                return float(flight["price"]["total"])
    except Exception as e:
        print(f"Exception occurred: {e}")
    return None

