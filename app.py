# ============================================
# OAUTH INTEGRATION FOR SKILLVERIFY
# ============================================
# This shows how to add Google and GitHub OAuth to your Flask app

# 1. First, install required packages:
# pip install flask-dance

# 2. Update your main Flask app (app.py or main.py):

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import random
import os
import tempfile
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load variables from .env file into os.environ
load_dotenv()

from werkzeug.middleware.proxy_fix import ProxyFix

# Allow OAuth to work over HTTP locally and behind various proxies
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Relax token scope to prevent crashes when Google returns different scopes than requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

app = Flask(__name__)

# Tell Flask it is behind a proxy (like Render) so it generates HTTPS redirect URLs correctly
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
app.config['PREFERRED_URL_SCHEME'] = 'https'
# ============= GEMINI CONFIGURATION =============
api_key = os.environ.get('GEMINI_API_KEY')
if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None
    print("WARNING: GEMINI_API_KEY not set. AI features will be disabled.")

# ============= CONFIGURATION =============
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Use DATABASE_URL from environment for production (Supabase) or fallback to local SQLite
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///skillverify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Session cookie configuration for Vercel (serverless)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'   # Required for cross-site OAuth flows
app.config['SESSION_COOKIE_SECURE'] = True        # Required when SameSite=None
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_NAME'] = 'skillverify_session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_PERMANENT'] = True            # Make all sessions permanent by default

# ============= MAIL CONFIGURATION =============
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
mail = Mail(app)

# OAuth Configuration
# Google OAuth - Get credentials from https://console.cloud.google.com/
app.config['GOOGLE_OAUTH_CLIENT_ID'] = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')

# GitHub OAuth - Get credentials from https://github.com/settings/developers
app.config['GITHUB_OAUTH_CLIENT_ID'] = os.environ.get('GITHUB_OAUTH_CLIENT_ID')
app.config['GITHUB_OAUTH_CLIENT_SECRET'] = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET')

db = SQLAlchemy(app)

# ============= OAUTH BLUEPRINTS =============
# Google OAuth Blueprint
google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=['profile', 'email'],
    redirect_to='google_callback'
)
app.register_blueprint(google_bp, url_prefix='/login')

# GitHub OAuth Blueprint
github_bp = make_github_blueprint(
    client_id=app.config['GITHUB_OAUTH_CLIENT_ID'],
    client_secret=app.config['GITHUB_OAUTH_CLIENT_SECRET'],
    scope='user:email',
    redirect_to='github_callback'
)
app.register_blueprint(github_bp, url_prefix='/login')

# ============= DATABASE MODELS =============
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth users
    name = db.Column(db.String(100))
    oauth_provider = db.Column(db.String(50))  # 'google', 'github', or None
    oauth_id = db.Column(db.String(200))  # Legacy fallback / unified primary ID
    google_id = db.Column(db.String(200), unique=True, nullable=True)
    github_id = db.Column(db.String(200), unique=True, nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # New settings fields
    email_notifications = db.Column(db.Boolean, default=True)
    push_notifications = db.Column(db.Boolean, default=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=True)
    
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'profile_image': self.profile_image or '/static/images/default-avatar.png',
            'oauth_provider': self.oauth_provider,
            'created_at': self.created_at.isoformat(),
            'google_id': self.google_id,
            'github_id': self.github_id,
            'email_notifications': self.email_notifications,
            'push_notifications': self.push_notifications,
            'two_factor_enabled': self.two_factor_enabled,
            'is_public': self.is_public
        }


@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    if user_id:
        try:
            # Add a small timeout to avoid hanging serverless functions
            user = User.query.get(user_id)
            if user:
                return dict(logged_in_user=user)
        except Exception as e:
            print(f"Context Processor Error: {e}")
            # If DB is down, just treat as guest rather than 500ing the whole site
            return dict(logged_in_user=None)
    return dict(logged_in_user=None)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_readiness = db.Column(db.Integer, default=0)
    verified_skills = db.Column(db.Integer, default=0)
    total_xp = db.Column(db.Integer, default=0)
    certifications = db.Column(db.Integer, default=0)
    survey_insight = db.Column(db.Text, nullable=True)
    cv_score = db.Column(db.Integer, nullable=True)
    cv_feedback = db.Column(db.Text, nullable=True)
    certificate_score = db.Column(db.Integer, nullable=True)
    certificate_feedback = db.Column(db.Text, nullable=True)
    cv_filename = db.Column(db.String(255), nullable=True)
    certificate_filename = db.Column(db.String(255), nullable=True)
    ai_profile_impact = db.Column(db.Integer, default=0)
    file_log_json = db.Column(db.Text, nullable=True)
    
    # New Skill Verify fields
    visible_to_recruiters = db.Column(db.Boolean, default=True)
    open_to_opportunities = db.Column(db.Boolean, default=False)
    account_type = db.Column(db.String(50), default='job_seeker')
    
    def to_dict(self):
        return {
            'skill_readiness': self.skill_readiness,
            'verified_skills': self.verified_skills,
            'total_xp': self.total_xp,
            'certifications': self.certifications,
            'survey_insight': self.survey_insight,
            'cv_score': min(100, self.cv_score) if self.cv_score is not None else None,
            'cv_feedback': self.cv_feedback,
            'certificate_score': min(100, self.certificate_score) if self.certificate_score is not None else None,
            'certificate_feedback': self.certificate_feedback,
            'cv_filename': self.cv_filename,
            'certificate_filename': self.certificate_filename,
            'ai_profile_impact': self.ai_profile_impact,
            'file_log_json': self.file_log_json,
            'visible_to_recruiters': self.visible_to_recruiters,
            'open_to_opportunities': self.open_to_opportunities,
            'account_type': self.account_type
        }

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True) # e.g. "Tech & Coding"
    tags = db.Column(db.String(255), nullable=True)     # stored as comma-separated "#React,#JavaScript"
    likes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref=db.backref('posts', lazy=True))

    def to_dict(self, current_user_id=None):
        import random
        random_names = ["Alex M.", "Sarah C.", "Marcus R.", "Priya S.", "David T.", "Emma W.", "James K.", "Sofia G.", "Chris J.", "Taylor L."]
        
        # Determine if we should use the system user or a random name
        is_system_user = self.author and self.author.email == "demo@skillverify.com"
        
        if is_system_user:
            random.seed(self.user_id + self.id) # Seed so it's consistent for this post/user combo
            display_name = random.choice(random_names)
            author_image = '/static/images/default-avatar.png' # System users always get generic
            random.seed() # Reset seed
        else:
            display_name = self.author.name if self.author else "Anonymous"
            # Real users get their pfp or generic
            author_image = self.author.profile_image if self.author and self.author.profile_image else '/static/images/default-avatar.png'
        
        has_liked = False
        has_saved = False
        if current_user_id:
            has_liked = PostLike.query.filter_by(user_id=current_user_id, post_id=self.id).first() is not None
            has_saved = SavedPost.query.filter_by(user_id=current_user_id, post_id=self.id).first() is not None
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'author_name': display_name,
            'author_image': author_image,
            'content': self.content,
            'category': self.category,
            'tags': self.tags.split(',') if self.tags else [],
            'likes': self.likes,
            'comments_count': self.comments_count,
            'has_liked': has_liked,
            'has_saved': has_saved,
            'created_at': self.created_at.isoformat()
        }

class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class SavedPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref=db.backref('comments', lazy=True))
    
    def to_dict(self):
        import random
        random_names = ["Alex M.", "Sarah C.", "Marcus R.", "Priya S.", "David T.", "Emma W.", "James K.", "Sofia G.", "Chris J.", "Taylor L."]
        
        is_system_user = self.author and self.author.email == "demo@skillverify.com"
        if is_system_user:
            random.seed(self.user_id + self.id) # Seed so it's consistent
            display_name = random.choice(random_names)
            author_image = '/static/images/default-avatar.png'
            random.seed() # Reset seed
        else:
            display_name = self.author.name if self.author else "Anonymous"
            author_image = self.author.profile_image if self.author and self.author.profile_image else '/static/images/default-avatar.png'
            
        return {
            'id': self.id,
            'user_id': self.user_id,
            'post_id': self.post_id,
            'author_name': display_name,
            'author_image': author_image,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }

