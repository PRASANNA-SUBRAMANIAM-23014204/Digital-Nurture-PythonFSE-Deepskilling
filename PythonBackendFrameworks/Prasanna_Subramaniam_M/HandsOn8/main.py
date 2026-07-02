from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uvicorn
import math

from database import Base, engine, get_db
from models import User, Department
from schemas import (
    CourseCreate, CourseUpdate, CourseResponse,
    StudentCreate, StudentUpdate, StudentResponse,
    EnrollmentCreate, EnrollmentResponse,
    DepartmentResponse, DepartmentCreate, DepartmentUpdate,
    PaginatedResponse, ErrorResponse
)
from dependencies import get_current_user
from auth import router as auth_router
from crud import (
    get_course, get_courses, get_courses_count, create_course,
    update_course, delete_course,
    get_student, get_students, create_student, update_student, delete_student,
    get_enrollment, get_enrollments, create_enrollment, delete_enrollment,
    get_course_students, get_department, get_departments, get_departments_count
)

app = FastAPI(
    title="Course Management API",
    description="""
    ## Course Management System API - v1
    
    This RESTful API provides endpoints for managing a college course management system.
    
    ### REST Principles Followed:
    - **Resource-based URLs**: Uses nouns, not verbs (`/api/v1/courses` not `/api/v1/getCourses`)
    - **HTTP Methods**: GET (read), POST (create), PUT (full update), PATCH (partial update), DELETE (remove)
    - **Status Codes**: 
        - 200 OK for successful GET, PUT, PATCH
        - 201 Created for POST with Location header
        - 204 No Content for DELETE
        - 400 Bad Request for validation errors
        - 401 Unauthorized for missing/invalid auth
        - 404 Not Found for missing resources
        - 409 Conflict for duplicate resources
        - 422 Unprocessable Entity for schema errors
    - **Pagination**: Offset-based pagination with metadata (count, next, previous, results)
    - **Versioning**: URL-based versioning (`/api/v1/`)
    - **Standardized Errors**: Consistent error response format
    
    ### Features:
    - Courses, Students, Enrollments, Departments management
    - JWT-based authentication
    - Pagination and filtering
    - Search functionality
    - Background tasks for email notifications
    
    ### Authentication:
    Use the `/api/v1/auth/login` endpoint to get a JWT token, then include it in the Authorization header:
    `Authorization: Bearer <your_token>`
    """,
    version="1.0.0",
    contact={
        "name": "Course Management API Support",
        "email": "support@coursemanager.com",
        "url": "https://coursemanager.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Location"],
)

# Include authentication router
app.include_router(auth_router)


@app.on_event("startup")
async def startup():
    """Create database tables on startup"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# --- Standardized Error Handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Standardized error response format"""
    error_code = "UNKNOWN_ERROR"
    if exc.status_code == 400:
        error_code = "BAD_REQUEST"
    elif exc.status_code == 401:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        error_code = "FORBIDDEN"
    elif exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 409:
        error_code = "CONFLICT"
    elif exc.status_code == 422:
        error_code = "VALIDATION_ERROR"
    elif exc.status_code == 500:
        error_code = "INTERNAL_SERVER_ERROR"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": exc.detail,
                "field": None
            }
        }
    )


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Course Management API is running",
        "version": "1.0.0",
        "docs": "/docs",
        "api": "/api/v1/"
    }


# --- Department Endpoints ---
@app.get(
    "/api/v1/departments",
    response_model=PaginatedResponse[DepartmentResponse],
    tags=["Departments"],
    summary="List all departments",
    description="Get a paginated list of all departments"
)
async def list_departments(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List all departments with pagination"""
    skip = (page - 1) * page_size
    departments = await get_departments(db, skip, page_size)
    total = await get_departments_count(db)
    
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    base_url = "/api/v1/departments"
    next_url = f"{base_url}?page={page + 1}&page_size={page_size}" if page < total_pages else None
    prev_url = f"{base_url}?page={page - 1}&page_size={page_size}" if page > 1 else None
    
    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": departments
    }


@app.get(
    "/api/v1/departments/{department_id}",
    response_model=DepartmentResponse,
    tags=["Departments"],
    summary="Get department by ID",
    description="Retrieve a single department by its ID"
)
async def get_department_by_id(
    department_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get department by ID"""
    department = await get_department(db, department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with id {department_id} does not exist"
        )
    return department


@app.post(
    "/api/v1/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Departments"],
    summary="Create a new department",
    description="Create a new department (requires authentication)"
)
async def create_new_department(
    department: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new department"""
    db_department = Department(**department.model_dump())
    db.add(db_department)
    await db.commit()
    await db.refresh(db_department)
    
    # Return with Location header
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=DepartmentResponse.model_validate(db_department).model_dump(),
        headers={"Location": f"/api/v1/departments/{db_department.id}"}
    )


@app.put(
    "/api/v1/departments/{department_id}",
    response_model=DepartmentResponse,
    tags=["Departments"],
    summary="Full update department",
    description="Replace all fields of a department (requires authentication)"
)
async def update_department_by_id(
    department_id: int,
    department_update: DepartmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Full update department details"""
    db_department = await get_department(db, department_id)
    if not db_department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with id {department_id} does not exist"
        )
    
    update_data = department_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_department, key, value)
    
    await db.commit()
    await db.refresh(db_department)
    return db_department


