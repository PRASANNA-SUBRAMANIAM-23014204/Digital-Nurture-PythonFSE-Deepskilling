from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uvicorn

from database import Base, engine, get_db
from models import User
from schemas import (
    CourseCreate, CourseUpdate, CourseResponse, CourseWithStudentsResponse,
    StudentCreate, StudentUpdate, StudentResponse,
    EnrollmentCreate, EnrollmentResponse,
    DepartmentResponse, DepartmentCreate, DepartmentUpdate
)
from security import hash_password, verify_password, create_access_token
from dependencies import get_current_user
from auth import router as auth_router
from crud import (
    get_course, get_courses, get_courses_count, create_course,
    update_course, delete_course,
    get_student, get_students, create_student, update_student, delete_student,
    get_enrollment, get_enrollments, create_enrollment, delete_enrollment,
    get_course_students, get_department, get_departments
)

app = FastAPI(
    title="Course Management API",
    description="""
    ## Course Management System API
    
    This API provides endpoints for managing a college course management system.
    
    ### Features:
    * **Courses** - Create, read, update, and delete courses
    * **Students** - Manage student records
    * **Enrollments** - Enroll students in courses
    * **Departments** - Manage academic departments
    * **Authentication** - JWT-based authentication with bcrypt password hashing
    
    ### Authentication Flow:
    1. Register a new user at `/api/v1/auth/register`
    2. Login at `/api/v1/auth/login` to get a JWT token
    3. Use the token in the Authorization header: `Bearer <token>`
    
    ### Response Standards:
    - 200 OK: Successful GET, PUT, PATCH requests
    - 201 Created: Successful POST requests with Location header
    - 204 No Content: Successful DELETE requests
    - 400 Bad Request: Validation errors
    - 401 Unauthorized: Missing or invalid authentication
    - 404 Not Found: Resource not found
    - 409 Conflict: Duplicate resource (e.g., duplicate email)
    - 422 Unprocessable Entity: Schema validation errors
    """,
    version="1.0.0",
    contact={
        "name": "Course Management API Support",
        "email": "support@coursemanager.com",
        "url": "https://coursemanager.com",
    },
    license_info={
        "name": "MIT",
    }
)

# Configure CORS - Allow frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
app.include_router(auth_router)


@app.on_event("startup")
async def startup():
    """Create database tables on startup"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def root():
    return {"message": "Course Management API is running"}


# --- Department Endpoints ---
@app.get("/api/v1/departments", response_model=list[DepartmentResponse], tags=["Departments"])
async def list_departments(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """List all departments with pagination"""
    return await get_departments(db, skip, limit)


@app.get("/api/v1/departments/{department_id}", response_model=DepartmentResponse, tags=["Departments"])
async def get_department_by_id(
    department_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get department by ID"""
    department = await get_department(db, department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with id {department_id} not found"
        )
    return department


@app.post("/api/v1/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, tags=["Departments"])
async def create_new_department(
    department: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new department (requires authentication)"""
    db_department = Department(**department.model_dump())
    db.add(db_department)
    await db.commit()
    await db.refresh(db_department)
    return db_department


@app.put("/api/v1/departments/{department_id}", response_model=DepartmentResponse, tags=["Departments"])
async def update_department_by_id(
    department_id: int,
    department_update: DepartmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update department details (requires authentication)"""
    db_department = await get_department(db, department_id)
    if not db_department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with id {department_id} not found"
        )
    
    update_data = department_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_department, key, value)
    
    await db.commit()
    await db.refresh(db_department)
    return db_department


