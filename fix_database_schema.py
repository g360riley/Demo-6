"""
Script to update database tables with new schema
Run this once to migrate existing tables to the new enhanced schema
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def fix_database_schema():
    """Drop and recreate tables with enhanced schema"""

    # Connect directly to database
    try:
        db = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306)),
            cursorclass=pymysql.cursors.DictCursor
        )
        print("[OK] Connected to database")
    except Exception as e:
        print(f"Error: Could not connect to database: {e}")
        return

    cursor = db.cursor()

    try:
        # Drop and recreate tickers table
        print("Updating tickers table...")
        cursor.execute('DROP TABLE IF EXISTS tickers')
        cursor.execute('''
            CREATE TABLE tickers (
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
        print("[OK] Tickers table updated")

        # Drop and recreate weather table
        print("Updating weather table...")
        cursor.execute('DROP TABLE IF EXISTS weather')
        cursor.execute('''
            CREATE TABLE weather (
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
        print("[OK] Weather table updated")

        # Drop and recreate movies table
        print("Updating movies table...")
        cursor.execute('DROP TABLE IF EXISTS movies')
        cursor.execute('''
            CREATE TABLE movies (
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
        print("[OK] Movies table updated")

        # Drop and recreate chatbot_history table
        print("Updating chatbot_history table...")
        cursor.execute('DROP TABLE IF EXISTS chatbot_history')
        cursor.execute('''
            CREATE TABLE chatbot_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                model VARCHAR(50) DEFAULT 'llama3-8b-8192',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("[OK] Chatbot history table updated")

        db.commit()
        print("\n[SUCCESS] All tables updated successfully!")
        print("\nNote: All existing data has been cleared. You can now add new entries.")

    except Exception as e:
        print(f"\n[ERROR] Error updating database: {e}")
        db.rollback()
    finally:
        cursor.close()
        db.close()
        print("Database connection closed.")

if __name__ == '__main__':
    print("=" * 60)
    print("Database Schema Update Script")
    print("=" * 60)
    print("\nThis will DROP and RECREATE all tables with the new schema.")
    print("WARNING: This will DELETE all existing data!\n")

    response = input("Do you want to continue? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        fix_database_schema()
    else:
        print("Operation cancelled.")
