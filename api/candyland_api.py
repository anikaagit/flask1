from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from __init__ import db
from model.user import User
from model.candyland import CandylandCharacter, CandylandScore, CandylandBadge, CandylandUserBadge

candyland_api = Blueprint('candyland_api', __name__, url_prefix='/api/candyland')

# --- LOGIN/SIGNUP ROUTES (Keep your existing ones) ---
@candyland_api.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if User.query.filter_by(_uid=username).first(): 
        return jsonify({"error": "Username taken"}), 400
    new_user = User(name=username, uid=username, password=password) 
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created"}), 201

@candyland_api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(_uid=username).first()
    if user and user.is_password(password): 
        login_user(user)
        char_data = CandylandCharacter.query.filter_by(user_id=user.id).first()
        response = {
            "message": "Login successful", 
            "username": user.uid,
            "character_type": char_data.character_type if char_data else None,
            "character_name": char_data.character_name if char_data else None
        }
        return jsonify(response), 200
    return jsonify({"error": "Invalid creds"}), 401

@candyland_api.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200

# --- SCORE & CHARACTER ROUTES (Keep your existing ones) ---
@candyland_api.route('/save_character', methods=['POST'])
@login_required 
def save_character():
    data = request.get_json()
    char_entry = CandylandCharacter.query.filter_by(user_id=current_user.id).first()
    if char_entry:
        char_entry.character_type = data.get('character_type')
        char_entry.character_name = data.get('character_name')
    else:
        new_entry = CandylandCharacter(user_id=current_user.id, character_type=data.get('character_type'), character_name=data.get('character_name'))
        db.session.add(new_entry)
    db.session.commit()
    return jsonify({"message": "Character saved!"}), 200

@candyland_api.route('/save_score', methods=['POST'])
@login_required 
def save_score():
    data = request.get_json()
    score_type = data.get('score_type')
    score_value = data.get('score_value')
    if not score_type or score_value is None: return jsonify({"error": "Missing data"}), 400
    score_entry = CandylandScore.query.filter_by(user_id=current_user.id, score_type=score_type).first()
    if score_entry:
        score_entry.score_value = score_value
    else:
        db.session.add(CandylandScore(user_id=current_user.id, score_type=score_type, score_value=score_value))
    db.session.commit()
    return jsonify({"message": "Score saved"}), 200

@candyland_api.route('/get_scores', methods=['GET'])
@login_required 
def get_scores():
    user_scores = CandylandScore.query.filter_by(user_id=current_user.id).all()
    return jsonify([{"score_type": e.score_type, "score_value": e.score_value} for e in user_scores]), 200

# --- NEW: BADGE ROUTES ---

@candyland_api.route('/save_badge', methods=['POST'])
@login_required
def save_badge():
    data = request.get_json()
    badge_name = data.get('badge_name')
    badge_icon = data.get('badge_icon')
    
    if not badge_name:
        return jsonify({"error": "Badge name required"}), 400

    # 1. Check if the Badge Definition exists in the system (e.g. "Perfect Morning")
    # If not, we create it so other users can earn it too.
    badge_def = CandylandBadge.query.filter_by(badge_name=badge_name).first()
    if not badge_def:
        badge_def = CandylandBadge(badge_name=badge_name, badge_icon=badge_icon or "🏅")
        db.session.add(badge_def)
        db.session.commit() # Commit needed to generate badge_def.id
    
    # 2. Check if THIS User already has this badge
    user_badge = CandylandUserBadge.query.filter_by(
        user_id=current_user.id, 
        badge_id=badge_def.id
    ).first()
    
    if not user_badge:
        # Create the relationship
        new_relationship = CandylandUserBadge(user_id=current_user.id, badge_id=badge_def.id)
        db.session.add(new_relationship)
        db.session.commit()
        return jsonify({"message": f"Badge '{badge_name}' awarded!"}), 200
    
    return jsonify({"message": "User already has this badge"}), 200

@candyland_api.route('/get_badges', methods=['GET'])
@login_required
def get_badges():
    # Join logic handled by SQLAlchemy relationships
    user_badges = CandylandUserBadge.query.filter_by(user_id=current_user.id).all()
    
    results = []
    for ub in user_badges:
        results.append({
            "name": ub.badge.badge_name,
            "icon": ub.badge.badge_icon
        })
        
    return jsonify(results), 200