import os
import sys

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, create_default_admin

# Initialize database and admin user
with app.app_context():
    try:
        db.create_all()
        create_default_admin()
    except Exception as e:
        print(f"Serverless DB init status: {e}")

# Export Flask application instance for Vercel WSGI handler
app = app