# ============= OAUTH ROUTES =============

@app.route('/auth/google')
def google_login_route():
    """Initiate Google OAuth login"""
    if not google.authorized:
        return redirect(url_for('google.login'))
    return redirect(url_for('google_callback'))

@app.route('/login/google/callback')
def google_callback():
    """Google OAuth callback"""
    if not google.authorized:
        return jsonify({'success': False, 'message': 'Failed to log in with Google'}), 400
    
    # Get user info from Google
    resp = google.get('/oauth2/v2/userinfo')
    if not resp.ok:
        return jsonify({'success': False, 'message': 'Failed to fetch user info from Google'}), 400
    
    google_info = resp.json()
    google_id = google_info['id']
    email = google_info['email']
    name = google_info.get('name', '')
    
    # CASE 1: User is already logged in (Linking scenario)
    current_uid = session.get('user_id')
    if current_uid:
        user = User.query.get(current_uid)
        # Check if this Google ID is already linked to ANOTHER account
        other_user = User.query.filter(User.google_id == google_id, User.id != current_uid).first()
        if other_user:
            return redirect(url_for('user_profile', error='This Google account is already linked to another SkillVerify profile.'))
        
        user.google_id = google_id
        if not user.oauth_provider: # If native, keep it native but track this link
            pass 
        db.session.commit()
        return redirect(url_for('user_profile', message='Google account linked successfully!'))

    # CASE 2: Not logged in (Login scenario)
    # Check by google_id first
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        # Fallback to legacy oauth_id or email
        user = User.query.filter_by(oauth_provider='google', oauth_id=google_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                # Link it now for future logins
                user.google_id = google_id
                db.session.commit()
    
    if not user:
        # Check if email already exists with different provider
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Generate OTP for existing user
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['pending_user_id'] = existing_user.id
            
            # Send OTP via Email
            try:
                msg_email = Message('Your Verification Code - SkillVerify', 
                              sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'), 
                              recipients=[email])
                msg_email.body = f'Your verification code is: {otp}\n\nPlease enter this code to complete your login.\n\nBest regards,\nThe SkillVerify Team'
                msg_email.html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
                    <h2 style="color: #4f46e5; text-align: center;">SkillVerify Verification</h2>
                    <p>Hello,</p>
                    <p>Your verification code is:</p>
                    <div style="text-align: center; margin: 20px 0;">
                        <span style="font-size: 24px; font-weight: bold; padding: 10px 20px; background-color: #f3f4f6; border-radius: 5px; letter-spacing: 2px;">{otp}</span>
                    </div>
                    <p>Please enter this code to complete your login securely. This code is valid for a limited time.</p>
                    <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
                    <p style="font-size: 12px; color: #777;">If you did not request this code, please securely ignore this email.</p>
                    <p style="font-size: 12px; color: #777;">Best regards,<br><strong>The SkillVerify Team</strong></p>
                </div>
                """
                mail.send(msg_email)
                print(f"DEBUG: OAuth collision OTP sent to {email}: {otp}")
            except Exception as e:
                print(f"ERROR: Failed to send email: {e}")
                print(f"DEBUG: OAuth collision OTP for {email} (Fallback): {otp}")
                
            return redirect(url_for('index', show_otp='true', message='Verification code sent to your email.'))
        
        # Create new user
        user = User(
            email=email,
            name=name,
            oauth_provider='google',
            oauth_id=google_id
        )
        db.session.add(user)
        db.session.commit()
        
        # Create profile
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    
    # Log user in
    session['user_id'] = user.id
    session['email'] = user.email
    session.permanent = True
    
    return redirect(url_for('index'))

@app.route('/auth/github')
def github_login_route():
    """Initiate GitHub OAuth login"""
    if not github.authorized:
        return redirect(url_for('github.login'))
    return redirect(url_for('github_callback'))

@app.route('/login/github/callback')
def github_callback():
    """GitHub OAuth callback"""
    if not github.authorized:
        return jsonify({'success': False, 'message': 'Failed to log in with GitHub'}), 400
    
    # Get user info from GitHub
    resp = github.get('/user')
    if not resp.ok:
        return jsonify({'success': False, 'message': 'Failed to fetch user info from GitHub'}), 400
    
    github_info = resp.json()
    github_id = str(github_info['id'])
    name = github_info.get('name', github_info.get('login', ''))
    
    # CASE 1: Already logged in (Linking)
    current_uid = session.get('user_id')
    if current_uid:
        user = User.query.get(current_uid)
        other_user = User.query.filter(User.github_id == github_id, User.id != current_uid).first()
        if other_user:
            return redirect(url_for('index'))
        
        user.github_id = github_id
        db.session.commit()
        return redirect(url_for('index'))

    # CASE 2: Login scenario
    user = User.query.filter_by(github_id=github_id).first()
    
    if not user:
        email_resp = github.get('/user/emails')
        emails = email_resp.json() if email_resp.ok else []
        email = next((e['email'] for e in emails if e['primary']), None)
        
        if not email:
            return jsonify({
                'success': False, 
                'message': 'Could not retrieve email from GitHub.'
            }), 400
            
        # Check by legacy or email
        user = User.query.filter_by(oauth_provider='github', oauth_id=github_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.github_id = github_id
                db.session.commit()
    
    if not user:
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Generate OTP for existing user
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['pending_user_id'] = existing_user.id
            
            # Send OTP via Email
            try:
                msg_email = Message('Your Verification Code - SkillVerify', 
                              sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'), 
                              recipients=[email])
                msg_email.body = f'Your verification code is: {otp}\n\nPlease enter this code to complete your login.\n\nBest regards,\nThe SkillVerify Team'
                msg_email.html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
                    <h2 style="color: #4f46e5; text-align: center;">SkillVerify Verification</h2>
                    <p>Hello,</p>
                    <p>Your verification code is:</p>
                    <div style="text-align: center; margin: 20px 0;">
                        <span style="font-size: 24px; font-weight: bold; padding: 10px 20px; background-color: #f3f4f6; border-radius: 5px; letter-spacing: 2px;">{otp}</span>
                    </div>
                    <p>Please enter this code to complete your login securely. This code is valid for a limited time.</p>
                    <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
                    <p style="font-size: 12px; color: #777;">If you did not request this code, please securely ignore this email.</p>
                    <p style="font-size: 12px; color: #777;">Best regards,<br><strong>The SkillVerify Team</strong></p>
                </div>
                """
                mail.send(msg_email)
                print(f"DEBUG: OAuth collision OTP sent to {email}: {otp}")
            except Exception as e:
                print(f"ERROR: Failed to send email: {e}")
                print(f"DEBUG: OAuth collision OTP for {email} (Fallback): {otp}")
                
            return redirect(url_for('index', show_otp='true', message='Verification code sent to your email.'))
        
        # Create new user
        user = User(
            email=email,
            name=name,
            oauth_provider='github',
            oauth_id=github_id
        )
        db.session.add(user)
        db.session.commit()
        
        # Create profile
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    
    # Log user in
    session['user_id'] = user.id
    session['email'] = user.email
    session.permanent = True
    
    return redirect(url_for('index'))

# ============= REGULAR AUTH ROUTES =============

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user with OTP verification"""
    data = request.get_json() or {}
    
    # === PHASE 2: OTP VERIFICATION ===
    if 'otp' in data:
        otp_input = data.get('otp')
        
        # Check if we have pending registration data
        if 'pending_registration' not in session or 'otp' not in session:
            return jsonify({'success': False, 'message': 'Session expired. Please try registering again.'}), 400
        
        # Verify OTP
        if session.get('otp') == otp_input:
            reg_data = session['pending_registration']
            
            # Double check if user exists (edge case)
            if User.query.filter_by(email=reg_data['email']).first():
                return jsonify({'success': False, 'message': 'Email already registered'}), 400

            # Create User
            user = User(email=reg_data['email'], name=reg_data['name'])
            user.password_hash = reg_data['password_hash'] # Already hashed
            db.session.add(user)
            db.session.commit()
            
            # Create default profile
            profile = UserProfile(
                user_id=user.id,
                skill_readiness=0,
                verified_skills=0,
                total_xp=0,
                certifications=0
            )
            db.session.add(profile)
            db.session.commit()
            
            # Clear session and Auto-Login
            session.pop('otp', None)
            session.pop('pending_registration', None)
            
            session['user_id'] = user.id
            session['email'] = user.email
            session.permanent = True
            
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': user.to_dict()
            }), 201
        else:
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400

    # === PHASE 1: INITIAL REGISTRATION REQUEST ===
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['pending_registration'] = {
        'email': email,
        'name': name,
        'password_hash': generate_password_hash(password)
    }
    
    # Send OTP via Email
    try:
        msg = Message('Verify Your Account - SkillVerify', 
                      sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'), 
                      recipients=[email])
        msg.body = f'Your verification code is: {otp}\n\nPlease enter this code to complete your registration.\n\nBest regards,\nThe SkillVerify Team'
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4f46e5; text-align: center;">Welcome to SkillVerify!</h2>
            <p>Hello,</p>
            <p>Thank you for registering. Your verification code is:</p>
            <div style="text-align: center; margin: 20px 0;">
                <span style="font-size: 24px; font-weight: bold; padding: 10px 20px; background-color: #f3f4f6; border-radius: 5px; letter-spacing: 2px;">{otp}</span>
            </div>
            <p>Please enter this code to complete your registration securely.</p>
            <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
            <p style="font-size: 12px; color: #777;">Best regards,<br><strong>The SkillVerify Team</strong></p>
        </div>
        """
        mail.send(msg)
        print(f"DEBUG: Registration OTP sent to {email}: {otp}")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")
        print(f"DEBUG: Registration OTP for {email} (Fallback): {otp}")

    return jsonify({
        'success': False,
        'otp_required': True,
        'message': 'Verification code sent to your email'
    }), 200

@app.route('/api/login', methods=['POST'])
def login():
    """Login user with OTP verification"""
    data = request.get_json() or {}
    
    # OTP Verification Phase
    if 'otp' in data:
        otp_input = data.get('otp')
        
        # Check if we have a pending login session
        if 'pending_user_id' not in session or 'otp' not in session:
            return jsonify({'success': False, 'message': 'Session expired. Please try logging in again.'}), 400
        
        # Verify OTP
        if session.get('otp') == otp_input:
            user_id = session['pending_user_id']
            user = User.query.get(user_id)
            
            if not user:
                 return jsonify({'success': False, 'message': 'User not found'}), 400

            # Clear temporary session data
            session.pop('otp', None)
            session.pop('pending_user_id', None)
            
            # Finalize Login
            session['user_id'] = user.id
            session['email'] = user.email
            session.permanent = True # Always make it permanent for better experience on Vercel
            
            if session.get('_remember_me'):
                session.pop('_remember_me', None)
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400

    # Initial Login Phase (Email/Password)
    email = data.get('email')
    password = data.get('password')
    remember_me = data.get('rememberMe', False)
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    if not user.check_password(password):
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['pending_user_id'] = user.id
    if remember_me:
        session['_remember_me'] = True
    
    # Send OTP via Email
    try:
        msg = Message('Your Verification Code - SkillVerify', 
                      sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'), 
                      recipients=[email])
        msg.body = f'Your verification code is: {otp}\n\nPlease enter this code to complete your login.\n\nBest regards,\nThe SkillVerify Team'
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4f46e5; text-align: center;">SkillVerify Verification</h2>
            <p>Hello,</p>
            <p>Your verification code is:</p>
            <div style="text-align: center; margin: 20px 0;">
                <span style="font-size: 24px; font-weight: bold; padding: 10px 20px; background-color: #f3f4f6; border-radius: 5px; letter-spacing: 2px;">{otp}</span>
            </div>
            <p>Please enter this code to complete your login securely. This code is valid for a limited time.</p>
            <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
            <p style="font-size: 12px; color: #777;">If you did not request this code, please securely ignore this email.</p>
            <p style="font-size: 12px; color: #777;">Best regards,<br><strong>The SkillVerify Team</strong></p>
        </div>
        """
        mail.send(msg)
        print(f"DEBUG: OTP sent to {email}: {otp}")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")
        # For development/demo purposes, print OTP to console
        print(f"DEBUG: OTP for {email} (Fallback): {otp}")
    
    return jsonify({
        'success': False,
        'otp_required': True,
        'message': 'Verification code sent to your email'
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """Get dashboard data for logged-in user"""
    # print(f"DEBUG: get_dashboard_data session: {session}")
    user_id = session.get('user_id')
    
    if not user_id:
        # Return default data if not logged in
        return jsonify({
            'success': True,
            'user': None,
            'stats': {
                'skill_readiness': 87,
                'verified_skills': 12,
                'total_xp': 2450,
                'certifications': 5
            },
            'challenges': []
        }), 200
    
    user = User.query.get(user_id)
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'stats': profile.to_dict() if profile else {},
        'challenges': []
    }), 200

@app.route('/api/submit-survey', methods=['POST'])
def submit_survey():
    """Submit career test survey and generate AI insights"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to submit survey'}), 401
    
    data = request.get_json()
    
    insight_text = ""
    if client:
        try:
            prompt = f"""
            Act as an expert career counselor. Analyze the following career survey responses from a user and provide:
            1. A concise, encouraging paragraph with personalized career insights based on their interests, skills, and goals.
            2. A bulleted list of 3 specific, highly relevant websites, courses, or resources that can help them explore these career paths further (include actual URLs).
            3. At the very end, provide exactly 4 recommended careers formatted strictly as JSON inside a <recommended> block. Use material symbols names for icons. 
            Example format:
            <recommended>
            [
              {{"title": "Software Engineer", "icon": "code"}},
              {{"title": "Graphic Designer", "icon": "brush"}},
              {{"title": "Business Analyst", "icon": "trending_up"}},
              {{"title": "Registered Nurse", "icon": "medical_services"}}
            ]
            </recommended>
            
            Survey Responses:
            {data}
            """
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            insight_text = response.text
        except Exception as e:
            print(f"Error generating insight: {e}")
            insight_text = "Your survey has been recorded! Unfortunately, our AI is currently unavailable to generate personalized insights right now. Please check back later."
    else:
        insight_text = "Your survey has been recorded! AI insights are currently disabled because the GEMINI_API_KEY is not set."

    # Save to the user profile
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        
    profile.survey_insight = insight_text
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Survey submitted successfully',
        'insight': insight_text
    }), 201

