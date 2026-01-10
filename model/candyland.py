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

# Update this function in candyland.py
def calculate_badge_rarity(badge_id):
    """
    Refined Business Logic: Calculates rarity based on 
    Attempts (JinjaAdmin) vs Earned (UserBadge).
    """
    badge = CandylandBadge.query.get(badge_id)
    if not badge:
        return 0

    # 1. Get total attempts from the "Administration Table" (JinjaAdmin)
    stats = CandylandJinjaAdmin.query.filter_by(game_id=badge.badge_name).first()
    total_attempts = stats.total_global_attempts if stats else 0
    
    # 2. Get total people who actually won it (Many-to-Many table)
    total_earned = db.session.query(func.count(CandylandUserBadge.user_id)).filter_by(badge_id=badge_id).scalar()

    if total_attempts == 0:
        # Fallback: if no Jinja stats exist yet, use total users so we don't divide by zero
        total_users = db.session.query(func.count(User.id)).scalar()
        if total_users == 0: return 0
        return round((total_earned / total_users) * 100, 1)
    
    rarity_percentage = (total_earned / total_attempts) * 100
    return round(rarity_percentage, 1)

def inject_mock_data(count=50):
    """
    FIXED: Now increments JinjaAdmin attempts along with assigning badges
    to ensure rarity math stays below 100%.
    """
    badge_data = [
        ('Path Finder', '📍'), ('Speed Runner', '⚡'), ('Perfect Navigator', '🧭'),
        ('Bug Master', '🐛'), ('Quick Reflexes', '🤺'), ('Good Shot', '🎯'),
        ('Slow and Steady', '🐢'), ('Eagle Eye', '👁️'), ('Perfect Scholar', '🎓'),
        ('Social Butterfly', '🦋'), ('Perfect Conversationalist', '💬'),
        ('Friend Magnet', '🧲'), ('Awkward Moments', '😅'), ('Learning to Socialize', '🌱'),
        ('Perfect Morning', '🌅'), ('Sharp Memory', '🧠'), ('Morning Star', '⭐'),
        ('Still Sleepy', '😴'), ('Careful Observer', '🧐')
    ]

    # Ensure badges and Admin records exist
    badge_objs = []
    for name, icon in badge_data:
        b = CandylandBadge.query.filter_by(badge_name=name).first()
        if not b:
            b = CandylandBadge(badge_name=name, badge_icon=icon)
            db.session.add(b)
        badge_objs.append(b)
        
        # Ensure there is a record in JinjaAdmin for this badge
        admin_rec = CandylandJinjaAdmin.query.filter_by(game_id=name).first()
        if not admin_rec:
            admin_rec = CandylandJinjaAdmin(game_id=name, total_global_attempts=0)
            db.session.add(admin_rec)
    db.session.commit()

    for i in range(count):
        fake_uid = f"mock_user_{random.randint(1000, 9999)}_{i}"
        if not User.query.filter_by(_uid=fake_uid).first():
            user = User(name=fake_uid, uid=fake_uid, password="password123")
            db.session.add(user)
            db.session.flush() 

            for b in badge_objs:
                # IMPORTANT: Every mock user represents an "Attempt" 
                admin_rec = CandylandJinjaAdmin.query.filter_by(game_id=b.badge_name).first()
                admin_rec.total_global_attempts += 1

                # Probabilities for "Earned"
                if b.badge_name in ['Bug Master', 'Perfect Scholar', 'Perfect Morning']:
                    prob = 0.03 # 3% Rare
                elif b.badge_name in ['Path Finder', 'Still Sleepy']:
                    prob = 0.70 # 70% Common
                else:
                    prob = 0.15 # 15% Uncommon
                
                if random.random() < prob:
                    rel = CandylandUserBadge(user_id=user.id, badge_id=b.id)
                    db.session.add(rel)
    
    db.session.commit()
    print(f"Injected {count} users. Denominators (JinjaAdmin) and Numerators (UserBadge) are synced.")

def clear_candyland_data():
    """
    Cleans up mock users and resets admin stats so you can fix the 1400% error.
    """
    # Delete mock users (names starting with mock_user_)
    mock_users = User.query.filter(User._uid.like('mock_user_%')).all()
    for u in mock_users:
        # Relationships (badges/scores) will cascade delete if your model is set up correctly
        db.session.delete(u)
    
    # Reset JinjaAdmin attempts to 0
    db.session.query(CandylandJinjaAdmin).update({CandylandJinjaAdmin.total_global_attempts: 0})
    
    db.session.commit()
    print("Mock data cleared and JinjaAdmin reset.")
    
def setup_candyland_with_data():
    """
    Replacement for initCandyland to ensure tables are created 
    AND mock data is injected.
    """
    db.create_all()
    # Only inject if we don't have enough data already
    if db.session.query(func.count(User.id)).scalar() < 20:
        inject_mock_data(100)

# --- NEW: JINJA ADMINISTRATION TABLE (Phase 1) ---
class CandylandJinjaAdmin(db.Model):
    """
    This is the core Administration Table requested by the professor.
    It tracks global game analytics (Attempts) used to calculate rarity.
    """
    __tablename__ = 'candyland_jinja_admin'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(100), unique=True, nullable=False) # e.g., 'Path Finder'
    total_global_attempts = db.Column(db.Integer, default=0)

    def __init__(self, game_id, total_global_attempts=0):
        self.game_id = game_id
        self.total_global_attempts = total_global_attempts

    def to_dict(self):
        return {
            "game_id": self.game_id,
            "attempts": self.total_global_attempts
        }