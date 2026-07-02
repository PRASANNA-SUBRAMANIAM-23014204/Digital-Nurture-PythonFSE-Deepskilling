"""
Student Service - Manages students and enrollments

Port: 5002
Endpoints:
- GET /health - Health check
- GET /api/students - List all students
- GET /api/students/<id> - Get student by ID
- POST /api/students - Create a new student
- PUT /api/students/<id> - Update student
- DELETE /api/students/<id> - Delete student
- POST /api/students/<id>/enroll - Enroll student in a course
- GET /api/students/<id>/courses - Get courses for a student
"""

from flask import Flask, request, jsonify
import requests
from database import db, init_app
from models import Student, Enrollment
import os

# Create Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'student-service-secret'

# Course Service URL
COURSE_SERVICE_URL = os.getenv('COURSE_SERVICE_URL', 'http://localhost:5001')

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
        'service': 'student_service',
        'port': 5002
    }


def verify_course_exists(course_id):
    """Verify course exists in Course Service"""
    try:
        response = requests.get(
            f"{COURSE_SERVICE_URL}/api/courses/{course_id}",
            timeout=5
        )
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


@app.route('/api/students', methods=['GET'])
def list_students():
    """List all students"""
    students = Student.query.all()
    return jsonify([student.to_dict() for student in students]), 200


@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Get a student by ID"""
    student = Student.query.get(student_id)
    if not student:
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Student with id {student_id} not found'
            }
        }, 404
    return jsonify(student.to_dict()), 200


@app.route('/api/students', methods=['POST'])
def create_student():
    """Create a new student"""
    data = request.get_json()
    
    required_fields = ['first_name', 'last_name', 'email', 'department_id']
    for field in required_fields:
        if field not in data:
            return {
                'error': {
                    'code': 'BAD_REQUEST',
                    'message': f'Missing required field: {field}'
                }
            }, 400
    
    # Check if email already exists
    existing = Student.query.filter_by(email=data['email']).first()
    if existing:
        return {
            'error': {
                'code': 'CONFLICT',
                'message': f'Student with email {data["email"]} already exists'
            }
        }, 409
    
    student = Student(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        department_id=data['department_id'],
        enrollment_year=data.get('enrollment_year')
    )
    
    db.session.add(student)
    db.session.commit()
    
    return jsonify(student.to_dict()), 201


@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """Update a student"""
    student = Student.query.get(student_id)
    if not student:
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Student with id {student_id} not found'
            }
        }, 404
    
    data = request.get_json()
    
    if 'first_name' in data:
        student.first_name = data['first_name']
    if 'last_name' in data:
        student.last_name = data['last_name']
    if 'email' in data:
        # Check if email already exists for another student
        existing = Student.query.filter(
            Student.email == data['email'],
            Student.id != student_id
        ).first()
        if existing:
            return {
                'error': {
                    'code': 'CONFLICT',
                    'message': f'Student with email {data["email"]} already exists'
                }
            }, 409
        student.email = data['email']
    if 'department_id' in data:
        student.department_id = data['department_id']
    if 'enrollment_year' in data:
        student.enrollment_year = data['enrollment_year']
    
    db.session.commit()
    return jsonify(student.to_dict()), 200


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student"""
    student = Student.query.get(student_id)
    if not student:
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Student with id {student_id} not found'
            }
        }, 404
    
    db.session.delete(student)
    db.session.commit()
    return '', 204


@app.route('/api/students/<int:student_id>/enroll', methods=['POST'])
def enroll_student(student_id):
    """
    Enroll a student in a course
    
    This endpoint demonstrates inter-service communication:
    1. Student Service receives the enrollment request
    2. Calls Course Service to verify the course exists
    3. Creates the enrollment if the course exists
    """
    student = Student.query.get(student_id)
    if not student:
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Student with id {student_id} not found'
            }
        }, 404
    
    data = request.get_json()
    
    if 'course_id' not in data:
        return {
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Missing required field: course_id'
            }
        }, 400
    
    course_id = data['course_id']
    
    # Check if course exists (Inter-service communication)
    course_exists = verify_course_exists(course_id)
    if not course_exists:
        # If Course Service is unavailable, return 503
        try:
            response = requests.get(f"{COURSE_SERVICE_URL}/api/courses/{course_id}", timeout=2)
            if response.status_code == 404:
                return {
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': f'Course with id {course_id} not found'
                    }
                }, 404
        except requests.exceptions.ConnectionError:
            return {
                'error': {
                    'code': 'SERVICE_UNAVAILABLE',
                    'message': 'Course Service is unavailable. Please try again later.'
                }
            }, 503
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(
        student_id=student_id,
        course_id=course_id
    ).first()
    
    if existing:
        return {
            'error': {
                'code': 'CONFLICT',
                'message': f'Student already enrolled in course {course_id}'
            }
        }, 409
    
    enrollment = Enrollment(
        student_id=student_id,
        course_id=course_id,
        grade=data.get('grade')
    )
    
    db.session.add(enrollment)
    db.session.commit()
    
    return jsonify({
        'id': enrollment.id,
        'student_id': enrollment.student_id,
        'course_id': enrollment.course_id,
        'enrollment_date': enrollment.enrollment_date.isoformat(),
        'grade': enrollment.grade
    }), 201


@app.route('/api/students/<int:student_id>/courses', methods=['GET'])
def get_student_courses(student_id):
    """Get all courses for a student"""
    student = Student.query.get(student_id)
    if not student:
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Student with id {student_id} not found'
            }
        }, 404
    
    enrollments = Enrollment.query.filter_by(student_id=student_id).all()
    
    # Get course details from Course Service
    courses = []
    for enrollment in enrollments:
        try:
            response = requests.get(
                f"{COURSE_SERVICE_URL}/api/courses/{enrollment.course_id}",
                timeout=3
            )
            if response.status_code == 200:
                course_data = response.json()
                courses.append({
                    **course_data,
                    'enrollment_date': enrollment.enrollment_date.isoformat(),
                    'grade': enrollment.grade
                })
            else:
                courses.append({
                    'id': enrollment.course_id,
                    'name': 'Course details unavailable',
                    'enrollment_date': enrollment.enrollment_date.isoformat(),
                    'grade': enrollment.grade
                })
        except:
            courses.append({
                'id': enrollment.course_id,
                'name': 'Course service unavailable',
                'enrollment_date': enrollment.enrollment_date.isoformat(),
                'grade': enrollment.grade
            })
    
    return jsonify(courses), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)