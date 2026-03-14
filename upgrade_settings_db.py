import sqlite3
import os

def upgrade_db():
    db_path = '/Users/ayush/Minzo/sv/instance/skillverify.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tables and columns to add
    updates = [
        ("user", "email_notifications", "BOOLEAN DEFAULT 1"),
        ("user", "push_notifications", "BOOLEAN DEFAULT 1"),
        ("user", "two_factor_enabled", "BOOLEAN DEFAULT 0"),
        ("user", "is_public", "BOOLEAN DEFAULT 1"),
        ("user_profile", "visible_to_recruiters", "BOOLEAN DEFAULT 1"),
        ("user_profile", "open_to_opportunities", "BOOLEAN DEFAULT 0"),
        ("user_profile", "account_type", "VARCHAR(50) DEFAULT 'job_seeker'")
    ]
    
    for table, column, col_type in updates:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
            print(f"Added {column} column to {table} table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"{column} column already exists in {table} table.")
            else:
                print(f"Error adding {column} to {table} table: {e}")
            
    conn.commit()
    conn.close()
    print("Database upgrade finished.")

if __name__ == "__main__":
    upgrade_db()
