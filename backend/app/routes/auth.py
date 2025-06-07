from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from app import db
from app.models.user import User, UserRole
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from flasgger import swag_from
import bcrypt

auth_bp = Blueprint("auth", __name__)

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
        "400": {"description": "Invalid input or email already exists"}
    }
})
def register():
    data = request.get_json()
    if not all(k in data for k in ("email", "password", "name", "role")):
        return jsonify({"message": "Missing required fields"}), 400
    
    if User.query.filter_by(email=data["email"]).first():
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
    
    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if session.get("user_id"):
        if session.get("role") == "professor":
            return redirect("/sessions/create")
        else:
            session_id = request.args.get("session_id", "1")
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
        "401": {"description": "Invalid credentials"}
    }
})
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data["email"]).first()

    if not user or not bcrypt.checkpw(data["password"].encode("utf-8"), user.password.encode("utf-8")):
        return jsonify({"message": "Invalid credentials"}), 401

    session["user_id"] = user.id
    session["role"] = user.role.value
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role.value}
    )
    return jsonify({"access_token": access_token}), 200

@auth_bp.route("/logout", methods=["GET"])
def logout():
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
        "401": {"description": "Unauthorized"}
    }
})
def get_profile():
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    user = User.query.get(int(current_user_id))
    return jsonify({
        "email": user.email,
        "name": user.name,
        "role": claims["role"]
    }), 200
