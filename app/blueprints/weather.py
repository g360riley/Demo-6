from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

weather = Blueprint('weather', __name__)

# Helper function to get weather data from OpenWeatherMap
def get_weather_data(city, state=''):
    """Fetch weather data from OpenWeatherMap API"""
    api_key = os.getenv('WEATHER_API_KEY')
    if not api_key or api_key == 'your_openweather_api_key_here':
        return None, "Weather API key not configured"

    try:
        # Build query string
        if state:
            query = f'{city},{state},US'
        else:
            query = f'{city},US'

        # Get current weather
        url = f'https://api.openweathermap.org/data/2.5/weather?q={query}&appid={api_key}&units=imperial'
        response = requests.get(url, timeout=10)
        data = response.json()

        # Check for API errors
        if response.status_code == 404:
            return None, f"City not found: {city}"
        elif response.status_code != 200:
            error_msg = data.get('message', 'Unknown error')
            return None, f"API error: {error_msg}"

        # Extract relevant data
        weather_data = {
            'city': data['name'],
            'state': state.upper() if state else '',
            'temperature': round(data['main']['temp'], 1),
            'feels_like': round(data['main']['feels_like'], 1),
            'humidity': data['main']['humidity'],
            'description': data['weather'][0]['description'].title(),
            'icon': data['weather'][0]['icon'],
            'wind_speed': round(data['wind']['speed'], 1),
            'pressure': data['main']['pressure'],
            'temp_min': round(data['main']['temp_min'], 1),
            'temp_max': round(data['main']['temp_max'], 1)
        }

        return weather_data, None
    except requests.Timeout:
        return None, "API request timed out. Please try again."
    except KeyError as e:
        return None, f"Unexpected API response format: missing {str(e)}"
    except Exception as e:
        return None, f"Error fetching weather data: {str(e)}"