@app.delete(
    "/api/v1/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Departments"],
    summary="Delete department",
    description="Delete a department (requires authentication)"
)
async def delete_department_by_id(
    department_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a department"""
    db_department = await get_department(db, department_id)
    if not db_department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with id {department_id} does not exist"
        )
    await db.delete(db_department)
    await db.commit()
    return None


# --- Course Endpoints ---
@app.get(
    "/api/v1/courses",
    response_model=PaginatedResponse[CourseResponse],
    tags=["Courses"],
    summary="List all courses",
    description="Get a paginated list of courses with optional filtering and search"
)
async def list_courses(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    search: Optional[str] = Query(None, description="Search by course name or code"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all courses with pagination, filtering, and search
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page
    - **department_id**: Filter by department
    - **search**: Search in course name and code (case-insensitive)
    """
    skip = (page - 1) * page_size
    courses = await get_courses(db, skip, page_size, department_id, search)
    total = await get_courses_count(db, department_id, search)
    
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    # Build next/previous URLs
    base_url = "/api/v1/courses"
    params = []
    if department_id:
        params.append(f"department_id={department_id}")
    if search:
        params.append(f"search={search}")
    params.append(f"page_size={page_size}")
    
    param_string = "&".join(params)
    next_url = f"{base_url}?{param_string}&page={page + 1}" if page < total_pages else None
    prev_url = f"{base_url}?{param_string}&page={page - 1}" if page > 1 else None
    
    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": courses
    }


@app.get(
    "/api/v1/courses/{course_id}",
    response_model=CourseResponse,
    tags=["Courses"],
    summary="Get course by ID",
    description="Retrieve a single course by its ID"
)
async def get_course_by_id(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get course by ID"""
    course = await get_course(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} does not exist"
        )
    return course


@app.get(
    "/api/v1/courses/{course_id}/students",
    response_model=List[StudentResponse],
    tags=["Courses"],
    summary="Get students in a course",
    description="Get all students enrolled in a specific course"
)
async def get_course_students_endpoint(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all students enrolled in a course"""
    course = await get_course(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} does not exist"
        )
    return await get_course_students(db, course_id)


@app.post(
    "/api/v1/courses",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Courses"],
    summary="Create a new course",
    description="Create a new course (requires authentication)",
    response_description="The created course"
)
async def create_new_course(
    course: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new course
    
    - **name**: Course name
    - **code**: Unique course code  
    - **credits**: Number of credits
    - **department_id**: ID of the department offering the course
    """
    # Check if department exists
    department = await get_department(db, course.department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with id {course.department_id} does not exist"
        )
    
    new_course = await create_course(db, course)
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=CourseResponse.model_validate(new_course).model_dump(),
        headers={"Location": f"/api/v1/courses/{new_course.id}"}
    )


@app.put(
    "/api/v1/courses/{course_id}",
    response_model=CourseResponse,
    tags=["Courses"],
    summary="Full update course",
    description="Replace all fields of a course (requires authentication)"
)
async def update_course_by_id(
    course_id: int,
    course_update: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Full update course details - all fields required"""
    course = await update_course(db, course_id, course_update)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} does not exist"
        )
    return course


@app.patch(
    "/api/v1/courses/{course_id}",
    response_model=CourseResponse,
    tags=["Courses"],
    summary="Partial update course",
    description="Partially update a course (requires authentication)"
)
async def patch_course_by_id(
    course_id: int,
    course_update: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Partial update course details - only provided fields are updated"""
    course = await update_course(db, course_id, course_update)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} does not exist"
        )
    return course


@app.delete(
    "/api/v1/courses/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Courses"],
    summary="Delete course",
    description="Delete a course (requires authentication)"
)
async def delete_course_by_id(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a course"""
    course = await delete_course(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} does not exist"
        )
    return None


