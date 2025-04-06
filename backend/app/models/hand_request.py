from app import db
from datetime import datetime
import enum

class HandStatus(enum.Enum):
    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"

class HandRequest(db.Model):
    __tablename__ = "hand_requests"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Enum(HandStatus), default=HandStatus.PENDING, nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    granted_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<HandRequest {self.user_id} - {self.status.value}>"