from __init__ import db
from model.user import User
import json
import os

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
class CandylandUserBadge(db.Model):
    __tablename__ = 'candyland_user_badges'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('candyland_badges.id'), primary_key=True)

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
    badge = CandylandBadge.query.get(badge_id)
    if not badge:
        return 0
    stats = CandylandJinjaAdmin.query.filter_by(game_id=badge.badge_name).first()
    total_attempts = stats.total_global_attempts if stats else 0
    total_earned = db.session.query(func.count(CandylandUserBadge.user_id)).filter_by(badge_id=badge_id).scalar()
    if total_attempts == 0:
        total_users = db.session.query(func.count(User.id)).scalar()
        if total_users == 0: return 0
        return round((total_earned / total_users) * 100, 1)
    rarity_percentage = (total_earned / total_attempts) * 100
    return round(rarity_percentage, 1)

def inject_mock_data(count=50):
    badge_data = [
        ('Path Finder', '📍'), ('Speed Runner', '⚡'), ('Perfect Navigator', '🧭'),
        ('Bug Master', '🐛'), ('Quick Reflexes', '🤺'), ('Good Shot', '🎯'),
        ('Slow and Steady', '🐢'), ('Eagle Eye', '👁️'), ('Perfect Scholar', '🎓'),
        ('Social Butterfly', '🦋'), ('Perfect Conversationalist', '💬'),
        ('Friend Magnet', '🧲'), ('Awkward Moments', '😅'), ('Learning to Socialize', '🌱'),
        ('Perfect Morning', '🌅'), ('Sharp Memory', '🧠'), ('Morning Star', '⭐'),
        ('Still Sleepy', '😴'), ('Careful Observer', '🧐')
    ]
    badge_objs = []
    for name, icon in badge_data:
        b = CandylandBadge.query.filter_by(badge_name=name).first()
        if not b:
            b = CandylandBadge(badge_name=name, badge_icon=icon)
            db.session.add(b)
        badge_objs.append(b)
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
                admin_rec = CandylandJinjaAdmin.query.filter_by(game_id=b.badge_name).first()
                admin_rec.total_global_attempts += 1
                if b.badge_name in ['Bug Master', 'Perfect Scholar', 'Perfect Morning']:
                    prob = 0.03
                elif b.badge_name in ['Path Finder', 'Still Sleepy']:
                    prob = 0.70
                else:
                    prob = 0.15
                if random.random() < prob:
                    rel = CandylandUserBadge(user_id=user.id, badge_id=b.id)
                    db.session.add(rel)
    db.session.commit()

def clear_candyland_data():
    mock_users = User.query.filter(User._uid.like('mock_user_%')).all()
    for u in mock_users:
        db.session.delete(u)
    db.session.query(CandylandJinjaAdmin).update({CandylandJinjaAdmin.total_global_attempts: 0})
    db.session.commit()
    
def setup_candyland_with_data():
    db.create_all()
    if db.session.query(func.count(User.id)).scalar() < 20:
        inject_mock_data(100)

class CandylandJinjaAdmin(db.Model):
    __tablename__ = 'candyland_jinja_admin'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(100), unique=True, nullable=False)
    total_global_attempts = db.Column(db.Integer, default=0)
    def __init__(self, game_id, total_global_attempts=0):
        self.game_id = game_id
        self.total_global_attempts = total_global_attempts
    def to_dict(self):
        return {"game_id": self.game_id, "attempts": self.total_global_attempts}

# --- PHASE 2: SERIALIZATION LOGIC (BACKUP) ---
def backup_rarity_data():
    """
    Utility function to save the JinjaAdmin and UserBadge state to JSON.
    Uses 'uid' and 'badge_name' instead of IDs so the data is portable 
    across database resets.
    """
    # 1. Capture Global Attempt Stats (JinjaAdmin)
    admin_data = []
    all_stats = CandylandJinjaAdmin.query.all()
    for s in all_stats:
        admin_data.append({
            "game_id": s.game_id,
            "total_global_attempts": s.total_global_attempts
        })

    # 2. Capture Many-to-Many Badge Assignments
    badge_assignments = []
    all_assignments = CandylandUserBadge.query.all()
    for a in all_assignments:
        badge_assignments.append({
            "uid": a.user._uid,
            "badge_name": a.badge.badge_name
        })

    # 3. Build final dictionary
    snapshot = {
        "jinja_attempts": admin_data,
        "user_badge_assignments": badge_assignments
    }

    # 4. Write to file
    file_path = os.path.join(os.getcwd(), 'rarity_snapshot.json')
    with open(file_path, 'w') as f:
        json.dump(snapshot, f, indent=4)
    
    return file_path