# --- Student Endpoints ---
@app.get(
    "/api/v1/students",
    response_model=PaginatedResponse[StudentResponse],
    tags=["Students"],
    summary="List all students",
    description="Get a paginated list of all students"
)
async def list_students(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List all students with pagination"""
    skip = (page - 1) * page_size
    students = await get_students(db, skip, page_size)
    # In a real app, you'd have a count function
    total = len(students) + (page - 1) * page_size  # Simplified for demo
    
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    base_url = "/api/v1/students"
    next_url = f"{base_url}?page={page + 1}&page_size={page_size}" if page < total_pages else None
    prev_url = f"{base_url}?page={page - 1}&page_size={page_size}" if page > 1 else None
    
    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": students
    }


@app.get(
    "/api/v1/students/{student_id}",
    response_model=StudentResponse,
    tags=["Students"],
    summary="Get student by ID",
    description="Retrieve a single student by their ID"
)
async def get_student_by_id(
    student_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get student by ID"""
    student = await get_student(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} does not exist"
        )
    return student


@app.post(
    "/api/v1/students",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Students"],
    summary="Create a new student",
    description="Create a new student (requires authentication)"
)
async def create_new_student(
    student: StudentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new student"""
    # Check if department exists
    department = await get_department(db, student.department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with id {student.department_id} does not exist"
        )
    
    new_student = await create_student(db, student)
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=StudentResponse.model_validate(new_student).model_dump(),
        headers={"Location": f"/api/v1/students/{new_student.id}"}
    )


@app.put(
    "/api/v1/students/{student_id}",
    response_model=StudentResponse,
    tags=["Students"],
    summary="Full update student",
    description="Replace all fields of a student (requires authentication)"
)
async def update_student_by_id(
    student_id: int,
    student_update: StudentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Full update student details"""
    student = await update_student(db, student_id, student_update)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} does not exist"
        )
    return student


@app.patch(
    "/api/v1/students/{student_id}",
    response_model=StudentResponse,
    tags=["Students"],
    summary="Partial update student",
    description="Partially update a student (requires authentication)"
)
async def patch_student_by_id(
    student_id: int,
    student_update: StudentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Partial update student details"""
    student = await update_student(db, student_id, student_update)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} does not exist"
        )
    return student


@app.delete(
    "/api/v1/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Students"],
    summary="Delete student",
    description="Delete a student (requires authentication)"
)
async def delete_student_by_id(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a student"""
    student = await delete_student(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} does not exist"
        )
    return None


# --- Enrollment Endpoints ---
@app.get(
    "/api/v1/enrollments",
    response_model=PaginatedResponse[EnrollmentResponse],
    tags=["Enrollments"],
    summary="List all enrollments",
    description="Get a paginated list of all enrollments"
)
async def list_enrollments(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List all enrollments with pagination"""
    skip = (page - 1) * page_size
    enrollments = await get_enrollments(db, skip, page_size)
    total = len(enrollments) + (page - 1) * page_size  # Simplified for demo
    
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    base_url = "/api/v1/enrollments"
    next_url = f"{base_url}?page={page + 1}&page_size={page_size}" if page < total_pages else None
    prev_url = f"{base_url}?page={page - 1}&page_size={page_size}" if page > 1 else None
    
    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": enrollments
    }


@app.get(
    "/api/v1/enrollments/{enrollment_id}",
    response_model=EnrollmentResponse,
    tags=["Enrollments"],
    summary="Get enrollment by ID",
    description="Retrieve a single enrollment by its ID"
)
async def get_enrollment_by_id(
    enrollment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get enrollment by ID"""
    enrollment = await get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment with id {enrollment_id} does not exist"
        )
    return enrollment


@app.post(
    "/api/v1/enrollments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Enrollments"],
    summary="Create a new enrollment",
    description="Create a new enrollment with background email notification (requires authentication)"
)
async def create_new_enrollment(
    enrollment: EnrollmentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enroll a student in a course
    
    Creates a new enrollment with background task for email confirmation
    """
    # Check if student exists
    student = await get_student(db, enrollment.student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {enrollment.student_id} does not exist"
        )
    
    # Check if course exists
    course = await get_course(db, enrollment.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {enrollment.course_id} does not exist"
        )
    
    # Create enrollment
    db_enrollment = await create_enrollment(
        db, 
        enrollment.student_id, 
        enrollment.course_id,
        enrollment.grade
    )
    
    if not db_enrollment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this course"
        )
    
    # Add background task to send confirmation email
    background_tasks.add_task(
        send_confirmation_email,
        student.email,
        course.name
    )
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=EnrollmentResponse.model_validate(db_enrollment).model_dump(),
        headers={"Location": f"/api/v1/enrollments/{db_enrollment.id}"}
    )


@app.delete(
    "/api/v1/enrollments/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Enrollments"],
    summary="Delete enrollment",
    description="Delete an enrollment (requires authentication)"
)
async def delete_enrollment_by_id(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an enrollment"""
    enrollment = await delete_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment with id {enrollment_id} does not exist"
        )
    return None


def send_confirmation_email(email: str, course_name: str):
    """Background task to send confirmation email"""
    print(f"Sending confirmation email to {email} for course: {course_name}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)