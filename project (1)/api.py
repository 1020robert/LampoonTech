from amadeus import Client, ResponseError

# Initialize the Amadeus client
amadeus = Client(
    client_id='fNerPnbeIHI6yV0rVdZskz1PEru57Hky',
    client_secret='PiZflndUD1tgG6Qf'
)

def fetch_flights(origin, destination, departure_date, adults=1):
    """Fetches flight offers from Amadeus API dynamically."""

    if not departure_date:
        raise ValueError("Departure date is required.")

    if not isinstance(adults, int) or adults < 1:
        raise ValueError("Adults must be a positive integer.")

    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=adults
        )
        return response.data  # Return the flight data from Amadeus API
    except ResponseError as error:
        return {"error": str(error)}

def validate_origin(iata_code):
    """Validate if the provided IATA code is a valid airport code."""
    try:
        # Request to fetch airport information
        response = amadeus.reference_data.locations.get(
            keyword=iata_code,
            subType='AIRPORT'
        )
        # Check if the provided code matches any location in the response
        for location in response.data:
            if location['iataCode'].upper() == iata_code.upper():
                return True
        return False
    except ResponseError as e:
        print(f"Error validating origin: {e}")
        return False
    
def get_airline_name(iata_code):
    """Fetch airline name from Amadeus API using IATA code."""
    try:
        response = amadeus.reference_data.airlines.get(airlineCodes=iata_code)
        if response.data and "businessName" in response.data[0]:
            return response.data[0]["businessName"]
        return iata_code  # Return the IATA code if no name is found
    except ResponseError:
        return iata_code  # Return original code if API fails

def get_airport_name(iata_code):
    """Fetch airport name from Amadeus API using IATA code."""
    try:
        response = amadeus.reference_data.locations.get(
            keyword=iata_code,
            subType="AIRPORT"
        )
        if response.data and "name" in response.data[0]:
            return response.data[0]["name"]
        return iata_code  # Return the IATA code if no name is found
    except ResponseError:
        return iata_code  # Return original code if API fails

