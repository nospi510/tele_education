from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from app import db
from app.models.user import User, UserRole
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from flasgger import swag_from
import bcrypt
import logging

# Configurer les logs
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET"])
def register_page():
    logger.debug("Accessing register page")
    if session.get("user_id"):
        if session.get("role") == "professor":
            logger.debug("User is professor, redirecting to /sessions/create")
            return redirect("/sessions/create")
        else:
            session_id = request.args.get("session_id", "1")
            logger.debug(f"User is viewer, redirecting to /sessions/viewer?session_id={session_id}")
            return redirect(f"/sessions/viewer?session_id={session_id}")
    return render_template("register.html")

@auth_bp.route("/register", methods=["POST"])
@swag_from({
    "tags": ["Authentication"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "example": "user@example.com"},
                    "password": {"type": "string", "example": "password123"},
                    "name": {"type": "string", "example": "John Doe"},
                    "role": {"type": "string", "enum": ["professor", "viewer"], "example": "viewer"}
                },
                "required": ["email", "password", "name", "role"]
            }
        }
    ],
    "responses": {
        "201": {"description": "User registered successfully"},
        "400": {"description": "Invalid input or email already exists"},
        "500": {"description": "Server error"}
    }
})
def register():
    try:
        logger.debug("Received POST request to /auth/register")
        data = request.get_json()
        logger.debug(f"Request data: {data}")

        if not data:
            logger.error("No JSON data provided")
            return jsonify({"message": "No JSON data provided"}), 400

        if not all(k in data for k in ("email", "password", "name", "role")):
            logger.error("Missing required fields")
            return jsonify({"message": "Missing required fields"}), 400

        if data["role"] not in ["professor", "viewer"]:
            logger.error(f"Invalid role: {data['role']}")
            return jsonify({"message": "Invalid role"}), 400

        if User.query.filter_by(email=data["email"]).first():
            logger.error(f"Email already exists: {data['email']}")
            return jsonify({"message": "Email already exists"}), 400

        hashed_password = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt())
        user = User(
            email=data["email"],
            password=hashed_password.decode("utf-8"),
            name=data["name"],
            role=UserRole(data["role"])
        )
        db.session.add(user)
        db.session.commit()

        logger.debug(f"User registered successfully: {data['email']}")
        return jsonify({"message": "User registered successfully"}), 201

    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        db.session.rollback()
        return jsonify({"message": f"Server error: {str(e)}"}), 500

@auth_bp.route("/login", methods=["GET"])
def login_page():
    logger.debug("Accessing login page")
    if session.get("user_id"):
        if session.get("role") == "professor":
            logger.debug("User is professor, redirecting to /sessions/create")
            return redirect("/sessions/create")
        else:
            session_id = request.args.get("session_id", "1")
            logger.debug(f"User is viewer, redirecting to /sessions/viewer?session_id={session_id}")
            return redirect(f"/sessions/viewer?session_id={session_id}")
    return render_template("login.html")

@auth_bp.route("/login", methods=["POST"])
@swag_from({
    "tags": ["Authentication"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "example": "user@example.com"},
                    "password": {"type": "string", "example": "password123"}
                },
                "required": ["email", "password"]
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Login successful",
            "schema": {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"}
                }
            }
        },
        "401": {"description": "Invalid credentials"},
        "500": {"description": "Server error"}
    }
})
def login():
    try:
        logger.debug("Received POST request to /auth/login")
        data = request.get_json()
        logger.debug(f"Request data: {data}")

        if not data or not all(k in data for k in ("email", "password")):
            logger.error("Missing required fields")
            return jsonify({"message": "Missing required fields"}), 400

        user = User.query.filter_by(email=data["email"]).first()

        if not user or not bcrypt.checkpw(data["password"].encode("utf-8"), user.password.encode("utf-8")):
            logger.error(f"Invalid credentials for email: {data['email']}")
            return jsonify({"message": "Invalid credentials"}), 401

        session["user_id"] = user.id
        session["role"] = user.role.value
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role.value}
        )
        logger.debug(f"User logged in: {data['email']}")
        return jsonify({"access_token": access_token}), 200

    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        return jsonify({"message": f"Server error: {str(e)}"}), 500

@auth_bp.route("/logout", methods=["GET"])
def logout():
    logger.debug("Logging out user")
    session.pop("user_id", None)
    session.pop("role", None)
    return redirect(url_for("auth.login_page"))

@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
@swag_from({
    "tags": ["Authentication"],
    "security": [{"Bearer": []}],
    "responses": {
        "200": {
            "description": "User profile retrieved",
            "schema": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "name": {"type": "string"},
                    "role": {"type": "string"}
                }
            }
        },
        "401": {"description": "Unauthorized"},
        "500": {"description": "Server error"}
    }
})
def get_profile():
    try:
        logger.debug("Accessing profile")
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        user = User.query.get(int(current_user_id))
        if not user:
            logger.error(f"User not found for id: {current_user_id}")
            return jsonify({"message": "User not found"}), 404
        logger.debug(f"Profile retrieved for user: {user.email}")
        return jsonify({
            "email": user.email,
            "name": user.name,
            "role": claims["role"]
        }), 200
    except Exception as e:
        logger.error(f"Error in get_profile: {str(e)}")
        return jsonify({"message": f"Server error: {str(e)}"}), 500