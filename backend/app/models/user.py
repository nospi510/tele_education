from app import db
from datetime import datetime
import enum

class UserRole(enum.Enum):
    PROFESSOR = "professor"
    VIEWER = "viewer"

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    sessions = db.relationship("Session", backref="professor", lazy=True)
    hand_requests = db.relationship("HandRequest", backref="user", lazy=True)
    comments = db.relationship("Comment", backref="user", lazy=True)
    quiz_responses = db.relationship("QuizResponse", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.email} - {self.role.value}>"