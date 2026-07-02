from flask import Blueprint, request, jsonify

courses_bp = Blueprint(
    "courses",
    __name__,
    url_prefix="/api/courses"
)

# Temporary in-memory database
courses = []
next_id = 1


def make_response_json(data, status_code=200):
    return jsonify({
        "status": "success",
        "data": data
    }), status_code


# GET ALL COURSES
@courses_bp.route("/", methods=["GET"])
def get_courses():
    return make_response_json(courses)


# CREATE COURSE
@courses_bp.route("/", methods=["POST"])
def create_course():
    global next_id

    data = request.get_json()

    if data is None:
        return jsonify({
            "status": "error",
            "message": "Request must be JSON"
        }), 400

    required = ["name", "code", "credits"]

    for field in required:
        if field not in data:
            return jsonify({
                "status": "error",
                "message": f"{field} is required"
            }), 400

    course = {
        "id": next_id,
        "name": data["name"],
        "code": data["code"],
        "credits": data["credits"]
    }

    courses.append(course)
    next_id += 1

    return make_response_json(course, 201)


# GET COURSE BY ID
@courses_bp.route("/<int:course_id>", methods=["GET"])
def get_course(course_id):

    for course in courses:
        if course["id"] == course_id:
            return make_response_json(course)

    return jsonify({
        "status": "error",
        "message": "Course not found"
    }), 404


# UPDATE COURSE
@courses_bp.route("/<int:course_id>", methods=["PUT"])
def update_course(course_id):

    data = request.get_json()

    if data is None:
        return jsonify({
            "status": "error",
            "message": "Request must be JSON"
        }), 400

    for course in courses:
        if course["id"] == course_id:

            course["name"] = data.get("name", course["name"])
            course["code"] = data.get("code", course["code"])
            course["credits"] = data.get("credits", course["credits"])

            return make_response_json(course)

    return jsonify({
        "status": "error",
        "message": "Course not found"
    }), 404


# DELETE COURSE
@courses_bp.route("/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):

    for course in courses:
        if course["id"] == course_id:
            courses.remove(course)

            return make_response_json({
                "message": "Course deleted successfully"
            })

    return jsonify({
        "status": "error",
        "message": "Course not found"
    }), 404