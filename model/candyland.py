from __init__ import db
from model.user import User

class CandylandCharacter(db.Model):
    __tablename__ = 'candyland_character'
    
    id = db.Column(db.Integer, primary_key=True)
    # This links your game character to the main User table
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

# Function to initialize data if needed (keeps the pattern of the repo)
def initCandyland():
    db.create_all()