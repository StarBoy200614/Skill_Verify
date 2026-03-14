import sqlite3
import os

def upgrade_db():
    db_path = '/Users/ayush/Minzo/sv/instance/skillverify.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add profile_image to user table
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN profile_image VARCHAR(255);")
        print("Added profile_image column to user table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("profile_image column already exists in user table.")
        else:
            print(f"Error adding profile_image to user table: {e}")
            
    conn.commit()
    conn.close()
    print("Database upgrade finished.")

if __name__ == "__main__":
    upgrade_db()