@weather.route('/', methods=['GET', 'POST'])
def show_weather():
    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()

        if not city:
            flash('City is required!', 'error')
            return redirect(url_for('weather.show_weather'))

        # Fetch live weather data from API
        weather_data, error = get_weather_data(city, state)

        if error:
            flash(error, 'error')
            return redirect(url_for('weather.show_weather'))

        try:
            cursor = g.db.cursor()

            # Create table if it doesn't exist (with enhanced schema)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weather (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    city VARCHAR(100) NOT NULL,
                    state VARCHAR(50),
                    temperature DECIMAL(5, 2) NOT NULL,
                    feels_like DECIMAL(5, 2),
                    humidity INT,
                    description VARCHAR(100),
                    icon VARCHAR(10),
                    wind_speed DECIMAL(5, 2),
                    temp_min DECIMAL(5, 2),
                    temp_max DECIMAL(5, 2),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert new weather entry with live data
            cursor.execute(
                '''INSERT INTO weather (city, state, temperature, feels_like, humidity, description, icon, wind_speed, temp_min, temp_max)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (weather_data['city'], weather_data['state'], weather_data['temperature'],
                 weather_data['feels_like'], weather_data['humidity'], weather_data['description'],
                 weather_data['icon'], weather_data['wind_speed'], weather_data['temp_min'], weather_data['temp_max'])
            )
            g.db.commit()
            flash(f'Weather for {weather_data["city"]} added successfully! Current: {weather_data["temperature"]}°F', 'success')
        except Exception as e:
            flash(f'Error adding weather location: {str(e)}', 'error')

        return redirect(url_for('weather.show_weather'))

    # Get all weather entries
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM weather ORDER BY id DESC')
        weather_list = cursor.fetchall()
    except:
        weather_list = []
        cursor = g.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather (
                id INT AUTO_INCREMENT PRIMARY KEY,
                city VARCHAR(100) NOT NULL,
                state VARCHAR(50),
                temperature DECIMAL(5, 2) NOT NULL,
                feels_like DECIMAL(5, 2),
                humidity INT,
                description VARCHAR(100),
                icon VARCHAR(10),
                wind_speed DECIMAL(5, 2),
                temp_min DECIMAL(5, 2),
                temp_max DECIMAL(5, 2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        g.db.commit()

    # Check if API key is configured
    api_key = os.getenv('WEATHER_API_KEY')
    api_configured = api_key and api_key != 'your_openweather_api_key_here'

    return render_template('weather.html', weather_list=weather_list, api_configured=api_configured)

@weather.route('/update/<int:weather_id>')
def update_weather(weather_id):
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM weather WHERE id = %s', (weather_id,))
        weather_entry = cursor.fetchone()

        if not weather_entry:
            flash('Weather location not found', 'error')
            return redirect(url_for('weather.show_weather'))

        # Fetch live weather data from API
        weather_data, error = get_weather_data(weather_entry['city'], weather_entry.get('state', ''))

        if error:
            flash(error, 'error')
            return redirect(url_for('weather.show_weather'))

        # Update weather entry with all new data
        cursor.execute(
            '''UPDATE weather
               SET temperature = %s, feels_like = %s, humidity = %s, description = %s,
                   icon = %s, wind_speed = %s, temp_min = %s, temp_max = %s, updated_at = CURRENT_TIMESTAMP
               WHERE id = %s''',
            (weather_data['temperature'], weather_data['feels_like'], weather_data['humidity'],
             weather_data['description'], weather_data['icon'], weather_data['wind_speed'],
             weather_data['temp_min'], weather_data['temp_max'], weather_id)
        )
        g.db.commit()
        flash(f'Weather for {weather_entry["city"]} updated: {weather_data["temperature"]}°F - {weather_data["description"]}', 'success')

    except Exception as e:
        flash(f'Error updating weather: {str(e)}', 'error')

    return redirect(url_for('weather.show_weather'))

@weather.route('/delete/<int:weather_id>')
def delete_weather(weather_id):
    try:
        cursor = g.db.cursor()
        cursor.execute('DELETE FROM weather WHERE id = %s', (weather_id,))
        g.db.commit()
        flash('Weather location deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting weather location: {str(e)}', 'error')

    return redirect(url_for('weather.show_weather'))

@weather.route('/update-all')
def update_all_weather():
    """Update all weather locations with live data from API"""
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM weather')
        all_weather = cursor.fetchall()

        if not all_weather:
            flash('No locations to update', 'warning')
            return redirect(url_for('weather.show_weather'))

        updated_count = 0
        failed_count = 0

        for location in all_weather:
            weather_data, error = get_weather_data(location['city'], location.get('state', ''))

            if error:
                failed_count += 1
                continue

            cursor.execute(
                '''UPDATE weather
                   SET temperature = %s, feels_like = %s, humidity = %s, description = %s,
                       icon = %s, wind_speed = %s, temp_min = %s, temp_max = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s''',
                (weather_data['temperature'], weather_data['feels_like'], weather_data['humidity'],
                 weather_data['description'], weather_data['icon'], weather_data['wind_speed'],
                 weather_data['temp_min'], weather_data['temp_max'], location['id'])
            )
            updated_count += 1

        g.db.commit()

        if updated_count > 0:
            flash(f'Successfully updated {updated_count} location(s)', 'success')
        if failed_count > 0:
            flash(f'Failed to update {failed_count} location(s)', 'warning')

    except Exception as e:
        flash(f'Error updating weather locations: {str(e)}', 'error')

    return redirect(url_for('weather.show_weather'))

@weather.route('/lookup')
def lookup_weather():
    """Quick lookup endpoint for weather data (AJAX/API use)"""
    city = request.args.get('city', '').strip()
    state = request.args.get('state', '').strip()

    if not city:
        return jsonify({'error': 'City is required'}), 400

    weather_data, error = get_weather_data(city, state)

    if error:
        return jsonify({'error': error}), 400

    return jsonify(weather_data)
