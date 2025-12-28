from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    banned_until = db.Column(db.DateTime, nullable=True)
    zombie_badge = db.Column(db.Boolean, default=False)
    
    # Relationships
    sessions = db.relationship('GameSession', backref='user', lazy=True)

class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tables_practiced = db.Column(db.String(100)) # e.g., "2,3,5" or "All"
    score = db.Column(db.Integer, default=0) # Total correct
    total_questions = db.Column(db.Integer, default=0)
    
    details = db.relationship('QuestionLog', backref='session', lazy=True)

class QuestionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    number_base = db.Column(db.Integer, nullable=False) # The table number (e.g., 7)
    number_mult = db.Column(db.Integer, nullable=False) # The multiplier (e.g., 8)
    is_correct = db.Column(db.Boolean, nullable=False)
