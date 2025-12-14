from __init__ import db
from model.user import User

# --- EXISTING CHARACTER MODEL ---
class CandylandCharacter(db.Model):
    __tablename__ = 'candyland_character'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    character_type = db.Column(db.String(50), nullable=True)
    character_name = db.Column(db.String(100), nullable=True)

    def __init__(self, user_id, character_type, character_name):
        self.user_id = user_id
        self.character_type = character_type
        self.character_name = character_name

    def to_dict(self):
        return {
            "character_type": self.character_type,
            "character_name": self.character_name
        }

# --- EXISTING SCORE MODEL ---
class CandylandScore(db.Model):
    __tablename__ = 'candyland_scores'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score_type = db.Column(db.String(50), nullable=False)
    score_value = db.Column(db.Integer, nullable=False)

# --- NEW: BADGE DEFINITION ---
class CandylandBadge(db.Model):
    __tablename__ = 'candyland_badges'
    
    id = db.Column(db.Integer, primary_key=True)
    badge_name = db.Column(db.String(100), unique=True, nullable=False)
    badge_icon = db.Column(db.String(10), nullable=False) # Stores emoji like 🏆
    
    def __init__(self, badge_name, badge_icon):
        self.badge_name = badge_name
        self.badge_icon = badge_icon

# --- NEW: USER <-> BADGE RELATIONSHIP (Many-to-Many) ---
# This matches your teacher's "UserSections" pattern
class CandylandUserBadge(db.Model):
    __tablename__ = 'candyland_user_badges'
    
    # Composite Primary Key ensures a user cannot have duplicate of same badge
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('candyland_badges.id'), primary_key=True)

    # Relationships to access data easily
    user = db.relationship("User", backref=db.backref("my_badges", cascade="all, delete-orphan"))
    badge = db.relationship("CandylandBadge", backref=db.backref("owners", cascade="all, delete-orphan"))

    def __init__(self, user_id, badge_id):
        self.user_id = user_id
        self.badge_id = badge_id

def initCandyland():
    db.create_all()