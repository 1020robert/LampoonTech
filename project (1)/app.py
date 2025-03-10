import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from helpers import apology, login_required, usd, format_datetime, fetch_flight_price
import pytz
from api import fetch_flights, validate_origin, get_airline_name, get_airport_name

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters['format_datetime'] = format_datetime


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Homepage after login"""
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("Fill out all of the boxes")

        if password != confirmation:
            return apology("Password does not equal confirmation")

        try:
            id = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                            username, generate_password_hash(password))
        except:
            return apology("Username is already taken")

        session["user_id"] = id

        # Redirect user to home page
        return redirect("/")

    # get request and a post request(what should happen once you fill out the table)


@app.route("/suggestions", methods=["GET", "POST"])
@login_required
def suggestions():
    """Get user suggestions"""
    if request.method == "POST":
        suggestion = request.form.get("suggestion")

        # Validate the suggestion
        if not suggestion:
            return apology("Message cannot be empty!")

        # Insert the suggestion into the database
        db.execute(
            "INSERT INTO suggestions (user_id, suggestion) VALUES (?, ?)",
            session["user_id"], suggestion
        )

        flash("Suggestion submitted successfully!")
        return redirect("/suggestions")  # Redirect to avoid resubmitting the form on refresh

    # Fetch all suggestions from the database (GET request)
    all_suggestions = db.execute(
        "SELECT users.username, suggestions.suggestion, suggestions.created_at "
        "FROM suggestions "
        "JOIN users ON suggestions.user_id = users.id "
        "ORDER BY suggestions.created_at DESC"
    )

    return render_template("suggestions.html", suggestions=all_suggestions)


@app.route("/about")
def about():
    """Route the about page"""
    return render_template("about.html")


@app.route('/search',  methods=["GET", "POST"])
@login_required
def search_flights():
    """Allows users to search for flights"""
    if request.method == "GET":
        # Display the search form
        return render_template("search.html")
    else:
        # Handle form submission for flight search
        origin = request.form.get('origin').strip().upper()
        departure_date = request.form.get('departure_date')
        adults = request.form.get('adults', 1)

        if not isinstance(origin, str):
            return apology("Origin must be a string")

        if not len(origin) == 3:
            return apology("Origin must be three characters")

        if not origin.isalpha():
            return apology("Origin must be alphabetical")

        # Validate the form inputs
        if not origin:
            return apology("Invalid Origin")

        if not validate_origin(origin):
            return apology("Invalid Origin.")

        if not departure_date:
            return apology("Invalid Departure Date")
        try:
            adults = int(adults)
            if adults < 1:
                return apology("Number of adults must be at least 1")
        except ValueError:
            return apology("Invalid number of adults")

        today = datetime.now().date()
        try:
            selected_date = datetime.strptime(departure_date, "%Y-%m-%d").date()
            if selected_date < today:
                return apology("Departure date must be today or in the future")
        except ValueError:
            return apology("Invalid date format")

        # Fetch only flights to Boston
        flights = fetch_flights(origin, departure_date, adults)

        if not flights:
            return apology("No flights to Boston found")

        session["flights"] = flights
        return redirect('/results')


@app.route('/save_flight', methods=["POST"])
@login_required
def save_flight():
    """Save a specific flight for the logged-in user."""
    origin = request.form.get("origin")
    destination = request.form.get("destination")
    departure_date = request.form.get("departure_date")
    price = request.form.get("price")
    airline = request.form.get("airline")

    if not origin or not destination or not departure_date or not price:
        return apology("Missing flight data")

    try:
        price = float(price)
    except ValueError:
        return apology("Invalid price value")
    # Save to database
    db.execute("INSERT INTO saved_flights (user_id, origin, destination, departure_date, price, airline) VALUES (?, ?, ?, ?, ?, ?)",
               session["user_id"], origin, destination, departure_date, price, airline)

    flash("Flight saved successfully!")
    return redirect("/saved_flights")


@app.route('/saved_flights', methods=["GET"])
@login_required
def saved_flights():
    """Display the user's saved flights with updated prices."""
    saved_flights = db.execute(
        "SELECT * FROM saved_flights WHERE user_id = ? ORDER BY saved_at DESC", session["user_id"])

    for flight in saved_flights:
        updated_price = fetch_flight_price(
            flight["origin"], flight["destination"], flight["departure_date"])

        # Debugging: Print the updated_price
        print(f"Updated price for flight ID {flight['id']}: {updated_price}")

        # Ensure it's a number
        if updated_price is not None and isinstance(updated_price, (int, float)):
            db.execute("UPDATE saved_flights SET price = ? WHERE id = ?",
                       updated_price, flight["id"])

    return render_template("saved_flights.html", saved_flights=saved_flights)



@app.route('/results', methods=["GET"])
@login_required
def results():
    """Display the results for the user's flight search."""
    flights = session.get("flights")

    if not flights or not isinstance(flights, list):
        return render_template("no_results.html")

    # Replace IATA codes with full names before rendering the page
    for flight in flights:
        for itinerary in flight.get("itineraries", []):
            for segment in itinerary.get("segments", []):
                segment["departure"]["airportName"] = get_airport_name(segment["departure"]["iataCode"])
                segment["arrival"]["airportName"] = get_airport_name(segment["arrival"]["iataCode"])

        flight["airlineName"] = get_airline_name(flight["validatingAirlineCodes"][0]) if "validatingAirlineCodes" in flight else "Unknown Airline"

    return render_template("results.html", flights=flights)


@app.route('/delete_flight/<int:flight_id>', methods=["POST"])
@login_required
def delete_flight(flight_id):
    """Delete a saved flight by ID."""
    db.execute("DELETE FROM saved_flights WHERE id = ? AND user_id = ?",
               flight_id, session["user_id"])
    flash("Flight deleted successfully!")
    return redirect('/saved_flights')

@app.route('/image_flight_search')
@login_required
def image_flight_search():
    """Renders the image-based flight search page."""
    return render_template('image_flight_search.html')

@app.route('/fetch_flight_from_bos', methods=["POST"])
@login_required
def fetch_flight_from_bos():
    """Fetches the cheapest flight from BOS to a selected destination and redirects to results."""
    destination = request.form.get('destination')

    if not destination:
        return apology("Invalid destination")

    # Set departure date to tomorrow
    departure_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')

    # ✅ Explicitly pass arguments without reassigning `adults`
    flights = fetch_flights("BOS", destination, departure_date, 1)

    if not flights or not isinstance(flights, list):
        return apology("No flights found")

    # Extract the **cheapest** flight
    cheapest_flight = min(flights, key=lambda flight: float(flight.get("price", {}).get("total", float('inf'))))

    # Ensure the flight has the correct structure for results.html
    if "itineraries" not in cheapest_flight or "segments" not in cheapest_flight["itineraries"][0]:
        return apology("Invalid flight data format.")

    # Store the flight in session in a list (so results.html can iterate over it)
    session["flights"] = [cheapest_flight]

    return redirect("/results")


@app.route('/children')
@login_required  # Remove this if you want the page to be public
def potential_step_children():
    """Render the Potential Step Children page."""
    return render_template('children.html')



