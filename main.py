from collections import Counter
from flask import Flask, request, jsonify
import requests
from geopy.distance import geodesic

app = Flask(__name__)

def fetch_venue_data(api_url='http://localhost:8080/api'):
    response = requests.post(f"{api_url}/users/login", headers={'Content-Type': 'application/json'}, json={'email': 'admin@example.com', 'password': 'Admin1234*'})
    if response.status_code != 200:
        print('Error login: ', response.status_code)

    token = response.json()['token']
    response = requests.get(f"{api_url}/venues-ai", headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {token}"})

    if response.status_code == 200:
        print(response.json())
        return response.json()
    else:
        print("Error fetching data:", response.status_code)
        return []

# Function to calculate the distance between two geocoordinates
def haversine(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).km

@app.route('/recommendations', methods=['POST'])
def get_recommendations():
    user_data = request.json
    user_id = user_data.get('user_id')
    user_lat = user_data.get('user_lat')
    user_lon = user_data.get('user_lon')
    top_n = user_data.get('top_n', 5)

    venues = fetch_venue_data()

    if not venues:
        return jsonify({"error": "No venues found or failed to fetch data."}), 500

    user_venue_data = []
    for venue in venues['data']:  # assuming the API response contains a `data` key
        if 'fields' in venue:
            for field in venue['fields']:
                if 'bookings' in field:
                    for booking in field['bookings']:
                        if booking.get('customer_id') == user_id:
                            user_venue_data.append(venue)
                            break  # No need to continue if the user is already found

    if not user_venue_data:
        return {"error": "No venues found for the specified user."}

    field_types = [field['type'] for venue in user_venue_data for field in venue['fields'] if 'type' in field]
    fav_field_type = Counter(field_types).most_common(1)[0][0]  # Most frequent field type

    avg_user_rating = sum(venue['rating'] for venue in user_venue_data) / len(user_venue_data)

    recommended_venues = []
    for venue in venues['data']:
        if 'fields' in venue and any(field['type'] == fav_field_type for field in venue['fields']):
            venue_lat = venue['latitude']
            venue_lon = venue['longitude']
            distance_km = haversine(user_lat, user_lon, venue_lat, venue_lon)

            if venue['rating'] >= avg_user_rating and distance_km <= 20:
                recommended_venues.append({
                    'venue_id': venue['id'],
                    'venue_name': venue['name'],
                    'rating': venue['rating'],
                    'distance_km': distance_km
                })

    recommended_venues = sorted(recommended_venues, key=lambda x: (-x['rating'], x['distance_km']))

    print(f"rec: {recommended_venues}")

    return jsonify(recommended_venues[:top_n])

if __name__ == '__main__':
    app.run(debug=True)
