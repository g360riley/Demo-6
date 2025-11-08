from flask import Flask, g
from .app_factory import create_app
from .db_connect import close_db, get_db

app = create_app()
app.secret_key = 'your-secret'  # Replace with an environment

# Register Blueprints
from app.blueprints.examples import examples
from app.blueprints.tickers import tickers
from app.blueprints.weather import weather
from app.blueprints.movies import movies
from app.blueprints.chatbot import chatbot

app.register_blueprint(examples, url_prefix='/example')
app.register_blueprint(tickers, url_prefix='/tickers')
app.register_blueprint(weather, url_prefix='/weather')
app.register_blueprint(movies, url_prefix='/movies')
app.register_blueprint(chatbot, url_prefix='/chatbot')

from . import routes

@app.before_request
def before_request():
    g.db = get_db()
    if g.db is None:
        print("Warning: Database connection unavailable. Some features may not work.")

# Setup database connection teardown
@app.teardown_appcontext
def teardown_db(exception=None):
    close_db(exception)