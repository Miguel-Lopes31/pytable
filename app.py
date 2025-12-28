from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, GameSession, QuestionLog
from sqlalchemy import func, desc
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-this-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pytable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Authentication Decorator
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('menu'))
    return redirect(url_for('login'))

@app.before_request
def check_ban_status():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.banned_until and user.banned_until > datetime.utcnow():
            session.clear()
            return render_template('auth.html', error=f"Sua conta está banida até {user.banned_until.strftime('%d/%m/%Y %H:%M')}", mode='login')

# Auth Decorators
def admin_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return redirect(url_for('menu')) # Or 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('menu'))
        else:
            return render_template('auth.html', error="Invalid credentials", mode='login')
    
    return render_template('auth.html', mode='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            return render_template('auth.html', error="Username already exists", mode='register')
        
        new_user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        return redirect(url_for('menu'))
        
    return render_template('auth.html', mode='register')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# App Routes
@app.route('/menu')
@login_required
def menu():
    return render_template('menu.html', username=session['username'])

@app.route('/game')
@login_required
def game():
    # Helper to get info from query params, e.g. ?tables=2,3 or ?tables=all
    tables = request.args.get('tables', '1')
    return render_template('game.html', tables=tables)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['username'])

@app.route('/ranking')
@login_required
def ranking():
    # Helper to check if current user is admin for button visibility? No, template handles it.
    
    # Simple ranking: Total correct answers
    leaders = db.session.query(
        User, 
        func.sum(GameSession.score).label('total_score')
    ).join(GameSession).group_by(User.id).order_by(desc('total_score')).limit(20).all()
    
    return render_template('ranking.html', leaders=leaders)

# Admin Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.all()
    return render_template('admin/users.html', users=users, username=session['username'])

@app.route('/admin/user/<int:user_id>/ban', methods=['POST'])
@admin_required
def admin_ban_user(user_id):
    hours = request.form.get('hours', type=int)
    user = User.query.get_or_404(user_id)
    if hours:
        user.banned_until = datetime.utcnow() + timedelta(hours=hours)
    else:
        user.banned_until = None # Unban
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/edit', methods=['POST'])
@admin_required
def admin_edit_user(user_id):
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.get_or_404(user_id)
    
    if username:
        user.username = username
    if password:
        user.password_hash = generate_password_hash(password)
        
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/score', methods=['POST'])
@admin_required
def admin_manage_score(user_id):
    # This is tricky because score is aggregated from sessions. 
    # We will create a manual adjustment session.
    points = request.form.get('points', type=int)
    action = request.form.get('action') # 'add' or 'remove'
    
    if action == 'remove':
        points = -points
        
    # Create a "System Adjustment" session
    adj_session = GameSession(
        user_id=user_id,
        tables_practiced="Admin Adjustment",
        score=points,
        total_questions=0 # Doesn't affect accuracy if we only sum correct
    )
    db.session.add(adj_session)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# API Routes
@app.route('/api/submit_game', methods=['POST'])
@login_required
def submit_game():
    data = request.json
    user_id = session['user_id']
    
    new_session = GameSession(
        user_id=user_id,
        tables_practiced=data.get('tables'),
        score=data.get('score'),
        total_questions=data.get('total_questions')
    )
    db.session.add(new_session)
    db.session.flush() # Get ID
    
    # Save details
    for q in data.get('details', []):
        log = QuestionLog(
            session_id=new_session.id,
            number_base=q['base'],
            number_mult=q['mult'],
            is_correct=q['correct']
        )
        db.session.add(log)
    
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/stats')
@login_required
def get_stats():
    user_id = session['user_id']
    
    # Aggregate stats per number (1-10)
    # We want: { "1": { correct: 10, total: 12 }, "2": ... }
    
    results = db.session.query(
        QuestionLog.number_base,
        func.sum(QuestionLog.is_correct).label('correct'),
        func.count(QuestionLog.id).label('total')
    ).join(GameSession).filter(GameSession.user_id == user_id).group_by(QuestionLog.number_base).all()
    
    stats = {}
    for r in results:
        # SQLite returns sum as int or None, ensure defined
        c = int(r.correct) if r.correct else 0
        stats[r.number_base] = {
            'correct': c,
            'total': r.total,
            'rate': round((c / r.total) * 100, 1) if r.total > 0 else 0
        }
        
    return jsonify(stats)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
