from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

movies = Blueprint('movies', __name__)

# Helper function to get movie data from OMDB API
def get_movie_data(title, year=None):
    """Fetch movie data from OMDB API"""
    api_key = os.getenv('OMDB_API_KEY')
    if not api_key or api_key == 'your_omdb_api_key_here':
        return None, "OMDB API key not configured"

    try:
        # Build URL with optional year parameter
        url = f'http://www.omdbapi.com/?t={title}&apikey={api_key}'
        if year:
            url += f'&y={year}'

        response = requests.get(url, timeout=10)
        data = response.json()

        # Check for API errors
        if data.get('Response') == 'False':
            error_msg = data.get('Error', 'Unknown error')
            return None, f"Movie not found: {error_msg}"

        # Extract relevant data
        movie_data = {
            'title': data.get('Title', 'N/A'),
            'year': data.get('Year', 'N/A'),
            'rated': data.get('Rated', 'N/A'),
            'released': data.get('Released', 'N/A'),
            'runtime': data.get('Runtime', 'N/A'),
            'genre': data.get('Genre', 'N/A'),
            'director': data.get('Director', 'N/A'),
            'writer': data.get('Writer', 'N/A'),
            'actors': data.get('Actors', 'N/A'),
            'plot': data.get('Plot', 'N/A'),
            'language': data.get('Language', 'N/A'),
            'country': data.get('Country', 'N/A'),
            'awards': data.get('Awards', 'N/A'),
            'poster': data.get('Poster', 'N/A'),
            'imdb_rating': data.get('imdbRating', 'N/A'),
            'imdb_votes': data.get('imdbVotes', 'N/A'),
            'box_office': data.get('BoxOffice', 'N/A'),
            'imdb_id': data.get('imdbID', 'N/A')
        }

        return movie_data, None
    except requests.Timeout:
        return None, "API request timed out. Please try again."
    except Exception as e:
        return None, f"Error fetching movie data: {str(e)}"

@movies.route('/', methods=['GET', 'POST'])
def show_movies():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        year = request.form.get('year', '').strip()

        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('movies.show_movies'))

        # Fetch movie data from OMDB API
        movie_data, error = get_movie_data(title, year if year else None)

        if error:
            flash(error, 'error')
            return redirect(url_for('movies.show_movies'))

        try:
            cursor = g.db.cursor()

            # Create enhanced table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    year VARCHAR(10),
                    rated VARCHAR(10),
                    released VARCHAR(50),
                    runtime VARCHAR(50),
                    genre VARCHAR(200),
                    director VARCHAR(200),
                    writer TEXT,
                    actors TEXT,
                    plot TEXT,
                    language VARCHAR(100),
                    country VARCHAR(100),
                    awards TEXT,
                    poster VARCHAR(500),
                    imdb_rating VARCHAR(10),
                    imdb_votes VARCHAR(50),
                    box_office VARCHAR(50),
                    imdb_id VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert new movie with all data
            cursor.execute(
                '''INSERT INTO movies (title, year, rated, released, runtime, genre, director, writer, actors,
                   plot, language, country, awards, poster, imdb_rating, imdb_votes, box_office, imdb_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (movie_data['title'], movie_data['year'], movie_data['rated'], movie_data['released'],
                 movie_data['runtime'], movie_data['genre'], movie_data['director'], movie_data['writer'],
                 movie_data['actors'], movie_data['plot'], movie_data['language'], movie_data['country'],
                 movie_data['awards'], movie_data['poster'], movie_data['imdb_rating'], movie_data['imdb_votes'],
                 movie_data['box_office'], movie_data['imdb_id'])
            )
            g.db.commit()
            flash(f'Movie "{movie_data["title"]}" ({movie_data["year"]}) added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding movie: {str(e)}', 'error')

        return redirect(url_for('movies.show_movies'))

    # Get all movies
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM movies ORDER BY id DESC')
        movies_list = cursor.fetchall()
    except:
        movies_list = []
        cursor = g.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                year VARCHAR(10),
                rated VARCHAR(10),
                released VARCHAR(50),
                runtime VARCHAR(50),
                genre VARCHAR(200),
                director VARCHAR(200),
                writer TEXT,
                actors TEXT,
                plot TEXT,
                language VARCHAR(100),
                country VARCHAR(100),
                awards TEXT,
                poster VARCHAR(500),
                imdb_rating VARCHAR(10),
                imdb_votes VARCHAR(50),
                box_office VARCHAR(50),
                imdb_id VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        g.db.commit()

    # Check if API key is configured
    api_key = os.getenv('OMDB_API_KEY')
    api_configured = api_key and api_key != 'your_omdb_api_key_here'

    return render_template('movies.html', movies=movies_list, api_configured=api_configured)

@movies.route('/view/<int:movie_id>')
def view_movie(movie_id):
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM movies WHERE id = %s', (movie_id,))
        movie = cursor.fetchone()

        if movie:
            return render_template('movie_view.html', movie=movie)
        else:
            flash('Movie not found', 'error')
            return redirect(url_for('movies.show_movies'))
    except Exception as e:
        flash(f'Error viewing movie: {str(e)}', 'error')
        return redirect(url_for('movies.show_movies'))

@movies.route('/edit/<int:movie_id>', methods=['GET', 'POST'])
def edit_movie(movie_id):
    if request.method == 'POST':
        try:
            cursor = g.db.cursor()

            # Get all form fields
            fields = {
                'title': request.form.get('title'),
                'year': request.form.get('year'),
                'rated': request.form.get('rated'),
                'runtime': request.form.get('runtime'),
                'genre': request.form.get('genre'),
                'director': request.form.get('director'),
                'actors': request.form.get('actors'),
                'plot': request.form.get('plot'),
                'awards': request.form.get('awards'),
                'poster': request.form.get('poster'),
                'imdb_rating': request.form.get('imdb_rating')
            }

            cursor.execute(
                '''UPDATE movies SET title = %s, year = %s, rated = %s, runtime = %s, genre = %s,
                   director = %s, actors = %s, plot = %s, awards = %s, poster = %s, imdb_rating = %s
                   WHERE id = %s''',
                (fields['title'], fields['year'], fields['rated'], fields['runtime'], fields['genre'],
                 fields['director'], fields['actors'], fields['plot'], fields['awards'], fields['poster'],
                 fields['imdb_rating'], movie_id)
            )
            g.db.commit()
            flash(f'Movie "{fields["title"]}" updated successfully!', 'success')
            return redirect(url_for('movies.show_movies'))
        except Exception as e:
            flash(f'Error updating movie: {str(e)}', 'error')
            return redirect(url_for('movies.show_movies'))

    # If GET request, redirect to main page (shouldn't be accessed directly anymore)
    return redirect(url_for('movies.show_movies'))

@movies.route('/delete/<int:movie_id>')
def delete_movie(movie_id):
    try:
        cursor = g.db.cursor()
        cursor.execute('DELETE FROM movies WHERE id = %s', (movie_id,))
        g.db.commit()
        flash('Movie deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting movie: {str(e)}', 'error')

    return redirect(url_for('movies.show_movies'))

@movies.route('/search')
def search_movie():
    """Quick search endpoint for movie data (AJAX/API use)"""
    title = request.args.get('title', '').strip()
    year = request.args.get('year', '').strip()

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    movie_data, error = get_movie_data(title, year if year else None)

    if error:
        return jsonify({'error': error}), 400

    return jsonify(movie_data)
