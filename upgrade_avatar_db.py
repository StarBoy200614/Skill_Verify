"""
Migration: Change profile_image column from VARCHAR(255) to TEXT
to support base64-encoded images stored directly in the database.
"""
from app import app, db

with app.app_context():
    try:
        # SQLite: recreate column type via raw ALTER TABLE isn't supported.
        # Instead, use raw SQL to check the current type and modify the DB.
        engine = db.engine
        with engine.connect() as conn:
            # For SQLite, we check schema and update if needed
            result = conn.execute(db.text("PRAGMA table_info('user')"))
            cols = result.fetchall()
            
            profile_img_col = next((c for c in cols if c[1] == 'profile_image'), None)
            
            if profile_img_col:
                print(f"Current profile_image column type: {profile_img_col[2]}")
                if 'TEXT' in str(profile_img_col[2]).upper():
                    print("Column is already TEXT. No migration needed.")
                else:
                    print("Migrating profile_image to TEXT via table rebuild...")
                    # SQLite doesn't support ALTER COLUMN TYPE directly
                    # We need to recreate the table
                    conn.execute(db.text("BEGIN TRANSACTION"))
                    conn.execute(db.text("""
                        CREATE TABLE IF NOT EXISTS user_new (
                            id INTEGER PRIMARY KEY,
                            email VARCHAR(120) UNIQUE NOT NULL,
                            password_hash VARCHAR(255),
                            name VARCHAR(100),
                            oauth_provider VARCHAR(50),
                            oauth_id VARCHAR(200),
                            google_id VARCHAR(200) UNIQUE,
                            github_id VARCHAR(200) UNIQUE,
                            profile_image TEXT,
                            created_at DATETIME,
                            email_notifications BOOLEAN DEFAULT 1,
                            push_notifications BOOLEAN DEFAULT 1,
                            two_factor_enabled BOOLEAN DEFAULT 0,
                            is_public BOOLEAN DEFAULT 1
                        )
                    """))
                    conn.execute(db.text("""
                        INSERT INTO user_new 
                        SELECT id, email, password_hash, name, oauth_provider, oauth_id,
                               google_id, github_id, profile_image, created_at,
                               email_notifications, push_notifications, two_factor_enabled, is_public
                        FROM "user"
                    """))
                    conn.execute(db.text('DROP TABLE "user"'))
                    conn.execute(db.text('ALTER TABLE user_new RENAME TO "user"'))
                    conn.execute(db.text("COMMIT"))
                    print("Migration complete - profile_image is now TEXT.")
            else:
                print("profile_image column not found. Skipping migration.")
    except Exception as e:
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
