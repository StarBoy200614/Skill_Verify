from app import app, db
app.app_context().push()
try:
    db.session.execute(db.text('ALTER TABLE user ADD COLUMN test_col2 VARCHAR(10)'))
    db.session.commit()
    print("Success")
except Exception as e:
    print(f"Failed: {e}")
