from flask import Flask, jsonify
from config import Config
from courses.routes import courses_bp

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    app.register_blueprint(courses_bp)

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({"error": "Internal Server Error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)