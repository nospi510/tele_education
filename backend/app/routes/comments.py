from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.session import Session, SessionStatus
from app.models.user import User, UserRole
from app.models.comment import Comment
from flasgger import swag_from

comments_bp = Blueprint("comments", __name__)

@comments_bp.route("/<int:session_id>/comments", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Comments"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID of the session"
        },
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "example": "Great explanation!"}
                },
                "required": ["content"]
            }
        }
    ],
    "responses": {
        "201": {
            "description": "Comment posted successfully",
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "content": {"type": "string"},
                    "user_name": {"type": "string"},
                    "created_at": {"type": "string"}
                }
            }
        },
        "400": {"description": "Invalid request"},
        "404": {"description": "Session not found"}
    }
})
def post_comment(session_id):
    current_user = get_jwt_identity()
    user = User.query.get(current_user["id"])
    session = Session.query.get_or_404(session_id)

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session is not active"}), 400

    data = request.get_json()
    if "content" not in data or not data["content"]:
        return jsonify({"message": "Content is required"}), 400

    comment = Comment(
        session_id=session_id,
        user_id=user.id,
        content=data["content"]
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "id": comment.id,
        "content": comment.content,
        "user_name": user.name,
        "created_at": comment.created_at.isoformat()
    }), 201

@comments_bp.route("/<int:session_id>/comments", methods=["GET"])
@jwt_required()
@swag_from({
    "tags": ["Comments"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID of the session"
        }
    ],
    "responses": {
        "200": {
            "description": "List of comments for the session",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "content": {"type": "string"},
                        "user_name": {"type": "string"},
                        "created_at": {"type": "string"},
                        "is_hidden": {"type": "boolean"}
                    }
                }
            }
        },
        "404": {"description": "Session not found"}
    }
})
def get_comments(session_id):
    Session.query.get_or_404(session_id)

    comments = Comment.query.filter_by(session_id=session_id).all()
    result = [
        {
            "id": comment.id,
            "content": comment.content,
            "user_name": comment.user.name,
            "created_at": comment.created_at.isoformat(),
            "is_hidden": comment.is_hidden
        }
        for comment in comments
    ]
    return jsonify(result), 200

@comments_bp.route("/<int:session_id>/comments/<int:comment_id>/hide", methods=["PUT"])
@jwt_required()
@swag_from({
    "tags": ["Comments"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID of the session"
        },
        {
            "name": "comment_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID of the comment to hide"
        }
    ],
    "responses": {
        "200": {"description": "Comment hidden successfully"},
        "403": {"description": "Only the professor can hide comments"},
        "404": {"description": "Session or comment not found"}
    }
})
def hide_comment(session_id, comment_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)
    comment = Comment.query.get_or_404(comment_id)

    if session.professor_id != current_user["id"]:
        return jsonify({"message": "Only the professor can hide comments"}), 403
    if comment.session_id != session_id:
        return jsonify({"message": "Comment does not belong to this session"}), 400

    comment.is_hidden = True
    comment.created_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Comment hidden successfully"}), 200