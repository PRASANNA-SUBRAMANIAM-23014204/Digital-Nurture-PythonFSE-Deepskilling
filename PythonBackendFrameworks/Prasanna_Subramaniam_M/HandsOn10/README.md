# Hands-On 10: Microservices Architecture

## Course Management System - Microservices Implementation

### Architecture Overview

This project demonstrates a microservices-based architecture for a Course Management System with three independent services and an API Gateway.

### Services

#### 1. API Gateway (Port 5000)
- Routes requests to appropriate services
- Handles authentication header forwarding
- Provides health check endpoint
- Implements request logging

#### 2. Course Service (Port 5001)
- Manages departments and courses
- Owns its own database (courses.db)
- Endpoints: /api/courses/*, /api/departments/*

#### 3. Student Service (Port 5002)
- Manages students and enrollments
- Owns its own database (students.db)
- Communicates with Course Service via HTTP
- Endpoints: /api/students/*

#### 4. Auth Service (Port 5003)
- Handles authentication and authorization
- Owns its own database (auth.db)
- JWT token generation and validation
- Endpoints: /api/auth/*

### Service Communication

#### Synchronous Communication (HTTP)
- Student Service → Course Service: Verify course exists
- API Gateway → Services: Route requests

#### Communication Flow for Enrollment:
1. Client → API Gateway: POST /api/students/1/enroll
2. API Gateway → Student Service: Forward request
3. Student Service → Course Service: GET /api/courses/1
4. Course Service → Student Service: Course exists
5. Student Service: Creates enrollment
6. Student Service → API Gateway: Success response
7. API Gateway → Client: Response

### Running the Services

#### 1. Start Course Service
```bash
cd course_service
python app.py