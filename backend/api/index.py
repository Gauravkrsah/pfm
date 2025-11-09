import sys
import os

# Add the parent directory to the path so we can import from the backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Export the app for Vercel
app = app