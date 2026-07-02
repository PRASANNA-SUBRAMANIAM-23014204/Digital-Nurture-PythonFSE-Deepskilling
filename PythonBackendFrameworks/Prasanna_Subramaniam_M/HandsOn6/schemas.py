from pydantic import BaseModel
from typing import Optional


# Used when creating a new course
class CourseCreate(BaseModel):
    name: str
    code: str
    credits: int
    department_id: int


# Used when updating a course
class CourseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = None
    department_id: Optional[int] = None


# Used for API responses
class CourseResponse(BaseModel):
    id: int
    name: str
    code: str
    credits: int
    department_id: int

    class Config:
        from_attributes = True
        
from typing import List

class DepartmentResponse(BaseModel):
    id: int
    name: str
    courses: List[CourseResponse] = []

    class Config:
        from_attributes = True        