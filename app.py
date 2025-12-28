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

@app.context_processor
def inject_user():
    is_admin = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            is_admin = user.is_admin
            # Also refresh session is_admin just in case
            session['is_admin'] = is_admin
    return dict(current_user_is_admin=is_admin)

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
            session['is_admin'] = user.is_admin
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

# Helper for Level System
def get_level_data(total_score):
    if not total_score:
        total_score = 0
        
    level = total_score // 10
    if level > 1000:
        level = 1000
        
    title = "Iniciante"
    badge = ""
    
    if level >= 1000:
        title = "Gênio Indomável"
        badge = "🧞‍♂️"
    elif level >= 900:
        title = "Turing"
        badge = "💻"
    elif level >= 800:
        title = "Nash"
        badge = "🌐"
    elif level >= 700:
        title = "Mr Robot"
        badge = "🤖"
    elif level >= 600:
        title = "Sábio"
        badge = "🔮"
    elif level >= 500:
        title = "Doutor"
        badge = "🎓"
    elif level >= 400:
        title = "Mestre"
        badge = "🧠"
    elif level >= 300:
        title = "Professor"
        badge = "👨‍🏫"
    elif level >= 200:
        title = "Calculista"
        badge = "🧮"
    elif level >= 100:
        title = "Aprendiz"
        badge = "👶"
        
    return {
        'level': level,
        'title': title,
        'badge': badge,
        'next_level_score': (level + 1) * 10
    }

# App Routes
@app.route('/menu')
@login_required
def menu():
    user = User.query.get(session['user_id'])
    
    # Calculate Level
    total_score = db.session.query(func.sum(GameSession.score)).filter_by(user_id=user.id).scalar() or 0
    level_data = get_level_data(total_score)
    
    return render_template('menu.html', username=user.username, user=user, level_data=level_data)

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
    leaders_query = db.session.query(
        User, 
        func.sum(GameSession.score).label('total_score')
    ).join(GameSession).group_by(User.id).order_by(desc('total_score')).limit(20).all()
    
    # Enrich with level data
    leaders = []
    for user, score in leaders_query:
        lvl = get_level_data(score)
        leaders.append({
            'username': user.username,
            'is_admin': user.is_admin,
            'zombie_badge': user.zombie_badge,
            'total_score': score,
            'level': lvl['level'],
            'title': lvl['title'],
            'badge': lvl['badge']
        })
    
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
    is_admin = request.form.get('is_admin') == 'on'
    zombie_badge = request.form.get('zombie_badge') == 'on'
    
    user = User.query.get_or_404(user_id)
    
    if username:
        user.username = username
    if password:
        user.password_hash = generate_password_hash(password)
    
    user.is_admin = is_admin
    user.zombie_badge = zombie_badge
        
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/score', methods=['POST'])
@admin_required
def admin_manage_score(user_id):
    # This is tricky because score is aggregated from sessions. 
    # We will create a manual adjustment session.
    points = request.form.get('points', type=int)
    action = request.form.get('action') # 'add' or 'remove'
    
    if action == 'clear':
        # Calculate current total to negate it
        current_total = db.session.query(func.sum(GameSession.score)).filter_by(user_id=user_id).scalar() or 0
        points = -current_total
        desc = "Admin Clear"
    elif action == 'remove':
        points = -points
        desc = "Admin Adjustment"
    else:
        desc = "Admin Adjustment"
        
    # Create a "System Adjustment" session
    adj_session = GameSession(
        user_id=user_id,
        tables_practiced=desc,
        score=points,
        total_questions=0 # Doesn't affect accuracy if we only sum correct
    )
    db.session.add(adj_session)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself to avoid issues
    if user.id == session.get('user_id'):
        return redirect(url_for('admin_dashboard')) # Or show error
        
    # Cascading delete
    # 1. Get sessions
    sessions = GameSession.query.filter_by(user_id=user.id).all()
    session_ids = [s.id for s in sessions]
    
    # 2. Delete logs for these sessions
    if session_ids:
        QuestionLog.query.filter(QuestionLog.session_id.in_(session_ids)).delete(synchronize_session=False)
        
    # 3. Delete sessions
    for s in sessions:
        db.session.delete(s)
        
    # 4. Delete user
    db.session.delete(user)
    
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
    
    # Zombie Mode Logic
    mode = data.get('mode')
    if mode == 'zombie':
        # Condition: 100 correct (since we know it's 10x10) and NO errors (score == total)
        # Actually total_questions might be slightly different if they quit early, so check equality
        if data.get('score') == 100 and data.get('score') == data.get('total_questions'):
            user = User.query.get(user_id)
            user.zombie_badge = True
    
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

    return jsonify(stats)

@app.route('/api/smart_deck')
@login_required
def get_smart_deck():
    user_id = session['user_id']
    
    # Logic: Find "Active Errors".
    # An active error is a (base, mult) pair where the LATEST attempt was Incorrect.
    # If the latest attempt was Correct, it's considered "resolved" for now and removed from priority.
    
    # 1. Subquery to find the latest QuestionLog ID for each (base, mult) pair for this user
    latest_attempts_subquery = db.session.query(
        QuestionLog.number_base,
        QuestionLog.number_mult,
        func.max(QuestionLog.id).label('max_id')
    ).join(GameSession).filter(
        GameSession.user_id == user_id
    ).group_by(QuestionLog.number_base, QuestionLog.number_mult).subquery()
    
    # 2. Query the actual logs that match these max_ids AND are incorrect
    active_errors = db.session.query(QuestionLog).join(
        latest_attempts_subquery, 
        QuestionLog.id == latest_attempts_subquery.c.max_id
    ).filter(
        QuestionLog.is_correct == False
    ).all()
    
    deck_data = []
    
    # Add active errors to deck
    mistakes_list = [{'base': m.number_base, 'mult': m.number_mult, 'is_mistake': True} for m in active_errors]
    
    # If user has many errors, prioritize? For now take all (or limit if deck too big)
    # Let's shuffle the mistakes so they aren't always in same order if there are many
    import random
    random.shuffle(mistakes_list)
    
    for m in mistakes_list:
        deck_data.append(m)
        if len(deck_data) >= 20: # Cap mistakes at 20 per session to avoid fatigue? Or show all?
            break
            
    # 3. Fallback: If deck is empty (User is perfect!) or small, fill with Hard Questions
    # This ensures the mode is always playable.
    hard_questions = [
        (6,7), (6,8), (6,9), (7,6), (7,7), (7,8), (7,9), 
        (8,6), (8,7), (8,8), (8,9), (9,6), (9,7), (9,8), (9,9)
    ]
    
    while len(deck_data) < 10: # Ensure at least 10 cards
        base, mult = random.choice(hard_questions)
        # Avoid duplicates if possible?
        # Simple check
        if not any(d['base'] == base and d['mult'] == mult for d in deck_data):
             deck_data.append({'base': base, 'mult': mult, 'is_mistake': False})
        else:
             # Just add it anyway, repetition is good practice
             deck_data.append({'base': base, 'mult': mult, 'is_mistake': False})

    # Calculate answer for convenience
    for card in deck_data:
        card['answer'] = card['base'] * card['mult']
        
    return jsonify(deck_data)
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