@app.route('/api/update-profile', methods=['PUT'])
def update_profile():
    """Update user profile stats"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
    
    if 'skill_readiness' in data:
        profile.skill_readiness = data['skill_readiness']
    if 'verified_skills' in data:
        profile.verified_skills = data['verified_skills']
    if 'total_xp' in data:
        profile.total_xp = data['total_xp']
    if 'certifications' in data:
        profile.certifications = data['certifications']
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully',
        'profile': profile.to_dict()
    }), 200

@app.route('/api/analyze-cv', methods=['POST'])
def analyze_cv():
    """Upload and analyze a CV or certificate using Gemini"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to use this feature.'}), 401
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded.'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file.'}), 400
        
    if not client:
        return jsonify({'success': False, 'message': 'AI features are currently disabled.'}), 500
        
    # Save file temporarily
    filename = secure_filename(file.filename)
    extension = os.path.splitext(filename)[1]
    
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
        file.save(temp.name)
        temp_path = temp.name
        
    try:
        # Upload to Gemini
        print(f"DEBUG: Uploading {temp_path} to Gemini...")
        uploaded_file = client.files.upload(file=temp_path)
        
        prompt = """
        Act as an expert career counselor and recruiter. Read the attached resume, CV, or certificate carefully.
        Evaluate it against industry standards for impact, clarity, and skills representation.
        Provide exactly the following format in your response:
        SCORE: <A robust number from 0 to 100 representing the overall quality and impact>
        FEEDBACK: <A concise, encouraging paragraph of constructive feedback, highlighting key strengths and the most important area for improvement>
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, uploaded_file]
        )
        
        text = response.text
        
        # Parse output
        score = 0
        feedback = "We could not generate detailed feedback at this time."
        
        score_match = re.search(r'SCORE:\s*(\d+)', text, re.IGNORECASE)
        if score_match:
            score = int(score_match.group(1))
            
        feedback_match = re.search(r'FEEDBACK:\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        if feedback_match:
            feedback = feedback_match.group(1).strip()
            
        # Update user profile
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)
            
        profile.cv_score = score
        profile.cv_feedback = feedback
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'CV analyzed successfully',
            'score': score,
            'feedback': feedback
        }), 200
        
    except Exception as e:
        print(f"Error analyzing document with Gemini: {e}")
        return jsonify({'success': False, 'message': 'Error analyzing document. Make sure it is a supported format (PDF, TXT, DOCX, PNG, JPEG).'}), 500
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        # Clean up Gemini uploaded file (if it exists)
        try:
            if 'uploaded_file' in locals():
                client.files.delete(name=uploaded_file.name)
        except Exception as e:
            print(f"Failed to delete Gemini temporary file: {e}")

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Chat API endpoint powered by Gemini"""
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({'success': False, 'message': 'Message is required'}), 400
        
    try:
        from google import genai
        from google.genai import types
        # Try to use environment variable first, then fallback to the known working key test_api.py
        local_api_key = os.environ.get('GEMINI_API_KEY', "AIzaSyAk0Rxl3-e96BTkdAN1xkhauPjVoGqs5Rg")
        if not local_api_key:
            return jsonify({'success': False, 'message': 'AI features are disabled due to missing API key.'}), 500
            
        client = genai.Client(api_key=local_api_key)
        
        # Use a system instruction to instruct the AI Model to act as a career counselor 
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert career guidance counselor and assistant for SkillVerify. SkillVerify is a career advancement platform with AI-powered assessments, skill verification, and real-world challenges. Be very concise, helpful, and friendly. Answer career-related questions and provide guidance."
            )
        )
        
        if response and response.text:
            return jsonify({'success': True, 'message': response.text}), 200
        else:
            return jsonify({'success': False, 'message': "I'm sorry, I couldn't generate a response."}), 500
            
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"Chat error: {e}\\n{err}")
        return jsonify({'success': False, 'message': "I'm sorry, I'm having trouble connecting to my brain right now.", "error": err}), 500

