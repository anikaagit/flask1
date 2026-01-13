from __init__ import db
from datetime import datetime


class GameSession(db.Model):
    __tablename__ = 'game_sessions'

    session_id = db.Column(db.String(64), primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    gas_holder_npc_id = db.Column(db.Integer, db.ForeignKey('npcs.id'), nullable=False)

    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    attempts_count = db.Column(db.Integer, nullable=False, default=0)

    def __init__(
        self,
        session_id: str,
        gas_holder_npc_id: int,
        user_id: int | None = None,
        start_time: datetime | None = None,
    ):
        self.session_id = session_id
        self.gas_holder_npc_id = gas_holder_npc_id
        self.user_id = user_id
        if start_time:
            self.start_time = start_time

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_completed": self.is_completed,
            "attempts_count": self.attempts_count,
        }
