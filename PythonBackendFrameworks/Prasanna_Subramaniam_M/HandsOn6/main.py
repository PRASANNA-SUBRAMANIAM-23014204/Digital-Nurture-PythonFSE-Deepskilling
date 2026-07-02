from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from sqlalchemy import select
from typing import Optional
from database import Base, engine, get_db
from models import Course
from schemas import CourseCreate, CourseUpdate, CourseResponse

app = FastAPI(
    title="Course Management API",
    version="1.0"
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "API running"}


@app.post(
    "/api/courses/",
    response_model=CourseResponse
)
async def create_course(
    course: CourseCreate,
    db: AsyncSession = Depends(get_db)
):

    new_course = Course(
        name=course.name,
        code=course.code,
        credits=course.credits,
        department_id=course.department_id
    )

    db.add(new_course)

    await db.commit()

    await db.refresh(new_course)

    return new_course
@app.get(
    "/api/courses/{course_id}",
    response_model=CourseResponse
)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )

    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    return course
@app.get(
    "/api/courses/",
    response_model=list[CourseResponse]
)
async def get_courses(
    skip: int = 0,
    limit: int = 10,
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):

    stmt = select(Course)

    # Filter by department if provided
    if department_id is not None:
        stmt = stmt.where(Course.department_id == department_id)

    # Apply pagination
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)

    courses = result.scalars().all()

    return courses
@app.put(
    "/api/courses/{course_id}",
    response_model=CourseResponse
)
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )

    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    update_data = course_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(course, key, value)

    await db.commit()
    await db.refresh(course)

    return course
@app.delete("/api/courses/{course_id}")
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )

    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    await db.delete(course)
    await db.commit()

    return {
        "message": "Course deleted successfully"
    }