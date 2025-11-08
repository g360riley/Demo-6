from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

tickers = Blueprint('tickers', __name__)

# Helper function to get stock data from Alpha Vantage
def get_stock_data(symbol):
    """Fetch stock data from Alpha Vantage API"""
    api_key = os.getenv('STOCK_API_KEY')
    if not api_key or api_key == 'your_alpha_vantage_api_key_here':
        return None, "Stock API key not configured"

    try:
        # Get real-time quote
        url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}'
        response = requests.get(url, timeout=10)
        data = response.json()

        # Check for API errors
        if 'Error Message' in data:
            return None, f"Invalid ticker symbol: {symbol}"
        elif 'Note' in data:
            return None, "API rate limit reached. Please try again in a minute."
        elif 'Global Quote' not in data or not data['Global Quote']:
            return None, f"No data available for symbol: {symbol}"

        quote = data['Global Quote']

        # Extract relevant data
        stock_data = {
            'symbol': quote.get('01. symbol', symbol),
            'price': float(quote.get('05. price', 0)),
            'change': float(quote.get('09. change', 0)),
            'change_percent': quote.get('10. change percent', '0%'),
            'volume': int(quote.get('06. volume', 0)),
            'latest_trading_day': quote.get('07. latest trading day', 'N/A')
        }

        return stock_data, None
    except requests.Timeout:
        return None, "API request timed out. Please try again."
    except Exception as e:
        return None, f"Error fetching stock data: {str(e)}"

@tickers.route('/', methods=['GET', 'POST'])
def show_tickers():
    if request.method == 'POST':
        ticker_symbol = request.form.get('ticker_symbol', '').strip().upper()
        ticker_name = request.form.get('ticker_name', '').strip()

        if not ticker_symbol:
            flash('Ticker symbol is required!', 'error')
            return redirect(url_for('tickers.show_tickers'))

        # Fetch live data from API
        stock_data, error = get_stock_data(ticker_symbol)

        if error:
            flash(error, 'error')
            return redirect(url_for('tickers.show_tickers'))

        # Use provided name or default to symbol if not provided
        if not ticker_name:
            ticker_name = ticker_symbol

        try:
            cursor = g.db.cursor()

            # Create table if it doesn't exist (with enhanced schema)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    change_amount DECIMAL(10, 2) DEFAULT 0,
                    change_percent VARCHAR(20) DEFAULT '0%',
                    volume BIGINT DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert new ticker with live data
            cursor.execute(
                '''INSERT INTO tickers (symbol, name, price, change_amount, change_percent, volume)
                   VALUES (%s, %s, %s, %s, %s, %s)''',
                (stock_data['symbol'], ticker_name, stock_data['price'],
                 stock_data['change'], stock_data['change_percent'], stock_data['volume'])
            )
            g.db.commit()
            flash(f'Ticker {ticker_symbol} added successfully with live price ${stock_data["price"]:.2f}!', 'success')
        except Exception as e:
            flash(f'Error adding ticker: {str(e)}', 'error')

        return redirect(url_for('tickers.show_tickers'))

    # Get all tickers
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM tickers ORDER BY id DESC')
        tickers_list = cursor.fetchall()
    except:
        tickers_list = []
        cursor = g.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                change_amount DECIMAL(10, 2) DEFAULT 0,
                change_percent VARCHAR(20) DEFAULT '0%',
                volume BIGINT DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        g.db.commit()

    # Check if API key is configured
    api_key = os.getenv('STOCK_API_KEY')
    api_configured = api_key and api_key != 'your_alpha_vantage_api_key_here'

    return render_template('tickers.html', tickers=tickers_list, api_configured=api_configured)

@tickers.route('/update/<int:ticker_id>')
def update_ticker(ticker_id):
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM tickers WHERE id = %s', (ticker_id,))
        ticker = cursor.fetchone()

        if not ticker:
            flash('Ticker not found', 'error')
            return redirect(url_for('tickers.show_tickers'))

        # Fetch live data from API
        stock_data, error = get_stock_data(ticker['symbol'])

        if error:
            flash(error, 'error')
            return redirect(url_for('tickers.show_tickers'))

        # Update ticker with all new data
        cursor.execute(
            '''UPDATE tickers
               SET price = %s, change_amount = %s, change_percent = %s, volume = %s, last_updated = CURRENT_TIMESTAMP
               WHERE id = %s''',
            (stock_data['price'], stock_data['change'], stock_data['change_percent'],
             stock_data['volume'], ticker_id)
        )
        g.db.commit()

        change_indicator = "+" if stock_data['change'] >= 0 else ""
        flash(f'Ticker {ticker["symbol"]} updated: ${stock_data["price"]:.2f} ({change_indicator}${stock_data["change"]:.2f})', 'success')

    except Exception as e:
        flash(f'Error updating ticker: {str(e)}', 'error')

    return redirect(url_for('tickers.show_tickers'))

@tickers.route('/delete/<int:ticker_id>')
def delete_ticker(ticker_id):
    try:
        cursor = g.db.cursor()
        cursor.execute('DELETE FROM tickers WHERE id = %s', (ticker_id,))
        g.db.commit()
        flash('Ticker deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting ticker: {str(e)}', 'error')

    return redirect(url_for('tickers.show_tickers'))

@tickers.route('/update-all')
def update_all_tickers():
    """Update all tickers with live data from API"""
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM tickers')
        all_tickers = cursor.fetchall()

        if not all_tickers:
            flash('No tickers to update', 'warning')
            return redirect(url_for('tickers.show_tickers'))

        updated_count = 0
        failed_count = 0

        for ticker in all_tickers:
            stock_data, error = get_stock_data(ticker['symbol'])

            if error:
                failed_count += 1
                continue

            cursor.execute(
                '''UPDATE tickers
                   SET price = %s, change_amount = %s, change_percent = %s, volume = %s, last_updated = CURRENT_TIMESTAMP
                   WHERE id = %s''',
                (stock_data['price'], stock_data['change'], stock_data['change_percent'],
                 stock_data['volume'], ticker['id'])
            )
            updated_count += 1

        g.db.commit()

        if updated_count > 0:
            flash(f'Successfully updated {updated_count} ticker(s)', 'success')
        if failed_count > 0:
            flash(f'Failed to update {failed_count} ticker(s)', 'warning')

    except Exception as e:
        flash(f'Error updating tickers: {str(e)}', 'error')

    return redirect(url_for('tickers.show_tickers'))

@tickers.route('/lookup')
def lookup_ticker():
    """Quick lookup endpoint for stock data (AJAX/API use)"""
    symbol = request.args.get('symbol', '').strip().upper()

    if not symbol:
        return jsonify({'error': 'Symbol is required'}), 400

    stock_data, error = get_stock_data(symbol)

    if error:
        return jsonify({'error': error}), 400

    return jsonify(stock_data)
