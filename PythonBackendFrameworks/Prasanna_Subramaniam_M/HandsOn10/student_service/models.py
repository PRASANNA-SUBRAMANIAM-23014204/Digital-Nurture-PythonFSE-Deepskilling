from database import db
from datetime import datetime


class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    department_id = db.Column(db.Integer)  # Reference to department in course service
    enrollment_year = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    enrollments = db.relationship('Enrollment', back_populates='student', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'department_id': self.department_id,
            'enrollment_year': self.enrollment_year,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, nullable=False)  # Reference to course in course service
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.String(2))
    
    student = db.relationship('Student', back_populates='enrollments')