@app.route('/api/upload-document', methods=['POST'])
def upload_document():
    """Upload CV or Certificate for AI analysis"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
    doc_type = request.form.get('type') # 'cv' or 'certificate'
    if doc_type not in ['cv', 'certificate']:
        return jsonify({'success': False, 'message': 'Invalid document type'}), 400
        
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
        
    if file:
        import os
        from werkzeug.utils import secure_filename
        
        # Save temp file
        temp_dir = os.path.join(app.root_path, 'tmp')
        os.makedirs(temp_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)
        
        try:
            # Check if Gemini is configured
            local_api_key = os.environ.get('GEMINI_API_KEY')
            if not local_api_key:
                return jsonify({'success': False, 'message': 'AI features are disabled due to missing API key.'}), 500
                
            ai_client = genai.Client(api_key=local_api_key)
            
            # Upload file to Gemini
            ai_file = ai_client.files.upload(file=filepath)
            
            # Analyze
            prompt = f"Analyze this {doc_type}. Assess its quality, relevance, and impact. Return exactly a JSON object with two keys: 'score' (an integer from 0 to 100 representing its overall quality/strength) and 'feedback' (a short 2-3 sentence paragraph with constructive feedback and the key highlights). Do not include any markdown formatting like ```json in your response, just the raw JSON."
            
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[ai_file, prompt]
            )
            
            import json
            import re
            
            # Clean up response to parse JSON
            response_text = response.text.strip()
            # Remove Markdown code blocks if present
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            ai_result = json.loads(response_text)
            
            score_val = int(ai_result.get('score', 0))
            score = min(100, max(0, score_val))
            feedback = ai_result.get('feedback', 'No feedback provided.')
            
            # Update Database
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            if not profile:
                profile = UserProfile(user_id=user_id)
                db.session.add(profile)
                
            if doc_type == 'cv':
                profile.cv_score = score
                profile.cv_feedback = feedback
                profile.cv_filename = filename
            else:
                profile.certificate_score = score
                profile.certificate_feedback = feedback
                profile.certificate_filename = filename
                
            profile.certifications = (profile.certifications or 0) + 1
            
            # Add to file log
            log = []
            if profile.file_log_json:
                try:
                    log = json.loads(profile.file_log_json)
                except:
                    log = []
            log.append({
                "filename": filename,
                "type": doc_type,
                "score": score
            })
            profile.file_log_json = json.dumps(log)
            
            # Update AI Profile Impact (no cap limit)
            current_impact = profile.ai_profile_impact or 0
            profile.ai_profile_impact = current_impact + score
            
            # Update Skill Readiness and XP
            profile.skill_readiness = min(100, (profile.skill_readiness or 0) + 5)
            profile.total_xp = (profile.total_xp or 0) + 500
            
            db.session.commit()
            
            # Delete temp file
            if os.path.exists(filepath):
                os.remove(filepath)
                
            # Clean up Gemini file
            ai_client.files.delete(name=ai_file.name)
            
            return jsonify({
                'success': True,
                'score': score,
                'feedback': feedback,
                'message': 'Analysis complete'
            }), 200
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/reset-document-score', methods=['POST'])
def reset_document_score():
    """Reset the user's document analysis scores"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to use this feature.'}), 401
    
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if profile:
        profile.cv_score = None
        profile.cv_feedback = None
        profile.cv_filename = None
        profile.certificate_score = None
        profile.certificate_feedback = None
        profile.certificate_filename = None
        profile.skill_readiness = 0
        profile.verified_skills = 0
        profile.total_xp = 0
        profile.certifications = 0
        profile.ai_profile_impact = 0
        profile.file_log_json = '[]'
        db.session.commit()
        
    return jsonify({'success': True, 'message': 'Scores reset successfully.'}), 200

