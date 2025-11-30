from flask import Flask
from flask_login import LoginManager
from models import db, User
import os
import warnings

# Suppress warnings (they're harmless)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///nitiarthik.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Configure session security
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.upload import upload_bp
from routes.transactions import transactions_bp
from routes.accounts import accounts_bp
from routes.statements import statements_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(statements_bp)

@app.route('/')
def index():
    from flask import redirect, url_for
    from flask_login import current_user
    try:
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    except Exception as e:
        # If there's an error, just redirect to login
        return redirect(url_for('auth.login'))

@app.route('/health')
def health():
    """Health check endpoint - no authentication required"""
    return {'status': 'ok', 'message': 'Server is running'}, 200

if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
        print("\n" + "=" * 60)
        print(" " * 15 + "NitiArthik - Personal Finance Portal")
        print("=" * 60)
        print("\n✓ Database initialized")
        print("✓ Server starting...")
        print("\n" + "-" * 60)
        print("  Access the application at: http://127.0.0.1:5000")
        print("  Press CTRL+C to stop the server")
        print("-" * 60 + "\n")
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()




