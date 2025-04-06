from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, UserRole
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
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
                    "email": {"type": "string", "example": "ekasim@gmail.com"},
                    "password": {"type": "string", "example": "passer"}
                },
                "required": ["email", "password"]
            }
        }
    ],
    "responses": {
        "200": {"description": "Login successful", "schema": {
            "type": "object",
            "properties": {
                "access_token": {"type": "string"}
            }
        }},
        "401": {"description": "Invalid credentials"}
    }
})
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data["email"]).first()
    
    if not user or not bcrypt.checkpw(data["password"].encode("utf-8"), user.password.encode("utf-8")):
        return jsonify({"message": "Invalid credentials"}), 401
    
    # Créer un token avec un dictionnaire comme identité
    access_token = create_access_token(identity={"id": user.id, "role": user.role.value})
    return jsonify({"access_token": access_token}), 200

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
    current_user = get_jwt_identity()
    user = User.query.get(current_user["id"])
    return jsonify({
        "email": user.email,
        "name": user.name,
        "role": user.role.value
    }), 200