@app.route('/api/delete-document', methods=['POST'])
def delete_document():
    """Delete a specific document and its score"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in.'}), 401
    
    doc_type = request.json.get('type') if request.is_json else None
    doc_index = request.json.get('index') if request.is_json else None
    
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if profile:
        if doc_index is not None:
            import json
            log = []
            if profile.file_log_json:
                try:
                    log = json.loads(profile.file_log_json)
                except:
                    log = []
            
            if 0 <= doc_index < len(log):
                removed_item = log.pop(doc_index)
                score_to_subtract = removed_item.get('score', 0)
                profile.file_log_json = json.dumps(log)
                profile.ai_profile_impact = max(0, (profile.ai_profile_impact or 0) - score_to_subtract)
        
        # Keep old type logic for fallback/editing cases
        if doc_type == 'cv':
            profile.cv_score = None
            profile.cv_feedback = None
            profile.cv_filename = None
        elif doc_type == 'certificate':
            profile.certificate_score = None
            profile.certificate_feedback = None
            profile.certificate_filename = None
        db.session.commit()
        
    return jsonify({'success': True, 'message': 'Document deleted successfully.'}), 200

@app.route('/api/schedule_demo', methods=['POST'])
def schedule_demo():
    """Endpoint for scheduling a demo from organizations page"""
    data = request.get_json() or {}
    date = data.get('date', 'Unknown Date')
    time = data.get('time', 'Unknown Time')
    customer_email = data.get('email', '')
    
    try:
        msg = Message('New Demo Scheduled',
                      sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'),
                      recipients=['manaspandya2006@gmail.com'])
        msg.body = f"A new demo has been scheduled!\n\nDate: {date}\nTime: {time}\nCustomer Email: {customer_email}\n\nPlease follow up."
        msg.html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4f46e5;">New Demo Scheduled</h2>
            <p><strong>Action Required:</strong> A new demo has been scheduled.</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; width: 35%;">Date</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Time</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{time}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Submitter's Email</td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><a href="mailto:{customer_email}" style="color: #4f46e5;">{customer_email}</a></td>
                </tr>
            </table>
            <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
            <p style="font-size: 12px; color: #777;">Automated message from your SkillVerify System.</p>
        </div>
        '''
        mail.send(msg)

        if customer_email:
            msg_customer = Message('Demo Scheduling Confirmation - SkillVerify',
                          sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'),
                          recipients=[customer_email])
            msg_customer.body = f"Hi there,\n\nYour demo request has been successfully scheduled.\n\nDate: {date}\nTime: {time}\n\nOur team will reach out to you shortly with more details.\n\nBest regards,\nThe SkillVerify Team"
            msg_customer.html = f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
                <h2 style="color: #4f46e5; text-align: center;">SkillVerify Demo Confirmation</h2>
                <p>Hello,</p>
                <p>Thank you for expressing interest in SkillVerify! Your demo request has been successfully scheduled.</p>
                <div style="background-color: #f9fafb; padding: 15px; border-radius: 8px; margin: 20px 0; border: 1px solid #e5e7eb;">
                    <p style="margin: 5px 0;"><strong>Scheduled Date:</strong> {date}</p>
                    <p style="margin: 5px 0;"><strong>Scheduled Time:</strong> {time}</p>
                </div>
                <p>One of our team members will review your request and connect with you shortly with further instructions and the meeting link.</p>
                <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
                <p style="font-size: 12px; color: #777; text-align: center;">We look forward to speaking with you!</p>
                <p style="font-size: 12px; color: #777; text-align: center;">Best regards,<br><strong>The SkillVerify Team</strong></p>
            </div>
            '''
            mail.send(msg_customer)

        return jsonify({'success': True, 'message': 'Demo scheduled successfully'}), 200
    except Exception as e:
        print(f"ERROR: Failed to send demo schedule email: {e}")
        return jsonify({'success': False, 'message': 'Failed to schedule demo'}), 500


@app.route('/user_profile')
def user_profile():
    """Render the user profile page"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    user = User.query.get(user_id)
    return render_template('user_profile.html', user=user.to_dict())

@app.route('/api/user/update', methods=['POST'])
def update_user_info():
    """Update user's name or email"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    user = User.query.get(user_id)
    
    if 'name' in data:
        user.name = data['name']
    
    if 'email' in data:
        new_email = data['email']
        if new_email != user.email:
            existing = User.query.filter_by(email=new_email).first()
            if existing:
                return jsonify({'success': False, 'message': 'Email already in use'}), 400
            user.email = new_email
            session['email'] = new_email
            
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated successfully', 'user': user.to_dict()})

@app.route('/api/user/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    old_password = data.get('oldPassword')
    new_password = data.get('newPassword')
    
    user = User.query.get(user_id)
    
    if user.oauth_provider and not user.password_hash:
        # OAuth user setting password for the first time
        user.set_password(new_password)
    else:
        if not user.check_password(old_password):
            return jsonify({'success': False, 'message': 'Incorrect current password'}), 400
        user.set_password(new_password)
        
    db.session.commit()
    return jsonify({'success': True, 'message': 'Password changed successfully'})

@app.route('/api/user/settings', methods=['POST'])
def update_settings():
    """Update user preferences and privacy settings"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    user = User.query.get(user_id)
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
    
    # User settings
    if 'email_notifications' in data:
        user.email_notifications = data['email_notifications']
    if 'push_notifications' in data:
        user.push_notifications = data['push_notifications']
    if 'two_factor_enabled' in data:
        user.two_factor_enabled = data['two_factor_enabled']
    if 'is_public' in data:
        user.is_public = data['is_public']
        
    # Profile settings
    if 'visible_to_recruiters' in data:
        profile.visible_to_recruiters = data['visible_to_recruiters']
    if 'open_to_opportunities' in data:
        profile.open_to_opportunities = data['open_to_opportunities']
    if 'account_type' in data:
        profile.account_type = data['account_type']
        
    db.session.commit()
    return jsonify({'success': True, 'message': 'Settings updated successfully'})

@app.route('/api/user/unlink/<provider>', methods=['POST'])
def unlink_account(provider):
    """Unlink an OAuth account with safety checks"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    
    # Safety Check: Must have at least one other login method
    methods = 0
    if user.password_hash: methods += 1
    if user.google_id: methods += 1
    if user.github_id: methods += 1
    
    if methods <= 1:
        return jsonify({
            'success': False, 
            'message': 'You cannot unlink your only login method. Set a password or link another account first.'
        }), 400
        
    if provider == 'google':
        user.google_id = None
        if user.oauth_provider == 'google': user.oauth_provider = None
    elif provider == 'github':
        user.github_id = None
        if user.oauth_provider == 'github': user.oauth_provider = None
    else:
        return jsonify({'success': False, 'message': 'Invalid provider'}), 400
        
    db.session.commit()
    return jsonify({'success': True, 'message': f'{provider.capitalize()} account unlinked successfully.'})

@app.route('/api/user/upload-avatar', methods=['POST'])
def upload_avatar():
    """Upload and set profile picture"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(f"user_{user_id}_{file.filename}")
        upload_path = os.path.join(app.root_path, 'static', 'uploads', 'avatars')
        os.makedirs(upload_path, exist_ok=True)
        
        filepath = os.path.join(upload_path, filename)
        file.save(filepath)
        
        user = User.query.get(user_id)
        user.profile_image = f'/static/uploads/avatars/{filename}'
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Avatar updated', 'imageUrl': user.profile_image})
    
    return jsonify({'success': False, 'message': 'Upload failed'}), 500

