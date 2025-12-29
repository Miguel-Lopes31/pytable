from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, GameSession, QuestionLog, Classroom, StudentClassroom, Homework, HomeworkSubmission
from sqlalchemy import func, desc, or_, and_
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this-in-prod')

# Database Configuration: Use DATABASE_URL env var for production (Supabase/Render)
# Falls back to SQLite for local development
database_url = os.environ.get('DATABASE_URL', 'sqlite:///pytable.db')

# Supabase/Heroku uses 'postgres://' but SQLAlchemy requires 'postgresql://'
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
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
    is_teacher = False
    is_in_classroom = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            is_admin = user.is_admin
            is_teacher = user.is_teacher
            # Check if student is in any classroom (approved)
            if not is_teacher:
                is_in_classroom = StudentClassroom.query.filter_by(student_id=user.id, approved=True).first() is not None
            # Also refresh session is_admin just in case
            session['is_admin'] = is_admin
    return dict(current_user_is_admin=is_admin, current_user_is_teacher=is_teacher, current_user_in_classroom=is_in_classroom)

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
            return redirect(url_for('mode_select'))
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
        
        try:
            new_user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            return redirect(url_for('menu'))
        except Exception as e:
            db.session.rollback()
            print(f"ERROR creating user: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('auth.html', error=f"Erro ao criar usuário: {str(e)}", mode='register')
        
    return render_template('auth.html', mode='register')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/select')
@login_required
def mode_select():
    return render_template('mode_select.html', username=session.get('username'))

@app.route('/set_mode/<mode>')
@login_required
def set_mode(mode):
    if mode in ['multiply', 'divide']:
        session['operation_mode'] = mode
    return redirect(url_for('menu'))

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
    
    # Safety check: if user doesn't exist in DB (e.g., old session), clear and redirect
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Calculate Level
    total_score = db.session.query(func.sum(GameSession.score)).filter_by(user_id=user.id).scalar() or 0
    level_data = get_level_data(total_score)
    
    # Get current operation mode (default to multiply if not set)
    operation_mode = session.get('operation_mode', 'multiply')
    
    return render_template('menu.html', username=user.username, user=user, level_data=level_data, operation_mode=operation_mode)

@app.route('/game')
@login_required
def game():
    # Helper to get info from query params, e.g. ?tables=2,3 or ?tables=all
    tables = request.args.get('tables', '1')
    operation_mode = session.get('operation_mode', 'multiply')
    return render_template('game.html', tables=tables, operation_mode=operation_mode)

@app.route('/dashboard')
@login_required
def dashboard():
    operation_mode = session.get('operation_mode', 'multiply')
    return render_template('dashboard.html', username=session['username'], operation_mode=operation_mode)

@app.route('/ranking')
@login_required
def ranking():
    # Helper to check if current user is admin for button visibility? No, template handles it.
    
    # Simple ranking: Total correct answers (exclude admins)
    leaders_query = db.session.query(
        User, 
        func.sum(GameSession.score).label('total_score')
    ).join(GameSession).filter(User.is_admin == False).group_by(User.id).order_by(desc('total_score')).limit(20).all()
    
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
    is_teacher = request.form.get('is_teacher') == 'on'
    zombie_badge = request.form.get('zombie_badge') == 'on'
    
    user = User.query.get_or_404(user_id)
    
    if username:
        user.username = username
    if password:
        user.password_hash = generate_password_hash(password)
    
    user.is_admin = is_admin
    user.is_teacher = is_teacher
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
    
    # If user is a teacher, delete their classrooms and related data
    if user.is_teacher:
        classrooms = Classroom.query.filter_by(teacher_id=user.id).all()
        for classroom in classrooms:
            # Delete homework submissions for this classroom's homeworks
            for homework in classroom.homeworks:
                HomeworkSubmission.query.filter_by(homework_id=homework.id).delete()
                db.session.delete(homework)
            
            # Delete student enrollments
            StudentClassroom.query.filter_by(classroom_id=classroom.id).delete()
            
            # Delete the classroom
            db.session.delete(classroom)
        
    # Cascading delete for game sessions
    # 1. Get sessions
    sessions = GameSession.query.filter_by(user_id=user.id).all()
    session_ids = [s.id for s in sessions]
    
    # 2. Delete logs for these sessions
    if session_ids:
        QuestionLog.query.filter(QuestionLog.session_id.in_(session_ids)).delete(synchronize_session=False)
        
    # 3. Delete sessions
    for s in sessions:
        db.session.delete(s)
    
    # 4. Delete student enrollments (if student)
    StudentClassroom.query.filter_by(student_id=user.id).delete()
    
    # 5. Delete homework submissions (if student)
    HomeworkSubmission.query.filter_by(student_id=user.id).delete()
        
    # 6. Delete user
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
        if data.get('score')  == 100 and data.get('score') == data.get('total_questions'):
            user = User.query.get(user_id)
            user.zombie_badge = True
            
    # Homework Logic
    homework_id = data.get('homework_id')
    if homework_id:
        # Record submission
        # Check if exists first? Or allow retry? Let's allow retry, update best score? 
        # Requirement says "done or not", let's just save.
        # But wait, we want to know if they did it.
        # Let's save a new submission or update.
        # Warning: If they play multiple times, we might want to keep the best one or just the latest.
        # Let's simple: Create new if not exists, update if exists and better score?
        # User requirement: "shows errors and corrects". "Professor sees if done, score".
        
        # Check deadline
        hw = Homework.query.get(homework_id)
        if hw:
            is_late = datetime.utcnow() > hw.deadline
            
            sub = HomeworkSubmission.query.filter_by(homework_id=homework_id, student_id=user_id).first()
            if not sub:
                sub = HomeworkSubmission(
                    homework_id=homework_id,
                    student_id=user_id,
                    score=data.get('score'),
                    total_questions=data.get('total_questions'),
                    is_late=is_late
                )
                db.session.add(sub)
            else:
                # Update only if better score?
                if data.get('score') > sub.score:
                    sub.score = data.get('score')
                    sub.total_questions = data.get('total_questions')
                    sub.submitted_at = datetime.utcnow()
    
    db.session.flush() # Get ID
    
    # Save details
    operation = data.get('operation', 'multiply') # Get operation from payload
    
    for q in data.get('details', []):
        log = QuestionLog(
            session_id=new_session.id,
            number_base=q['base'],
            number_mult=q['mult'],
            is_correct=q['correct'],
            operation_type=operation
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
    
    # Use cast for PostgreSQL compatibility (SUM of boolean needs cast to int)
    from sqlalchemy import case
    
    # Get current operation mode (default to multiply if not set)
    operation_mode = session.get('operation_mode', 'multiply')
    
    # Handle legacy data where operation_type might be NULL (treat as multiply)
    op_filter = QuestionLog.operation_type == operation_mode
    if operation_mode == 'multiply':
        op_filter = or_(QuestionLog.operation_type == 'multiply', QuestionLog.operation_type == None)

    results = db.session.query(
        QuestionLog.number_base,
        func.sum(case((QuestionLog.is_correct == True, 1), else_=0)).label('correct'),
        func.count(QuestionLog.id).label('total')
    ).join(GameSession).filter(
        GameSession.user_id == user_id,
        op_filter
    ).group_by(QuestionLog.number_base).all()
    
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

@app.route('/api/heatmap')
@login_required
def get_heatmap():
    user_id = session['user_id']
    
    # Get detailed stats for each specific multiplication (base x mult)
    from sqlalchemy import case
    
    # Get current operation mode
    operation_mode = session.get('operation_mode', 'multiply')
    
    # Handle legacy data
    op_filter = QuestionLog.operation_type == operation_mode
    if operation_mode == 'multiply':
        op_filter = or_(QuestionLog.operation_type == 'multiply', QuestionLog.operation_type == None)

    results = db.session.query(
        QuestionLog.number_base,
        QuestionLog.number_mult,
        func.sum(case((QuestionLog.is_correct == True, 1), else_=0)).label('correct'),
        func.count(QuestionLog.id).label('total')
    ).join(GameSession).filter(
        GameSession.user_id == user_id,
        op_filter
    ).group_by(QuestionLog.number_base, QuestionLog.number_mult).all()
    
    # Build a 10x10 matrix of accuracy rates
    heatmap = {}
    for r in results:
        key = f"{r.number_base}x{r.number_mult}"
        c = int(r.correct) if r.correct else 0
        rate = round((c / r.total) * 100, 1) if r.total > 0 else None
        heatmap[key] = {
            'correct': c,
            'total': r.total,
            'rate': rate,
            'errors': r.total - c
        }
    
    return jsonify(heatmap)




# --- Teacher Mode Implementation ---

# Migration Check (Compatible with SQLite and PostgreSQL)
def check_and_migrate():
    try:
        with app.app_context():
            inspector = db.inspect(db.engine)
            is_postgres = 'postgresql' in str(db.engine.url)
            
            # Get proper table name (PostgreSQL needs quotes for reserved words)
            user_table = '"user"' if is_postgres else 'user'
            
            # Check if tables exist first
            tables = inspector.get_table_names()
            
            # Check for is_teacher column (only if user table exists)
            if 'user' in tables:
                user_columns = [c['name'] for c in inspector.get_columns('user')]
                if 'is_teacher' not in user_columns:
                    print("Migrating: Adding is_teacher to User table...")
                    try:
                        with db.engine.connect() as conn:
                            if is_postgres:
                                conn.execute(db.text(f'ALTER TABLE {user_table} ADD COLUMN is_teacher BOOLEAN DEFAULT FALSE'))
                            else:
                                conn.execute(db.text("ALTER TABLE user ADD COLUMN is_teacher BOOLEAN DEFAULT 0"))
                            conn.commit()
                    except Exception as e:
                        print(f"is_teacher column may already exist or error: {e}")
            
            # Check for approved column in student_classroom (only if table exists)
            if 'student_classroom' in tables:
                sc_columns = [c['name'] for c in inspector.get_columns('student_classroom')]
                if 'approved' not in sc_columns:
                    print("Migrating: Adding approved to StudentClassroom table...")
                    try:
                        with db.engine.connect() as conn:
                            if is_postgres:
                                conn.execute(db.text("ALTER TABLE student_classroom ADD COLUMN approved BOOLEAN DEFAULT FALSE"))
                            else:
                                conn.execute(db.text("ALTER TABLE student_classroom ADD COLUMN approved BOOLEAN DEFAULT 0"))
                            conn.commit()
                    except Exception as e:
                        print(f"approved column may already exist or error: {e}")

            # Check for operation_type in question_log
            if 'question_log' in tables:
                 ql_columns = [c['name'] for c in inspector.get_columns('question_log')]
                 if 'operation_type' not in ql_columns:
                     print("Migrating: Adding operation_type to QuestionLog...")
                     try:
                         with db.engine.connect() as conn:
                             # Same command for both SQLite and Postgres in this case
                             conn.execute(db.text("ALTER TABLE question_log ADD COLUMN operation_type VARCHAR(20) DEFAULT 'multiply'"))
                             conn.commit()
                     except Exception as e:
                         print(f"operation_type column error: {e}")
    except Exception as e:
        print(f"Migration check failed: {e}")
        # Don't crash the app, let db.create_all handle table creation

# Teacher Decorator
def teacher_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not (user.is_teacher or user.is_admin): # Admins can also access? Let's say yes or strict. for now is_teacher. 
            # Allow admins to access teacher panel too for debug? Or strict? 
            # Let's stick to is_teacher. Admin can grant himself teacher role.
            if not user.is_teacher:
                return redirect(url_for('menu'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/teacher')
@teacher_required
def teacher_dashboard():
    user = User.query.get(session['user_id'])
    classrooms = Classroom.query.filter_by(teacher_id=user.id).all()
    return render_template('teacher/dashboard.html', user=user, classrooms=classrooms)

@app.route('/teacher/create', methods=['POST'])
@teacher_required
def create_classroom():
    user = User.query.get(session['user_id'])
    
    # Limit check: 3 classes max
    current_count = Classroom.query.filter_by(teacher_id=user.id).count()
    if current_count >= 3:
        # Should show error, but for MVP redirect
        return redirect(url_for('teacher_dashboard'))
        
    name = request.form.get('name')
    if not name:
        return redirect(url_for('teacher_dashboard'))
        
    # Generate Code: 3 random letters + 3 random numbers
    import random, string
    chars = string.ascii_uppercase
    nums = string.digits
    code = ''.join(random.choice(chars) for _ in range(3)) + '-' + ''.join(random.choice(nums) for _ in range(3))
    
    # Ensure unique (simple retry)
    while Classroom.query.filter_by(code=code).first():
        code = ''.join(random.choice(chars) for _ in range(3)) + '-' + ''.join(random.choice(nums) for _ in range(3))
        
    new_class = Classroom(
        name=name,
        code=code,
        teacher_id=user.id
    )
    db.session.add(new_class)
    db.session.commit()
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/classroom/<int:id>')
@teacher_required
def view_classroom(id):
    user = User.query.get(session['user_id'])
    classroom = Classroom.query.get_or_404(id)
    
    # Security check
    if classroom.teacher_id != user.id and not user.is_admin:
        return redirect(url_for('teacher_dashboard'))
        
    # Get approved students
    approved_students = db.session.query(User, StudentClassroom.joined_at)\
        .join(StudentClassroom, StudentClassroom.student_id == User.id)\
        .filter(StudentClassroom.classroom_id == id, StudentClassroom.approved == True).all()
    
    # Get pending students
    pending_students = db.session.query(User, StudentClassroom.joined_at)\
        .join(StudentClassroom, StudentClassroom.student_id == User.id)\
        .filter(StudentClassroom.classroom_id == id, StudentClassroom.approved == False).all()
        
    # Process approved students
    student_data = []
    for s, joined in approved_students:
        total_score = db.session.query(func.sum(GameSession.score)).filter_by(user_id=s.id).scalar() or 0
        student_data.append({
            'id': s.id,
            'username': s.username,
            'joined_at': joined,
            'total_score': total_score,
            'level': get_level_data(total_score)['title']
        })
    
    # Process pending students
    pending_data = []
    for s, joined in pending_students:
        pending_data.append({
            'id': s.id,
            'username': s.username,
            'joined_at': joined
        })
        
    return render_template('teacher/classroom.html', classroom=classroom, students=student_data, pending_students=pending_data)

@app.route('/api/join_class', methods=['POST'])
@login_required
def join_class():
    code = request.form.get('code')
    if not code:
        return jsonify({'error': 'Código inválido'})
        
    classroom = Classroom.query.filter_by(code=code).first()
    if not classroom:
        return jsonify({'error': 'Turma não encontrada'})
        
    user_id = session['user_id']
    
    # Check if already joined (approved or pending)
    exists = StudentClassroom.query.filter_by(student_id=user_id, classroom_id=classroom.id).first()
    if exists:
        if exists.approved:
            return jsonify({'error': 'Você já está nesta turma!'})
        else:
            return jsonify({'error': 'Você já solicitou entrada nesta turma. Aguarde aprovação.'})
        
    new_entry = StudentClassroom(student_id=user_id, classroom_id=classroom.id, approved=False)
    db.session.add(new_entry)
    db.session.commit()
    
    return jsonify({'success': 'Solicitação enviada! Aguarde a aprovação do professor.', 'classname': classroom.name})

@app.route('/student/classroom')
@login_required
def student_classroom():
    user = User.query.get(session['user_id'])
    
    # Get all enrollments (approved and pending)
    enrollments = StudentClassroom.query.filter_by(student_id=user.id).all()
    class_data = []
    
    for enroll in enrollments:
        cls = enroll.classroom
        teacher = User.query.get(cls.teacher_id)
        
        # Only show tasks if approved
        task_list = []
        if enroll.approved:
            tasks = Homework.query.filter_by(classroom_id=cls.id).order_by(desc(Homework.created_at)).all()
            
            for t in tasks:
                sub = HomeworkSubmission.query.filter_by(homework_id=t.id, student_id=user.id).first()
                status = 'pending'
                score = None
                if sub:
                    status = 'completed'
                    score = f"{sub.score}/{sub.total_questions}"
                elif datetime.utcnow() > t.deadline:
                    status = 'late'
                    
                task_list.append({
                    'id': t.id,
                    'description': t.description,
                    'deadline': t.deadline,
                    'status': status,
                    'score': score,
                    'tables': t.tables_config
                })
            
        class_data.append({
            'id': cls.id,
            'name': cls.name,
            'teacher': teacher.username,
            'tasks': task_list,
            'approved': enroll.approved
        })
        
    return render_template('student/dashboard.html', classes=class_data)

# Teacher Task Management
@app.route('/teacher/classroom/<int:id>/create_task', methods=['POST'])
@teacher_required
def create_task(id):
    classroom = Classroom.query.get_or_404(id)
    # Auth check
    if classroom.teacher_id != session['user_id']:
        return redirect(url_for('teacher_dashboard'))
        
    start = request.form.get('start_table')
    end = request.form.get('end_table')
    days = request.form.get('days', type=int)
    
    if start and end and days:
        # Construct range string "3,4,5,6"
        s = int(start)
        e = int(end)
        if s > e: s, e = e, s
        tables = ",".join(str(i) for i in range(s, e + 1))
        
        desc = f"Tabuada do {s} ao {e}"
        if s == e:
             desc = f"Tabuada do {s}"
             
        deadline = datetime.utcnow() + timedelta(days=days)
        
        task = Homework(
            classroom_id=id,
            description=desc,
            tables_config=tables,
            deadline=deadline
        )
        db.session.add(task)
        db.session.commit()
        
    return redirect(url_for('view_classroom', id=id))

@app.route('/teacher/classroom/<int:id>/kick_student', methods=['POST'])
@teacher_required
def kick_student(id):
    classroom = Classroom.query.get_or_404(id)
    if classroom.teacher_id != session['user_id']:
        return redirect(url_for('teacher_dashboard'))
        
    student_id = request.form.get('student_id')
    entry = StudentClassroom.query.filter_by(classroom_id=id, student_id=student_id).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        
    return redirect(url_for('view_classroom', id=id))

@app.route('/teacher/classroom/<int:classroom_id>/approve/<int:student_id>', methods=['POST'])
@teacher_required
def approve_student(classroom_id, student_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    if classroom.teacher_id != session['user_id']:
        return redirect(url_for('teacher_dashboard'))
    
    enrollment = StudentClassroom.query.filter_by(classroom_id=classroom_id, student_id=student_id).first()
    if enrollment:
        enrollment.approved = True
        db.session.commit()
    
    return redirect(url_for('view_classroom', id=classroom_id))

@app.route('/teacher/classroom/<int:classroom_id>/reject/<int:student_id>', methods=['POST'])
@teacher_required
def reject_student(classroom_id, student_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    if classroom.teacher_id != session['user_id']:
        return redirect(url_for('teacher_dashboard'))
    
    enrollment = StudentClassroom.query.filter_by(classroom_id=classroom_id, student_id=student_id).first()
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
    
    return redirect(url_for('view_classroom', id=classroom_id))

@app.route('/api/leave_classroom/<int:classroom_id>', methods=['POST'])
@login_required
def leave_classroom(classroom_id):
    user_id = session['user_id']
    enrollment = StudentClassroom.query.filter_by(classroom_id=classroom_id, student_id=user_id).first()
    
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
        return jsonify({'success': 'Você saiu da turma.'})
    
    return jsonify({'error': 'Você não está nesta turma.'})


@app.route('/teacher/task/<int:id>/delete', methods=['POST'])
@teacher_required
def delete_task(id):
    task = Homework.query.get_or_404(id)
    # Check ownership via classroom
    cls = Classroom.query.get(task.classroom_id)
    if cls.teacher_id != session['user_id']:
         return redirect(url_for('teacher_dashboard'))
         
    # Cascade delete submissions
    HomeworkSubmission.query.filter_by(homework_id=id).delete()
    db.session.delete(task)
    db.session.commit()
    
    return redirect(url_for('view_classroom', id=cls.id))

@app.route('/teacher/homework/<int:id>')
@teacher_required
def view_homework_details(id):
    homework = Homework.query.get_or_404(id)
    classroom = Classroom.query.get(homework.classroom_id)
    
    # Auth check
    if classroom.teacher_id != session['user_id']:
        return redirect(url_for('teacher_dashboard'))
        
    # Get all students in the class
    students = db.session.query(User).join(StudentClassroom).filter(StudentClassroom.classroom_id == classroom.id).all()
    
    # Get all submissions for this homework
    submissions = HomeworkSubmission.query.filter_by(homework_id=id).all()
    submission_map = {s.student_id: s for s in submissions}
    
    student_details = []
    for student in students:
        sub = submission_map.get(student.id)
        status = "Pendente"
        score_display = "-"
        submitted_at = "-"
        is_late = False
        
        if sub:
            status = "Entregue"
            score_display = f"{sub.score} / {sub.total_questions}"
            submitted_at = sub.submitted_at.strftime('%d/%m/%Y %H:%M')
            is_late = sub.is_late
        elif datetime.utcnow() > homework.deadline:
            status = "Atrasado"
            
        student_details.append({
            'name': student.username,
            'status': status,
            'score': score_display,
            'submitted_at': submitted_at,
            'is_late': is_late,
            'correct_count': sub.score if sub else 0,
            'total_count': sub.total_questions if sub else 0
        })
        
    return render_template('teacher/homework_details.html', homework=homework, classroom=classroom, students=student_details)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        check_and_migrate()
    app.run(debug=True)
else:
    # Production (Gunicorn) - run migrations on import
    with app.app_context():
        db.create_all()
        check_and_migrate()
