import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app_production_final import app
app.secret_key = os.environ.get('SECRET_KEY', 'peak-overwatch-secret-2026')