@app.route('/api/user/delete-account', methods=['POST'])
def delete_account():
    """Delete user account and all associated data"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    
    session.clear()
    return jsonify({'success': True, 'message': 'Account deleted successfully'})

@app.route('/')
def index():
    show_otp = request.args.get('show_otp')
    message = request.args.get('message', 'Verification code sent to your email.')
    return render_template('dashboard.html', show_otp=show_otp, msg=message)

# ============= CAREER DATA =============
CAREER_DATA = {
    'cs': {
        'title': 'Computer Science',
        'subtitle': 'Build the future of technology through code',
        'careers': [
            {
                'title': 'Software Engineer',
                'description': 'Design, develop, and maintain software systems and applications.',
                'salary': '$120,000',
                'growth': '25% (Much faster than average)',
                'skills': ['Python', 'Java', 'Data Structures', 'System Design'],
                'required_skills': ['Python / Java / C++', 'Data Structures & Algorithms', 'System Design', 'Version Control (Git)', 'Cloud Architecture (AWS/Azure)', 'Problem Solving'],
                'ladder': [
                    {'title': 'Trainee Software Engineer', 'desc': 'Learning the ropes, assisting the team, and mastering the fundamentals.', 'icon': 'school'},
                    {'title': 'Junior Software Engineer', 'desc': 'Writing basic code, fixing minor bugs, and learning best practices.', 'icon': 'code'},
                    {'title': 'Software Engineer', 'desc': 'Developing features independently, code reviews, and system design basics.', 'icon': 'developer_mode'},
                    {'title': 'Senior Software Engineer', 'desc': 'Leading the architecture of complex modules and mentoring junior devs.', 'icon': 'architecture'},
                    {'title': 'Lead Software Engineer', 'desc': 'Guiding technical direction, unblocking the team, and ensuring quality.', 'icon': 'groups'},
                    {'title': 'Development Manager', 'desc': 'Managing teams, driving strategy, and optimizing developer productivity.', 'icon': 'psychology'},
                ]
            },
            {
                'title': 'Data Scientist',
                'description': 'Analyze complex data sets to extract valuable insights.',
                'salary': '$135,000',
                'growth': '36% (Much faster than average)',
                'skills': ['Machine Learning', 'Statistics', 'SQL', 'Python'],
                'required_skills': ['Python / R', 'Statistical Analysis', 'Machine Learning Models', 'Data Visualization (Tableau/PowerBI)', 'SQL / Databases', 'Big Data Technologies'],
                'ladder': [
                    {'title': 'Data Analyst', 'desc': 'Querying databases, cleaning data, and generating reports.', 'icon': 'query_stats'},
                    {'title': 'Junior Data Scientist', 'desc': 'Building basic models and performing exploratory data analysis.', 'icon': 'bar_chart'},
                    {'title': 'Data Scientist', 'desc': 'Developing complex machine learning models and predictive analytics.', 'icon': 'insights'},
                    {'title': 'Senior Data Scientist', 'desc': 'Leading data science projects, defining methodologies, and mentoring.', 'icon': 'hub'},
                    {'title': 'Lead Data Scientist', 'desc': 'Driving the data strategy, research, and cross-functional AI integration.', 'icon': 'science'},
                    {'title': 'Chief Data Officer', 'desc': 'Executive leadership over the organization\'s data and analytics strategy.', 'icon': 'account_balance'},
                ]
            },
            {
                'title': 'Cybersecurity Analyst',
                'description': 'Protect networks and systems from cyber threats.',
                'salary': '$112,000',
                'growth': '32% (Much faster than average)',
                'skills': ['Network Security', 'Cryptography', 'Risk Assessment'],
                'required_skills': ['Network Architecture', 'Security Protocols', 'Penetration Testing', 'Incident Response', 'Cryptography', 'SIEM Tools'],
                'ladder': [
                    {'title': 'Security Technician', 'desc': 'Monitoring systems, managing access controls, and responding to basic alerts.', 'icon': 'security'},
                    {'title': 'Junior Security Analyst', 'desc': 'Conducting vulnerability scans and assisting in incident response.', 'icon': 'policy'},
                    {'title': 'Cybersecurity Analyst', 'desc': 'Analyzing threats, implementing security measures, and handling breaches.', 'icon': 'gpp_bad'},
                    {'title': 'Senior Security Analyst', 'desc': 'Designing secure network architectures and leading incident response.', 'icon': 'shield'},
                    {'title': 'Lead Security Architect', 'desc': 'Defining enterprise security strategy and ensuring compliance.', 'icon': 'castle'},
                    {'title': 'Chief Information Security Officer', 'desc': 'Executive responsibility for the organization\'s information and data security.', 'icon': 'admin_panel_settings'},
                ]
            }
        ]
    },
    'healthcare': {
        'title': 'Health Care',
        'subtitle': 'Make a difference in people\'s lives through medicine',
        'careers': [
            {
                'title': 'Registered Nurse',
                'description': 'Provide and coordinate patient care in hospitals and clinics.',
                'salary': '$77,000',
                'growth': '6% (Faster than average)',
                'skills': ['Patient Care', 'Clinical Skills', 'Communication'],
                'required_skills': ['Patient Assessment', 'Medication Administration', 'Medical Terminology', 'Empathy & Care', 'Emergency Response', 'Electronic Health Records'],
                'ladder': [
                    {'title': 'Nursing Assistant/Student RN', 'desc': 'Assisting with basic patient care, taking vitals, and learning clinical workflows.', 'icon': 'favorite'},
                    {'title': 'Staff Registered Nurse', 'desc': 'Providing direct patient care, administering medications, and updating records.', 'icon': 'healing'},
                    {'title': 'Charge Nurse', 'desc': 'Overseeing a shift of nurses, coordinating schedules, and managing crises.', 'icon': 'health_and_safety'},
                    {'title': 'Nurse Manager', 'desc': 'Managing a department, handling budgets, and ensuring quality of care.', 'icon': 'medical_services'},
                    {'title': 'Director of Nursing', 'desc': 'Leading nursing operations across the facility and setting clinical standards.', 'icon': 'local_hospital'},
                    {'title': 'Chief Nursing Officer (CNO)', 'desc': 'Executive leadership of nursing practice and patient care operations.', 'icon': 'workspace_premium'},
                ]
            },
            {
                'title': 'Physician Assistant',
                'description': 'Practice medicine on teams with physicians and other healthcare workers.',
                'salary': '$126,000',
                'growth': '27% (Much faster than average)',
                'skills': ['Diagnosis', 'Treatment', 'Medical History', 'Teamwork'],
                'required_skills': ['Medical Diagnosis', 'Treatment Planning', 'Surgical Assisting', 'Pharmacology', 'Patient Counseling', 'Anatomy/Physiology'],
                'ladder': [
                    {'title': 'PA Student/Pre-PA', 'desc': 'Completing clinical rotations, shadowing, and foundational medical coursework.', 'icon': 'school'},
                    {'title': 'Junior Staff PA', 'desc': 'Assisting physicians, taking histories, and performing routine check-ups.', 'icon': 'stethoscope'},
                    {'title': 'Physician Assistant', 'desc': 'Diagnosing illnesses, developing treatment plans, and prescribing medications independently.', 'icon': 'vaccines'},
                    {'title': 'Senior PA / Specialized PA', 'desc': 'Working in specialized surgical or critical care fields with high autonomy.', 'icon': 'medication'},
                    {'title': 'Lead PA / Chief PA', 'desc': 'Managing teams of PAs, overseeing schedules, and contributing to hospital policy.', 'icon': 'badge'},
                    {'title': 'Clinical Director', 'desc': 'Executive leadership of clinical operations and interdisciplinary medical teams.', 'icon': 'event_available'},
                ]
            },
            {
                'title': 'Physical Therapist',
                'description': 'Help injured or ill people improve their movement and manage pain.',
                'salary': '$97,000',
                'growth': '15% (Much faster than average)',
                'skills': ['Rehabilitation', 'Anatomy', 'Treatment Planning'],
                'required_skills': ['Biomechanics', 'Exercise Therapy', 'Manual Therapy Techniques', 'Patient Assessment', 'Pain Management', 'Documentation'],
                'ladder': [
                    {'title': 'PT Student / Aide', 'desc': 'Assisting in setting up equipment and observing therapeutic sessions.', 'icon': 'fitness_center'},
                    {'title': 'Staff Physical Therapist', 'desc': 'Evaluating patients and implementing basic rehabilitation plans.', 'icon': 'elderly'},
                    {'title': 'Senior Physical Therapist', 'desc': 'Handling complex cases, mentoring staff, and specializing (e.g., ortho, neuro).', 'icon': 'assist_walker'},
                    {'title': 'Clinical Coordinator', 'desc': 'Managing clinic schedules, supervising PT assistants, and ensuring protocol adherence.', 'icon': 'calendar_today'},
                    {'title': 'Clinic Director', 'desc': 'Running the business and clinical operations of a therapy center.', 'icon': 'storefront'},
                    {'title': 'Rehab Services Director', 'desc': 'Overseeing physical, occupational, and speech therapy programs at an organizational level.', 'icon': 'corporate_fare'},
                ]
            }
        ]
    },
    'habitation': {
        'title': 'Habitation',
        'subtitle': 'Design, build, and maintain our living spaces',
        'careers': [
            {
                'title': 'Architect',
                'description': 'Plan and design houses, factories, office buildings, and other structures.',
                'salary': '$93,000',
                'growth': '3% (As fast as average)',
                'skills': ['Design', 'CAD', 'Creativity', 'Technical Knowledge'],
                'required_skills': ['AutoCAD/Revit', '3D Modeling', 'Building Codes', 'Structural Design', 'Client Communication', 'Project Management'],
                'ladder': [
                    {'title': 'Architectural Intern', 'desc': 'Drafting basic plans, building models, and assisting with project documentation.', 'icon': 'straighten'},
                    {'title': 'Junior Architect', 'desc': 'Developing designs, preparing presentations, and coordinating with engineers.', 'icon': 'edit'},
                    {'title': 'Project Architect', 'desc': 'Leading the design, ensuring code compliance, and managing the drafting team.', 'icon': 'architecture'},
                    {'title': 'Senior Architect', 'desc': 'Managing large-scale projects, client relations, and complex architectural challenges.', 'icon': 'location_city'},
                    {'title': 'Design Director', 'desc': 'Leading the creative vision for the firm and winning new business.', 'icon': 'palette'},
                    {'title': 'Principal/Partner', 'desc': 'Executive leadership, owning the business strategy, and leading the firm.', 'icon': 'real_estate_agent'},
                ]
            },
            {
                'title': 'Civil Engineer',
                'description': 'Design, build, and supervise infrastructure projects and systems.',
                'salary': '$89,000',
                'growth': '5% (As fast as average)',
                'skills': ['Engineering Principles', 'Project Management', 'Problem Solving'],
                'required_skills': ['AutoCAD Civil 3D', 'Structural Analysis', 'Geotechnical Knowledge', 'Math/Physics', 'Construction Management', 'Environmental Regulations'],
                'ladder': [
                    {'title': 'Engineering Technician', 'desc': 'Conducting surveys, taking soil samples, and assisting in drawing preparations.', 'icon': 'terrain'},
                    {'title': 'Junior Civil Engineer (EIT)', 'desc': 'Assisting in design calculations, cost estimates, and site inspections.', 'icon': 'engineering'},
                    {'title': 'Civil Engineer (PE)', 'desc': 'Designing infrastructure, signing off on plans, and managing subcontractors.', 'icon': 'construction'},
                    {'title': 'Senior Civil Engineer', 'desc': 'Leading massive public works projects, from bridges to highway systems.', 'icon': 'emoji_transportation'},
                    {'title': 'Engineering Manager', 'desc': 'Overseeing multiple engineering teams, budgets, and municipal contracts.', 'icon': 'domain'},
                    {'title': 'Chief Engineer / Director', 'desc': 'Executive responsibility for regional or departmental engineering operations.', 'icon': 'account_balance'},
                ]
            },
            {
                'title': 'Urban Planner',
                'description': 'Develop land use plans and programs that help create communities.',
                'salary': '$79,000',
                'growth': '4% (As fast as average)',
                'skills': ['Analysis', 'Communication', 'GIS', 'Planning Law'],
                'required_skills': ['GIS Mapping', 'Urban Policy', 'Zoning Laws', 'Public Speaking', 'Environmental Science', 'Statistical Analysis'],
                'ladder': [
                    {'title': 'Planning Assistant', 'desc': 'Gathering data, preparing public notices, and mapping zoning areas.', 'icon': 'map'},
                    {'title': 'Junior Planner', 'desc': 'Reviewing site plans, conducting community surveys, and writing reports.', 'icon': 'description'},
                    {'title': 'Urban Planner', 'desc': 'Developing community plans, presenting to city councils, and managing grant projects.', 'icon': 'nature_people'},
                    {'title': 'Senior Planner', 'desc': 'Leading major city redevelopment projects and revising comprehensive city plans.', 'icon': 'location_on'},
                    {'title': 'Principal Planner', 'desc': 'Advising mayors and councils, handling high-profile policy implementations.', 'icon': 'public'},
                    {'title': 'Director of City Planning', 'desc': 'Executive oversight of a city\'s entire planning, zoning, and development department.', 'icon': 'account_balance'},
                ]
            }
        ]
    },
    'polsci': {
        'title': 'Political Science',
        'subtitle': 'Understand and influence public policy and government',
        'careers': [
            {
                'title': 'Policy Analyst',
                'description': 'Analyze policies and their effects on society and the economy.',
                'salary': '$65,000',
                'growth': '6% (Faster than average)',
                'skills': ['Research', 'Analysis', 'Writing', 'Public Policy'],
                'required_skills': ['Statistical Analysis', 'Policy Evaluation', 'Research Writing', 'Economics Background', 'Public Speaking', 'Data Modeling'],
                'ladder': [
                    {'title': 'Research Assistant', 'desc': 'Collecting data, reviewing literature, and preparing policy summaries.', 'icon': 'search'},
                    {'title': 'Junior Policy Analyst', 'desc': 'Drafting policy briefs, monitoring legislation, and assisting in evaluations.', 'icon': 'article'},
                    {'title': 'Policy Analyst', 'desc': 'Evaluating policy impacts, testifying in hearings, and publishing reports.', 'icon': 'assessment'},
                    {'title': 'Senior Policy Analyst', 'desc': 'Leading major research initiatives and advising lawmakers directly.', 'icon': 'psychology'},
                    {'title': 'Director of Policy', 'desc': 'Managing a team of analysts and setting the research agenda for a think tank or agency.', 'icon': 'groups'},
                    {'title': 'Chief Policy Officer', 'desc': 'Executive leadership shaping the organization\'s public policy strategy.', 'icon': 'gavel'},
                ]
            },
            {
                'title': 'Legislative Assistant',
                'description': 'Support legislators in drafting and analyzing legislation.',
                'salary': '$58,000',
                'growth': '5% (As fast as average)',
                'skills': ['Research', 'Communication', 'Legislative Process'],
                'required_skills': ['Constituent Relations', 'Legal Research', 'Speech Writing', 'Negotiation', 'Event Coordination', 'Government Structure Knowledge'],
                'ladder': [
                    {'title': 'Legislative Intern', 'desc': 'Answering phones, sorting mail, and assisting constituents with basic issues.', 'icon': 'mail'},
                    {'title': 'Staff Assistant', 'desc': 'Managing schedules, drafting standard correspondence, and coordinating office logistics.', 'icon': 'calendar_month'},
                    {'title': 'Legislative Assistant', 'desc': 'Briefing the representative, drafting legislation, and tracking specific issue areas.', 'icon': 'gavel'},
                    {'title': 'Senior Legislative Assistant', 'desc': 'Handling complex committees, negotiating with other offices, and leading projects.', 'icon': 'handshake'},
                    {'title': 'Legislative Director', 'desc': 'Overseeing the entire legislative agenda and managing the legislative staff.', 'icon': 'account_tree'},
                    {'title': 'Chief of Staff', 'desc': 'Running the elected official\'s operations, political strategy, and office management.', 'icon': 'stars'},
                ]
            },
            {
                'title': 'Public Relations Specialist',
                'description': 'Create and maintain a positive public image for organizations.',
                'salary': '$67,000',
                'growth': '6% (Faster than average)',
                'skills': ['Communication', 'Media Relations', 'Writing'],
                'required_skills': ['Copywriting', 'Crisis Management', 'Social Media Strategy', 'Press Release Creation', 'Media Pitching', 'Public Speaking'],
                'ladder': [
                    {'title': 'PR Coordinator', 'desc': 'Building media lists, tracking press coverage, and drafting social media posts.', 'icon': 'list_alt'},
                    {'title': 'Junior PR Specialist', 'desc': 'Drafting press releases, pitching to local media, and organizing events.', 'icon': 'campaign'},
                    {'title': 'Public Relations Specialist', 'desc': 'Managing media relationships, developing campaign strategies, and acting as a spokesperson.', 'icon': 'record_voice_over'},
                    {'title': 'PR Manager', 'desc': 'Overseeing complete PR campaigns, crisis communication, and brand messaging.', 'icon': 'manage_accounts'},
                    {'title': 'Director of Public Relations', 'desc': 'Leading the PR department, setting long-term communication strategies.', 'icon': 'lan'},
                    {'title': 'Chief Comm Officer', 'desc': 'Executive leadership over all internal and external corporate communications.', 'icon': 'supervisor_account'},
                ]
            }
        ]
    }
}


@app.route('/careers')
def careers():
    """Careers page"""
    category = request.args.get('cat', 'all')
    
    if category == 'all':
        # Flatten all careers for 'all' view or just show a selection
        data = {
            'title': 'Explore Careers',
            'subtitle': 'Discover detailed career paths, salary insights, and required skills.',
            'careers': []
        }
        # Add a few examples from each category
        for cat in CAREER_DATA:
            data['careers'].extend(CAREER_DATA[cat]['careers'][:1])
    else:
        data = CAREER_DATA.get(category, CAREER_DATA['cs'])
        
    return render_template('careers.html', data=data, current_cat=category)

@app.route('/careers/<category>')
def specific_career(category):
    """Specific career category page"""
    if category in CAREER_DATA:
        return render_template('careers.html', data=CAREER_DATA[category], current_cat=category)
    return redirect(url_for('careers'))

@app.route('/organizations')
def organizations():
    """Organizations page"""
    return render_template('organizations.html')

@app.route('/community')
def community():
    """Community page"""
    category = request.args.get('category')
    tag = request.args.get('tag')
    post_id = request.args.get('post_id')
    
    query = Post.query
    if post_id:
        query = query.filter_by(id=post_id)
    if category:
        query = query.filter_by(category=category)
    if tag:
        query = query.filter(Post.tags.contains(tag))
        
    posts = query.order_by(Post.created_at.desc()).all()
    current_user_id = session.get('user_id')
    posts_data = [p.to_dict(current_user_id=current_user_id) for p in posts]
    
    return render_template('community.html', posts=posts_data, current_category=category, current_tag=tag)

@app.route('/api/posts', methods=['POST'])
def create_post():
    """Create a new community post"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to post'}), 401
        
    data = request.get_json()
    content = data.get('content')
    category = data.get('category', 'Home Feed')
    
    if not content:
        return jsonify({'success': False, 'message': 'Content cannot be empty'}), 400
        
    # Extract tags (words starting with #)
    import re
    tags_list = re.findall(r'#\w+', content)
    tags_str = ','.join(tags_list) if tags_list else None
    
    new_post = Post(
        user_id=user_id,
        content=content,
        category=category,
        tags=tags_str
    )
    
    db.session.add(new_post)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Post created successfully',
        'post': new_post.to_dict(current_user_id=user_id)
    }), 201

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """Toggle a like for a post"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to like a post'}), 401
        
    post = Post.query.get_or_404(post_id)
    existing_like = PostLike.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        post.likes = max(0, post.likes - 1)
        action = 'unliked'
    else:
        new_like = PostLike(user_id=user_id, post_id=post_id)
        db.session.add(new_like)
        post.likes += 1
        action = 'liked'
        
    db.session.commit()
    return jsonify({'success': True, 'action': action, 'likes': post.likes})

@app.route('/api/posts/<int:post_id>/save', methods=['POST'])
def toggle_save(post_id):
    """Toggle saving a post"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to save a post'}), 401
        
    post = Post.query.get_or_404(post_id)
    existing_save = SavedPost.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if existing_save:
        db.session.delete(existing_save)
        action = 'unsaved'
    else:
        new_save = SavedPost(user_id=user_id, post_id=post_id)
        db.session.add(new_save)
        action = 'saved'
        
    db.session.commit()
    return jsonify({'success': True, 'action': action})

