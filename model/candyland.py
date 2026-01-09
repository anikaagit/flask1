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

# --- APPENDED TO candyland.py ---
import random
from sqlalchemy import func

def calculate_badge_rarity(badge_id):
    """
    Business Logic: Calculates percentage of users who own a specific badge.
    """
    total_users = db.session.query(func.count(User.id)).scalar()
    if total_users == 0:
        return 0
    
    # Count how many users have this specific badge_id in the M2M table
    users_with_badge = db.session.query(func.count(CandylandUserBadge.user_id)).filter_by(badge_id=badge_id).scalar()
    
    rarity_percentage = (users_with_badge / total_users) * 100
    return round(rarity_percentage, 1)

def inject_mock_data(count=50):
    """
    Generates mock users and assigns badges with varying probabilities 
    to simulate different rarity levels.
    """
    # 1. Define the Master Badge List and Icons
    badge_data = [
        ('Path Finder', '📍'), ('Speed Runner', '⚡'), ('Perfect Navigator', '🧭'),
        ('Bug Master', '🐛'), ('Quick Reflexes', '🤺'), ('Good Shot', '🎯'),
        ('Slow and Steady', '🐢'), ('Eagle Eye', '👁️'), ('Perfect Scholar', '🎓'),
        ('Social Butterfly', '🦋'), ('Perfect Conversationalist', '💬'),
        ('Friend Magnet', '🧲'), ('Awkward Moments', '😅'), ('Learning to Socialize', '🌱'),
        ('Perfect Morning', '🌅'), ('Sharp Memory', '🧠'), ('Morning Star', '⭐'),
        ('Still Sleepy', '😴'), ('Careful Observer', '🧐')
    ]

    # 2. Ensure all badges exist in the DB
    badge_objs = []
    for name, icon in badge_data:
        b = CandylandBadge.query.filter_by(badge_name=name).first()
        if not b:
            b = CandylandBadge(badge_name=name, badge_icon=icon)
            db.session.add(b)
        badge_objs.append(b)
    db.session.commit()

    # 3. Create Mock Users and assign badges
    # We use a loop to create "A lot of test data" as requested
    for i in range(count):
        fake_uid = f"mock_user_{random.randint(1000, 9999)}_{i}"
        if not User.query.filter_by(_uid=fake_uid).first():
            user = User(name=fake_uid, uid=fake_uid, password="password123")
            db.session.add(user)
            db.session.flush() # Gets the ID without committing yet

            # Assign badges based on different probabilities to create 'Rarity'
            for b in badge_objs:
                # Some badges are very rare (3%), some are common (70%)
                if b.badge_name in ['Bug Master', 'Perfect Scholar']:
                    prob = 0.03 # 3% Rarity
                elif b.badge_name in ['Path Finder', 'Still Sleepy']:
                    prob = 0.70 # 70% Rarity
                else:
                    prob = 0.15 # 15% Rarity
                
                if random.random() < prob:
                    # Assign badge to user
                    rel = CandylandUserBadge(user_id=user.id, badge_id=b.id)
                    db.session.add(rel)
    
    db.session.commit()
    print(f"Successfully injected {count} mock users and distributed badges.")

def setup_candyland_with_data():
    """
    Replacement for initCandyland to ensure tables are created 
    AND mock data is injected.
    """
    db.create_all()
    # Only inject if we don't have enough data already
    if db.session.query(func.count(User.id)).scalar() < 20:
        inject_mock_data(100)