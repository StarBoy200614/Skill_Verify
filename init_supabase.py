import os
from dotenv import load_dotenv

# Load local environment variables (like your Supabase URL)
load_dotenv(override=True)

# Important: Make sure DATABASE_URL is set to your Supabase connection string
# in your local .env file before running this, or export it in your terminal!
if not os.environ.get('DATABASE_URL'):
    print("WARNING: No DATABASE_URL found in environment!")
    print("Please add your Supabase connection string to your .env file as DATABASE_URL='postgresql://...'")
    print("Then run this script again.")
    exit(1)

from app import app, db

def initialize_database():
    with app.app_context():
        try:
            print(f"Connecting to database: {os.environ.get('DATABASE_URL').split('@')[-1]}")
            # This creates all tables defined in your models
            db.create_all()
            print("✅ Successfully created all database tables in Supabase!")
        except Exception as e:
            print("❌ Error creating tables:")
            print(e)

if __name__ == "__main__":
    initialize_database()
