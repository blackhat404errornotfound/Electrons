from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'electrons-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///electrons.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

# ====================== MODELS ======================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    github_link = db.Column(db.String(300))
    tech_stack = db.Column(db.String(200))
    image_url = db.Column(db.String(300))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='projects')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ====================== ROUTES ======================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        return redirect(url_for('dashboard'))
    flash('Invalid email or password!', 'error')
    return redirect(url_for('login_page'))

@app.route('/signup', methods=['POST'])
def signup():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    password = request.form.get('password')

    if User.query.filter_by(email=email).first():
        flash('Email already registered!', 'error')
        return redirect(url_for('signup_page'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(first_name=first_name, last_name=last_name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    flash('Account created successfully!', 'success')
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/projects')
@login_required
def projects():
    user_projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
    return render_template('projects.html', projects=user_projects)

# Submit New Project
@app.route('/submit-project', methods=['POST'])
@login_required
def submit_project():
    title = request.form.get('title')
    description = request.form.get('description')
    github_link = request.form.get('github_link')
    tech_stack = request.form.get('tech_stack')

    image_url = None
    if 'project_image' in request.files:
        file = request.files['project_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_url = f"uploads/{filename}"

    new_project = Project(
        title=title,
        description=description,
        github_link=github_link,
        tech_stack=tech_stack,
        image_url=image_url,
        user_id=current_user.id
    )
    db.session.add(new_project)
    db.session.commit()
    flash('Project added successfully!', 'success')
    return redirect(url_for('projects'))

# Edit Project
@app.route('/edit-project/<int:project_id>', methods=['POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash('Unauthorized!', 'error')
        return redirect(url_for('projects'))

    project.title = request.form.get('title')
    project.description = request.form.get('description')
    project.github_link = request.form.get('github_link')
    project.tech_stack = request.form.get('tech_stack')

    if 'project_image' in request.files:
        file = request.files['project_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            project.image_url = f"uploads/{filename}"

    db.session.commit()
    flash('Project updated successfully!', 'success')
    return redirect(url_for('projects'))

# Delete Project
@app.route('/delete-project/<int:project_id>')
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash('Unauthorized!', 'error')
        return redirect(url_for('projects'))

    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)