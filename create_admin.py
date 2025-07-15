import os
from app import app, db, User
from werkzeug.security import generate_password_hash
# from dotenv import load_dotenv # Only needed if running this specific script directly locally outside of Flask's context

def create_admin_user_for_production():
    with app.app_context():
        # Get admin credentials from environment variables
        # These variables MUST be set on Render (and optionally in your local .env for testing)
        username = os.environ.get('ADMIN_USERNAME')
        password = os.environ.get('ADMIN_PASSWORD')

        if not all([username, password]):
            print("ERROR: ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD environment variables must be set.")
            print("Cannot create admin user without credentials.")
            return

        # Check if admin user already exists
        admin_user = User.query.filter_by(username=username).first()
        if admin_user:
            print(f"Admin user '{username}' already exists in the database. Skipping creation.")
            return

        # Hash the password
        hashed_password = generate_password_hash(password)

        new_admin = User(
            username=username,
            password_hash=hashed_password
        )

        db.session.add(new_admin)
        db.session.commit()
        print(f"Admin user '{username}' created successfully in the database!")

if __name__ == '__main__':
    # For local testing of this script with .env, you might re-enable load_dotenv() here
    # load_dotenv() # Uncomment this if you want to test this script locally using a .env file
    create_admin_user_for_production()