@app.route('/api/posts/<int:post_id>/comments', methods=['GET', 'POST'])
def handle_comments(post_id):
    """Fetch or create comments for a post"""
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'GET':
        comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
        return jsonify({
            'success': True,
            'comments': [c.to_dict() for c in comments]
        })
        
    # POST handling
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to comment'}), 401
        
    data = request.get_json()
    content = data.get('content')
    if not content:
        return jsonify({'success': False, 'message': 'Comment cannot be empty'}), 400
        
    new_comment = Comment(user_id=user_id, post_id=post_id, content=content)
    db.session.add(new_comment)
    post.comments_count += 1
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Comment added successfully',
        'comment': new_comment.to_dict(),
        'comments_count': post.comments_count
    }), 201

@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@app.route('/about')
def about():
    """About Us page"""
    return render_template('About_US.html')

# ============= INITIALIZATION =============
def init_db():
    with app.app_context():
        db.create_all()
        
        # Apply remote schema migrations for existing tables
        columns_to_add = [
            'google_id VARCHAR(200)',
            'github_id VARCHAR(200)',
            'email_notifications BOOLEAN DEFAULT TRUE',
            'push_notifications BOOLEAN DEFAULT TRUE',
            'two_factor_enabled BOOLEAN DEFAULT FALSE',
            'is_public BOOLEAN DEFAULT TRUE',
            'profile_image VARCHAR(255)'
        ]
        
        for col_def in columns_to_add:
            try:
                db.session.execute(db.text(f'ALTER TABLE "user" ADD COLUMN {col_def}'))
                db.session.commit()
            except Exception:
                db.session.rollback()
                
        # Attempt to add UNIQUE constraints on OAuth IDs
        try:
            db.session.execute(db.text('ALTER TABLE "user" ADD CONSTRAINT "user_google_id_key" UNIQUE (google_id)'))
            db.session.commit()
        except Exception:
            db.session.rollback()
            
        try:
            db.session.execute(db.text('ALTER TABLE "user" ADD CONSTRAINT "user_github_id_key" UNIQUE (github_id)'))
            db.session.commit()
        except Exception:
            db.session.rollback()
        
        # Seed some posts if none exist
        try:
            if Post.query.count() == 0:
                user = User.query.filter_by(email="demo@skillverify.com").first()
                if not user:
                    user = User(email="demo@skillverify.com", name="System User")
                    db.session.add(user)
                    db.session.commit()
                    
                demo_posts = [
                    Post(user_id=user.id, content="Just completed the Advanced React Challenge! 🎉 After weeks of struggling with state management, I finally understand the Context API and custom hooks. The real-world project really helped solidify my understanding. Anyone else working on this challenge?", category="Tech & Coding", tags="#React,#JavaScript,#Frontend", likes=234, comments_count=45, created_at=datetime.utcnow() - timedelta(hours=2)),
                    Post(user_id=user.id, content="Looking for feedback on my portfolio redesign! I've been working on implementing dark mode and improving accessibility. What are some must-have features for a designer portfolio in 2026? 🎨", category="Design", tags="#UXDesign,#Portfolio,#Feedback", likes=189, comments_count=67, created_at=datetime.utcnow() - timedelta(hours=5)),
                    Post(user_id=user.id, content="🚀 Career Tip: Don't just list skills on your resume - prove them! I helped 15 candidates get hired last month by showcasing their SkillVerify verified badges. Employers love seeing concrete proof of abilities. What's your experience with skills-based hiring?", category="Career Advice", tags="#CareerAdvice,#JobSearch,#SkillVerified", likes=456, comments_count=89, created_at=datetime.utcnow() - timedelta(days=1)),
                    Post(user_id=user.id, content="Just finished building my first machine learning model that predicts customer churn with 94% accuracy! 📈 The journey from zero ML knowledge to deploying a production model took 6 months. Thanks to everyone in this community who answered my questions along the way!", category="Data Science", tags="#MachineLearning,#DataScience,#Python", likes=567, comments_count=92, created_at=datetime.utcnow() - timedelta(days=2))
                ]
                db.session.bulk_save_objects(demo_posts)
                db.session.commit()
                print("✅ Database seeded with demo posts!")
        except Exception as e:
            print(f"Error seeding database: {e}")
            
        print("✅ Database initialized!")

# ============= ERROR HANDLERS =============
try:
    from oauthlib.oauth2.rfc6749.errors import OAuth2Error
    @app.errorhandler(OAuth2Error)
    def handle_oauth_error(e):
        print(f"OAuth Error: {e}")
        return redirect(url_for('index', show_otp='', message='OAuth login failed or timed out. Please try again.'))
except ImportError:
    pass

# Ensure the database tables are created in production
# On Vercel (serverless), we only run this if requested or once per cold start
# We wrap it in a try-except to prevent the whole app from crashing if DB is unreachable
if os.environ.get('VERCEL'):
    try:
        # Avoid running heavy migrations on every cold start if possible
        # For now, just create tables
        with app.app_context():
            db.create_all()
    except Exception as e:
        print(f"Lazy DB init failed: {e}")
else:
    init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)