# --- Course Endpoints ---
@app.get("/api/v1/courses", response_model=list[CourseResponse], tags=["Courses"])
async def list_courses(
    skip: int = 0,
    limit: int = 10,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all courses with pagination and filtering
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **department_id**: Filter by department ID
    - **search**: Search by course name or code (case-insensitive)
    """
    return await get_courses(db, skip, limit, department_id, search)


@app.get("/api/v1/courses/{course_id}", response_model=CourseResponse, tags=["Courses"])
async def get_course_by_id(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get course by ID"""
    course = await get_course(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )
    return course


@app.get("/api/v1/courses/{course_id}/students", response_model=list[StudentResponse], tags=["Courses"])
async def get_course_students_endpoint(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all students enrolled in a course"""
    course = await get_course(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )
    return await get_course_students(db, course_id)


@app.post("/api/v1/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED, tags=["Courses"])
async def create_new_course(
    course: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new course (requires authentication)
    
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
            detail=f"Department with id {course.department_id} not found"
        )
    
    return await create_course(db, course)


@app.put("/api/v1/courses/{course_id}", response_model=CourseResponse, tags=["Courses"])
async def update_course_by_id(
    course_id: int,
    course_update: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update course details (requires authentication)"""
    course = await update_course(db, course_id, course_update)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )
    return course


@app.patch("/api/v1/courses/{course_id}", response_model=CourseResponse, tags=["Courses"])
async def patch_course_by_id(
    course_id: int,
    course_update: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Partially update course details (requires authentication)"""
    course = await update_course(db, course_id, course_update)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )
    return course


@app.delete("/api/v1/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Courses"])
async def delete_course_by_id(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a course (requires authentication)
    
    Returns 204 No Content on success
    """
    course = await delete_course(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )
    return None


# --- Student Endpoints ---
@app.get("/api/v1/students", response_model=list[StudentResponse], tags=["Students"])
async def list_students(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """List all students with pagination"""
    return await get_students(db, skip, limit)


@app.get("/api/v1/students/{student_id}", response_model=StudentResponse, tags=["Students"])
async def get_student_by_id(
    student_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get student by ID"""
    student = await get_student(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} not found"
        )
    return student


@app.post("/api/v1/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED, tags=["Students"])
async def create_new_student(
    student: StudentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new student (requires authentication)"""
    # Check if department exists
    department = await get_department(db, student.department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with id {student.department_id} not found"
        )
    return await create_student(db, student)


@app.put("/api/v1/students/{student_id}", response_model=StudentResponse, tags=["Students"])
async def update_student_by_id(
    student_id: int,
    student_update: StudentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update student details (requires authentication)"""
    student = await update_student(db, student_id, student_update)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} not found"
        )
    return student


@app.delete("/api/v1/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Students"])
async def delete_student_by_id(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a student (requires authentication)"""
    student = await delete_student(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} not found"
        )
    return None


# --- Enrollment Endpoints ---
@app.get("/api/v1/enrollments", response_model=list[EnrollmentResponse], tags=["Enrollments"])
async def list_enrollments(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """List all enrollments with pagination"""
    return await get_enrollments(db, skip, limit)


@app.get("/api/v1/enrollments/{enrollment_id}", response_model=EnrollmentResponse, tags=["Enrollments"])
async def get_enrollment_by_id(
    enrollment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get enrollment by ID"""
    enrollment = await get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment with id {enrollment_id} not found"
        )
    return enrollment


@app.post("/api/v1/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED, tags=["Enrollments"])
async def create_new_enrollment(
    enrollment: EnrollmentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enroll a student in a course (requires authentication)
    
    Creates a new enrollment with background task for email confirmation
    """
    # Check if student exists
    student = await get_student(db, enrollment.student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {enrollment.student_id} not found"
        )
    
    # Check if course exists
    course = await get_course(db, enrollment.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {enrollment.course_id} not found"
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
    
    return db_enrollment


@app.delete("/api/v1/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Enrollments"])
async def delete_enrollment_by_id(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an enrollment (requires authentication)"""
    enrollment = await delete_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment with id {enrollment_id} not found"
        )
    return None


def send_confirmation_email(email: str, course_name: str):
    """Background task to send confirmation email"""
    print(f"Sending confirmation email to {email} for course: {course_name}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)