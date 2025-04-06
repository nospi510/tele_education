from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.session import Session, SessionStatus
from app.models.user import User, UserRole
from app.models.hand_request import HandRequest, HandStatus
from flasgger import swag_from
from datetime import datetime

hand_raise_bp = Blueprint("hand_raise", __name__)

@hand_raise_bp.route("/<int:session_id>/hand-raise", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Hand Raise"],
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
        "201": {
            "description": "Hand raise request created",
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "user_id": {"type": "integer"},
                    "status": {"type": "string"}
                }
            }
        },
        "400": {"description": "Invalid request"},
        "404": {"description": "Session not found"}
    }
})
def raise_hand(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if current_user["role"] == "professor":
        return jsonify({"message": "Professors cannot raise their hand"}), 400
    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session is not active"}), 400
    if HandRequest.query.filter_by(session_id=session_id, user_id=current_user["id"], status=HandStatus.PENDING).first():
        return jsonify({"message": "You already have a pending hand raise request"}), 400

    hand_request = HandRequest(
        session_id=session_id,
        user_id=current_user["id"],
        status=HandStatus.PENDING
    )
    db.session.add(hand_request)
    db.session.commit()

    return jsonify({
        "id": hand_request.id,
        "user_id": hand_request.user_id,
        "status": hand_request.status.value
    }), 201

@hand_raise_bp.route("/<int:session_id>/hand-requests", methods=["GET"])
@jwt_required()
@swag_from({
    "tags": ["Hand Raise"],
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
            "description": "List of hand raise requests",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "user_id": {"type": "integer"},
                        "user_name": {"type": "string"},
                        "status": {"type": "string"},
                        "requested_at": {"type": "string"}
                    }
                }
            }
        },
        "403": {"description": "Only the professor can view requests"},
        "404": {"description": "Session not found"}
    }
})
def get_hand_requests(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != current_user["id"]:
        return jsonify({"message": "Only the professor can view hand requests"}), 403

    requests = HandRequest.query.filter_by(session_id=session_id).all()
    result = [
        {
            "id": req.id,
            "user_id": req.user_id,
            "user_name": req.user.name,
            "status": req.status.value,
            "requested_at": req.requested_at.isoformat()
        }
        for req in requests
    ]
    return jsonify(result), 200

@hand_raise_bp.route("/<int:session_id>/hand-grant", methods=["PUT"])
@jwt_required()
@swag_from({
    "tags": ["Hand Raise"],
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
                    "request_id": {"type": "integer", "example": 1}
                },
                "required": ["request_id"]
            }
        }
    ],
    "responses": {
        "200": {"description": "Hand granted successfully"},
        "400": {"description": "Invalid request"},
        "403": {"description": "Only the professor can grant the hand"},
        "404": {"description": "Session or request not found"}
    }
})
def grant_hand(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != current_user["id"]:
        return jsonify({"message": "Only the professor can grant the hand"}), 403
    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session is not active"}), 400

    data = request.get_json()
    if "request_id" not in data:
        return jsonify({"message": "Request ID is required"}), 400

    hand_request = HandRequest.query.filter_by(id=data["request_id"], session_id=session_id).first_or_404()

    if hand_request.status != HandStatus.PENDING:
        return jsonify({"message": "Request is not pending"}), 400

    current_granted = HandRequest.query.filter_by(session_id=session_id, status=HandStatus.GRANTED).first()
    if current_granted:
        current_granted.status = HandStatus.REVOKED
        db.session.commit()

    hand_request.status = HandStatus.GRANTED
    hand_request.granted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Hand granted successfully"}), 200

@hand_raise_bp.route("/<int:session_id>/hand-revoke", methods=["PUT"])
@jwt_required()
@swag_from({
    "tags": ["Hand Raise"],
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
                    "request_id": {"type": "integer", "example": 1}
                },
                "required": ["request_id"]
            }
        }
    ],
    "responses": {
        "200": {"description": "Hand revoked successfully"},
        "400": {"description": "Invalid request"},
        "403": {"description": "Only the professor can revoke the hand"},
        "404": {"description": "Session or request not found"}
    }
})
def revoke_hand(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != current_user["id"]:
        return jsonify({"message": "Only the professor can revoke the hand"}), 403
    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session is not active"}), 400

    data = request.get_json()
    if "request_id" not in data:
        return jsonify({"message": "Request ID is required"}), 400

    hand_request = HandRequest.query.filter_by(id=data["request_id"], session_id=session_id).first_or_404()

    if hand_request.status != HandStatus.GRANTED:
        return jsonify({"message": "Request is not currently granted"}), 400

    hand_request.status = HandStatus.REVOKED
    db.session.commit()

    return jsonify({"message": "Hand revoked successfully"}), 200