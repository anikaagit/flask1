from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from __init__ import db
from model.user import User
from model.candyland import CandylandCharacter, CandylandScore, CandylandBadge, CandylandUserBadge

candyland_api = Blueprint('candyland_api', __name__, url_prefix='/api/candyland')

# ... [KEEP ALL EXISTING LOGIN/SIGNUP/SCORE/BADGE ROUTES UNCHANGED] ...

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

@candyland_api.route('/save_badge', methods=['POST'])
@login_required
def save_badge():
    data = request.get_json()
    badge_name = data.get('badge_name')
    badge_icon = data.get('badge_icon')
    if not badge_name: return jsonify({"error": "Badge name required"}), 400
    badge_def = CandylandBadge.query.filter_by(badge_name=badge_name).first()
    if not badge_def:
        badge_def = CandylandBadge(badge_name=badge_name, badge_icon=badge_icon or "🏅")
        db.session.add(badge_def)
        db.session.commit()
    user_badge = CandylandUserBadge.query.filter_by(user_id=current_user.id, badge_id=badge_def.id).first()
    if not user_badge:
        new_relationship = CandylandUserBadge(user_id=current_user.id, badge_id=badge_def.id)
        db.session.add(new_relationship)
        db.session.commit()
        return jsonify({"message": f"Badge '{badge_name}' awarded!"}), 200
    return jsonify({"message": "User already has this badge"}), 200

@candyland_api.route('/get_badges', methods=['GET'])
@login_required
def get_badges():
    user_badges = CandylandUserBadge.query.filter_by(user_id=current_user.id).all()
    results = [{"id": ub.badge.id, "name": ub.badge.badge_name, "icon": ub.badge.badge_icon} for ub in user_badges]
    return jsonify(results), 200

@candyland_api.route('/badge_owners', methods=['GET'])
def get_badge_owners():
    badge_id = request.args.get('badge_id')
    if not badge_id: return jsonify([]), 400
    try:
        results = db.session.query(User._uid).join(CandylandUserBadge, CandylandUserBadge.user_id == User.id).filter(CandylandUserBadge.badge_id == badge_id).all()
        usernames = [r[0] for r in results]
        return jsonify(usernames), 200
    except Exception as e:
        return jsonify([]), 500

from model.candyland import calculate_badge_rarity

@candyland_api.route('/get_badges_with_rarity', methods=['GET'])
@login_required
def get_badges_with_rarity():
    user_badges = CandylandUserBadge.query.filter_by(user_id=current_user.id).all()
    results = []
    for ub in user_badges:
        rarity_val = calculate_badge_rarity(ub.badge_id)
        results.append({
            "id": ub.badge.id,          
            "name": ub.badge.badge_name,
            "icon": ub.badge.badge_icon,
            "rarity": rarity_val,
            "rarity_text": f"Only {rarity_val}% have earned this"
        })
    return jsonify(results), 200

@candyland_api.route('/admin/inject_data', methods=['POST'])
def admin_inject():
    from model.candyland import inject_mock_data
    inject_mock_data(50)
    return jsonify({"message": "Injected 50 mock users"}), 200

from model.candyland import CandylandJinjaAdmin

@candyland_api.route('/increment_attempts', methods=['POST'])
def increment_attempts():
    data = request.get_json()
    game_id = data.get('game_id')
    if not game_id: return jsonify({"error": "game_id required"}), 400
    stats = CandylandJinjaAdmin.query.filter_by(game_id=game_id).first()
    if stats: stats.total_global_attempts += 1
    else:
        stats = CandylandJinjaAdmin(game_id=game_id, total_global_attempts=1)
        db.session.add(stats)
    db.session.commit()
    return jsonify({"message": f"Attempt logged for {game_id}", "total": stats.total_global_attempts}), 200

@candyland_api.route('/admin/clear_data', methods=['POST'])
def admin_clear():
    from model.candyland import clear_candyland_data
    clear_candyland_data()
    return jsonify({"message": "Database cleaned. Rarity reset to 0."}), 200

# --- PHASE 2: BACKUP TRIGGER ROUTE ---
@candyland_api.route('/admin/backup', methods=['POST'])
def admin_backup():
    """
    Endpoint to manually trigger a backup of the JinjaAdmin and M2M tables.
    """
    from model.candyland import backup_rarity_data
    try:
        path = backup_rarity_data()
        return jsonify({
            "message": "Rarity snapshot created successfully!",
            "location": path
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500