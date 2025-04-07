from flask import Blueprint
from api.routes import setup_routes

# Initialize the API Blueprint
api_bp = Blueprint('api', __name__)

# Register routes from the routes file
setup_routes(api_bp)
