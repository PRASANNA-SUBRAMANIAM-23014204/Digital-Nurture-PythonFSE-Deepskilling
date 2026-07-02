from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# User Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


# Department Schemas
class DepartmentBase(BaseModel):
    name: str
    head_of_dept: Optional[str] = None
    budget: Optional[float] = 0.0


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    head_of_dept: Optional[str] = None
    budget: Optional[float] = None


class DepartmentResponse(DepartmentBase):
    id: int

    class Config:
        from_attributes = True


# Course Schemas
class CourseBase(BaseModel):
    name: str
    code: str
    credits: int
    department_id: int


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = None
    department_id: Optional[int] = None


class CourseResponse(CourseBase):
    id: int
    department: Optional[DepartmentResponse] = None

    class Config:
        from_attributes = True


class CourseWithStudentsResponse(CourseResponse):
    students: List['StudentResponse'] = []


# Student Schemas
class StudentBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    department_id: int
    enrollment_year: Optional[int] = None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None
    enrollment_year: Optional[int] = None


class StudentResponse(StudentBase):
    id: int

    class Config:
        from_attributes = True


# Enrollment Schemas
class EnrollmentBase(BaseModel):
    student_id: int
    course_id: int
    grade: Optional[str] = None


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    enrollment_date: datetime
    grade: Optional[str] = None
    student: Optional[StudentResponse] = None
    course: Optional[CourseResponse] = None

    class Config:
        from_attributes = True


# Update forward references
CourseWithStudentsResponse.model_rebuild()