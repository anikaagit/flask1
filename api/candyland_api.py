from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from __init__ import db
from model.user import User
from model.candyland import CandylandCharacter

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

# --- LOGOUT ---
@candyland_api.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200