"""
Course Service - Manages departments and courses

Port: 5001
Endpoints:
- GET /health - Health check
- GET /api/courses - List all courses
- GET /api/courses/<id> - Get course by ID
- POST /api/courses - Create a new course
- PUT /api/courses/<id> - Update course
- DELETE /api/courses/<id> - Delete course
- GET /api/departments - List all departments
- POST /api/departments - Create department
"""

from flask import Flask, request, jsonify
from database import db, init_app
from models import Course, Department
import os

# Create Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///courses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'course-service-secret'

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
        'service': 'course_service',
        'port': 5001
    }


@app.route('/api/courses', methods=['GET'])
def list_courses():
    """List all courses"""
    courses = Course.query.all()
    return jsonify([course.to_dict() for course in courses]), 200


@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """Get a course by ID"""
    course = Course.query.get(course_id)
    if not course:
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Course with id {course_id} not found'
            }
        }, 404
    return jsonify(course.to_dict()), 200


@app.route('/api/courses', methods=['POST'])
def create_course():
    """Create a new course"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'code', 'credits', 'department_id']
    for field in required_fields:
        if field not in data:
            return {
                'error': {
                    'code': 'BAD_REQUEST',
                    'message': f'Missing required field: {field}'
                }
            }, 400
    
    # Check if department exists
    department = Department.query.get(data['department_id'])
    if not department:
        return {
            'error': {
                'code': 'BAD_REQUEST',
                'message': f'Department with id {data["department_id"]} not found'
            }
        }, 400
    
    # Check if course code already exists
    existing = Course.query.filter_by(code=data['code']).first()
    if existing:
        return {
            'error': {
                'code': 'CONFLICT',
                'message': f'Course with code {data["code"]} already exists'
            }
        }, 409
    
    course = Course(
        name=data['name'],
        code=data['code'],
        credits=data['credits'],
        department_id=data['department_id']
    )
    
    db.session.add(course)
    db.session.commit()
    
    return jsonify(course.to_dict()), 201


@app.route('/api/courses/<int:course_id>', methods=['PUT'])
def update_course(course_id):
    """Update a course"""
    course = Course.query.get(course_id)
    if not course:
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Course with id {course_id} not found'
            }
        }, 404
    
    data = request.get_json()
    
    if 'name' in data:
        course.name = data['name']
    if 'code' in data:
        course.code = data['code']
    if 'credits' in data:
        course.credits = data['credits']
    if 'department_id' in data:
        department = Department.query.get(data['department_id'])
        if not department:
            return {
                'error': {
                    'code': 'BAD_REQUEST',
                    'message': f'Department with id {data["department_id"]} not found'
                }
            }, 400
        course.department_id = data['department_id']
    
    db.session.commit()
    return jsonify(course.to_dict()), 200


@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    """Delete a course"""
    course = Course.query.get(course_id)
    if not course:
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Course with id {course_id} not found'
            }
        }, 404
    
    db.session.delete(course)
    db.session.commit()
    return '', 204


@app.route('/api/departments', methods=['GET'])
def list_departments():
    """List all departments"""
    departments = Department.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'head_of_dept': d.head_of_dept,
        'budget': d.budget,
        'course_count': len(d.courses)
    } for d in departments]), 200


@app.route('/api/departments', methods=['POST'])
def create_department():
    """Create a new department"""
    data = request.get_json()
    
    if 'name' not in data:
        return {
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Missing required field: name'
            }
        }, 400
    
    department = Department(
        name=data['name'],
        head_of_dept=data.get('head_of_dept'),
        budget=data.get('budget', 0.0)
    )
    
    db.session.add(department)
    db.session.commit()
    
    return jsonify({
        'id': department.id,
        'name': department.name,
        'head_of_dept': department.head_of_dept,
        'budget': department.budget
    }), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)