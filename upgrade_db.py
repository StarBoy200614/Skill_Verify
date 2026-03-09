import sqlite3

def upgrade_db():
    conn = sqlite3.connect('/Users/ayush/Minzo/sv/instance/skillverify.db')
    cursor = conn.cursor()
    
    # Try adding new columns to user_profile table
    columns_to_add = [
        "ALTER TABLE user_profile ADD COLUMN cv_score INTEGER DEFAULT 0;",
        "ALTER TABLE user_profile ADD COLUMN cv_feedback TEXT;",
        "ALTER TABLE user_profile ADD COLUMN certificate_score INTEGER DEFAULT 0;",
        "ALTER TABLE user_profile ADD COLUMN certificate_feedback TEXT;"
    ]
    
    for query in columns_to_add:
        try:
            cursor.execute(query)
            print(f"Executed: {query}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Skipped (already exists): {query}")
            else:
                print(f"Error executing {query}: {e}")
                
    conn.commit()
    conn.close()
    print("Database upgrade finished.")

if __name__ == "__main__":
    upgrade_db()
