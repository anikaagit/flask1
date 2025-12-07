from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from __init__ import db
from model.user import User
from model.candyland import CandylandCharacter
from model.candyland import CandylandScore

candyland_api = Blueprint('candyland_api', __name__, url_prefix='/api/candyland')

# --- SIGNUP ---
# Note: The professor likely has a user creation system. 
# If you MUST use your own json signup, use this:
@candyland_api.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    #email = data.get('email')
    password = data.get('password')

    # Check against the Professor's User Model
    # Note: Check model/user.py to see if the column is 'username' or '_uid'
    if User.query.filter_by(_uid=username).first(): 
        return jsonify({"error": "Username taken"}), 400

    # Create User using Professor's existing logic if possible, 
    # otherwise manual creation (adapt fields to match his User model):
    # This assumes his User model has these fields. You might need to adjust.
    new_user = User(name=username, uid=username, password=password) 
    
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created"}), 201

# --- LOGIN ---
@candyland_api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Check against Professor's User Model
    user = User.query.filter_by(_uid=username).first()

    # Use the verify/check password method from his model or standard check
    if user and user.is_password(password): 
        login_user(user)
        
        # Fetch Character Data
        char_data = CandylandCharacter.query.filter_by(user_id=user.id).first()
        
        response = {
            "message": "Login successful", 
            "username": user.uid,
            "character_type": None,
            "character_name": None
        }
        
        if char_data:
            response['character_type'] = char_data.character_type
            response['character_name'] = char_data.character_name

        return jsonify(response), 200
    
    return jsonify({"error": "Invalid creds"}), 401

# --- SAVE CHARACTER ---
@candyland_api.route('/save_character', methods=['POST'])
@login_required 
def save_character():
    data = request.get_json()
    
    # Check if character data exists for this user
    char_entry = CandylandCharacter.query.filter_by(user_id=current_user.id).first()
    
    if char_entry:
        char_entry.character_type = data.get('character_type')
        char_entry.character_name = data.get('character_name')
    else:
        new_entry = CandylandCharacter(
            user_id=current_user.id,
            character_type=data.get('character_type'),
            character_name=data.get('character_name')
        )
        db.session.add(new_entry)
    
    db.session.commit()
    return jsonify({"message": "Character saved!"}), 200

# --- SAVE SCORE ---
@candyland_api.route('/save_score', methods=['POST'])
@login_required 
def save_score():
    data = request.get_json()
    
    score_type = data.get('score_type')
    score_value = data.get('score_value')
    
    # Validation: Ensure we actually got the data we need
    if not score_type or score_value is None:
        return jsonify({"error": "Missing score_type or score_value"}), 400

    # Check if a score for THIS specific game type exists for this user
    score_entry = CandylandScore.query.filter_by(
        user_id=current_user.id, 
        score_type=score_type
    ).first()
    
    if score_entry:
        # OPTION A: Always overwrite with the new score (most recent)
        score_entry.score_value = score_value
        
        # OPTION B: Only overwrite if the new score is higher (high score system)
        # if score_value > score_entry.score_value:
        #     score_entry.score_value = score_value
            
    else:
        new_entry = CandylandScore(
            user_id=current_user.id,
            score_type=score_type,
            score_value=score_value
        )
        db.session.add(new_entry)
    
    db.session.commit()
    return jsonify({"message": f"{score_type} score saved successfully!"}), 200

# --- GET SCORES ---
@candyland_api.route('/get_scores', methods=['GET'])
@login_required 
def get_scores():
    # Fetch all scores for the current user
    user_scores = CandylandScore.query.filter_by(user_id=current_user.id).all()
    
    # Convert the database objects to a JSON-friendly list
    score_list = []
    for entry in user_scores:
        score_list.append({
            "score_type": entry.score_type,
            "score_value": entry.score_value
        })
    
    return jsonify(score_list), 200

# --- LOGOUT ---
@candyland_api.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200