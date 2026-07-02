from flask import Flask, jsonify
from config import Config
from courses.routes import courses_bp


def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Register Blueprint
    app.register_blueprint(courses_bp)

    # 404 Error Handler
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "status": "error",
            "message": "Resource not found"
        }), 404

    # 500 Error Handler
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({
            "status": "error",
            "message": "Internal Server Error"
        }), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run()