from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_teacher = db.Column(db.Boolean, default=False)
    banned_until = db.Column(db.DateTime, nullable=True)
    zombie_badge = db.Column(db.Boolean, default=False)
    
    # Relationships
    sessions = db.relationship('GameSession', backref='user', lazy=True)
    classrooms_created = db.relationship('Classroom', backref='teacher', lazy=True)
    classrooms_joined = db.relationship('StudentClassroom', backref='student', lazy=True)

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    students = db.relationship('StudentClassroom', backref='classroom', lazy=True)
    homeworks = db.relationship('Homework', backref='classroom', lazy=True)

class Homework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    tables_config = db.Column(db.String(50), nullable=False) # e.g. "2,3"
    deadline = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    submissions = db.relationship('HomeworkSubmission', backref='homework', lazy=True)

class HomeworkSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    homework_id = db.Column(db.Integer, db.ForeignKey('homework.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_late = db.Column(db.Boolean, default=False)

class StudentClassroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    
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
    operation_type = db.Column(db.String(20), default='multiply') # 'multiply' or 'divide'
