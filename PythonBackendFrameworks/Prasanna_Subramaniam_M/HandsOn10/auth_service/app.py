"""
Auth Service - Manages authentication and users

Port: 5003
Endpoints:
- GET /health - Health check
- POST /api/auth/register - Register a new user
- POST /api/auth/login - Login and get JWT token
- GET /api/auth/verify - Verify JWT token
"""

from flask import Flask, request, jsonify
from database import db, init_app
from models import User
from security import hash_password, verify_password, create_access_token, verify_token

# Create Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'auth-service-secret'

# Initialize database
init_app(app)

# Create tables
with app.app_context():
    db.create_all()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'auth_service',
        'port': 5003
    }


@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return {
                'error': {
                    'code': 'BAD_REQUEST',
                    'message': f'Missing required field: {field}'
                }
            }, 400
    
    # Check if username exists
    existing = User.query.filter_by(username=data['username']).first()
    if existing:
        return {
            'error': {
                'code': 'CONFLICT',
                'message': f'Username {data["username"]} already exists'
            }
        }, 409
    
    # Check if email exists
    existing = User.query.filter_by(email=data['email']).first()
    if existing:
        return {
            'error': {
                'code': 'CONFLICT',
                'message': f'Email {data["email"]} already exists'
            }
        }, 409
    
    # Create user
    user = User(
        username=data['username'],
        email=data['email'],
        hashed_password=hash_password(data['password'])
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify(user.to_dict()), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login and get JWT token"""
    data = request.get_json()
    
    if 'username' not in data or 'password' not in data:
        return {
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Missing username or password'
            }
        }, 400
    
    # Find user
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not verify_password(data['password'], user.hashed_password):
        return {
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Invalid username or password'
            }
        }, 401
    
    # Check if user is active
    if not user.is_active:
        return {
            'error': {
                'code': 'FORBIDDEN',
                'message': 'User account is disabled'
            }
        }, 403
    
    # Create access token
    access_token = create_access_token({"sub": user.username})
    
    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'user': user.to_dict()
    }, 200


@app.route('/api/auth/verify', methods=['POST'])
def verify():
    """Verify a JWT token"""
    data = request.get_json()
    
    if 'token' not in data:
        return {
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Missing token'
            }
        }, 400
    
    payload = verify_token(data['token'])
    
    if not payload:
        return {
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Invalid or expired token'
            }
        }, 401
    
    username = payload.get('sub')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return {
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'User not found'
            }
        }, 401
    
    return {
        'valid': True,
        'user': user.to_dict()
    }, 200


@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get current user from token"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return {
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Missing or invalid Authorization header'
            }
        }, 401
    
    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    
    if not payload:
        return {
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Invalid or expired token'
            }
        }, 401
    
    username = payload.get('sub')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return {
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'User not found'
            }
        }, 401
    
    return jsonify(user.to_dict()), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)