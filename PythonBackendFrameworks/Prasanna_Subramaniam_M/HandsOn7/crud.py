from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from models import Course, Department, Student, Enrollment
from schemas import CourseCreate, CourseUpdate, StudentCreate, StudentUpdate


# --- Department CRUD ---
async def get_department(db: AsyncSession, department_id: int):
    result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    return result.scalar_one_or_none()


async def get_departments(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(
        select(Department).offset(skip).limit(limit)
    )
    return result.scalars().all()


# --- Course CRUD ---
async def get_course(db: AsyncSession, course_id: int):
    result = await db.execute(
        select(Course).where(Course.id == course_id).options(selectinload(Course.department))
    )
    return result.scalar_one_or_none()


async def get_courses(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    department_id: Optional[int] = None,
    search: Optional[str] = None
):
    query = select(Course).options(selectinload(Course.department))
    
    if department_id is not None:
        query = query.where(Course.department_id == department_id)
    
    if search:
        query = query.where(
            or_(
                Course.name.ilike(f"%{search}%"),
                Course.code.ilike(f"%{search}%")
            )
        )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_courses_count(db: AsyncSession, department_id: Optional[int] = None, search: Optional[str] = None):
    query = select(func.count(Course.id))
    if department_id is not None:
        query = query.where(Course.department_id == department_id)
    if search:
        query = query.where(
            or_(
                Course.name.ilike(f"%{search}%"),
                Course.code.ilike(f"%{search}%")
            )
        )
    result = await db.execute(query)
    return result.scalar()


async def create_course(db: AsyncSession, course: CourseCreate):
    db_course = Course(**course.model_dump())
    db.add(db_course)
    await db.commit()
    await db.refresh(db_course)
    # Load department relationship
    result = await db.execute(
        select(Course).where(Course.id == db_course.id).options(selectinload(Course.department))
    )
    return result.scalar_one()


async def update_course(db: AsyncSession, course_id: int, course_update: CourseUpdate):
    db_course = await get_course(db, course_id)
    if db_course is None:
        return None
    
    update_data = course_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_course, key, value)
    
    await db.commit()
    await db.refresh(db_course)
    return db_course


async def delete_course(db: AsyncSession, course_id: int):
    db_course = await get_course(db, course_id)
    if db_course is None:
        return None
    await db.delete(db_course)
    await db.commit()
    return db_course


# --- Student CRUD ---
async def get_student(db: AsyncSession, student_id: int):
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    return result.scalar_one_or_none()


async def get_students(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(
        select(Student).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def create_student(db: AsyncSession, student: StudentCreate):
    db_student = Student(**student.model_dump())
    db.add(db_student)
    await db.commit()
    await db.refresh(db_student)
    return db_student


async def update_student(db: AsyncSession, student_id: int, student_update: StudentUpdate):
    db_student = await get_student(db, student_id)
    if db_student is None:
        return None
    
    update_data = student_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_student, key, value)
    
    await db.commit()
    await db.refresh(db_student)
    return db_student


async def delete_student(db: AsyncSession, student_id: int):
    db_student = await get_student(db, student_id)
    if db_student is None:
        return None
    await db.delete(db_student)
    await db.commit()
    return db_student


# --- Enrollment CRUD ---
async def get_enrollment(db: AsyncSession, enrollment_id: int):
    result = await db.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    return result.scalar_one_or_none()


async def get_enrollments(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(
        select(Enrollment).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def create_enrollment(db: AsyncSession, student_id: int, course_id: int, grade: Optional[str] = None):
    # Check if enrollment already exists
    result = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return None
    
    db_enrollment = Enrollment(
        student_id=student_id,
        course_id=course_id,
        grade=grade
    )
    db.add(db_enrollment)
    await db.commit()
    await db.refresh(db_enrollment)
    return db_enrollment


async def delete_enrollment(db: AsyncSession, enrollment_id: int):
    db_enrollment = await get_enrollment(db, enrollment_id)
    if db_enrollment is None:
        return None
    await db.delete(db_enrollment)
    await db.commit()
    return db_enrollment


async def get_course_students(db: AsyncSession, course_id: int):
    result = await db.execute(
        select(Student)
        .join(Enrollment)
        .where(Enrollment.course_id == course_id)
    )
    return result.scalars().all()