"""Smart Patrol System (智能巡更系统) - Flask Application Entry Point."""

import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager

from config import Config
from models import db, User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure instance and upload directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.instance_path), exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问该页面'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.records import records_bp
    from routes.exceptions import exceptions_bp
    from routes.reports import reports_bp
    from routes.cameras import cameras_bp
    from routes.users import users_bp
    from routes.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(exceptions_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(cameras_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(profile_bp)

    # Create tables on first run
    with app.app_context():
        db.create_all()
        # Auto-seed if no users exist
        if User.query.count() == 0:
            print("[INFO] No users found -- running seed...")
            from seed import seed
            seed()

    return app


if __name__ == '__main__':
    app = create_app()
    print("\n" + "=" * 60)
    print("  智能巡更系统 Smart Patrol System V1.0")
    print("  http://127.0.0.1:5000")
    print("=" * 60)
    print("  演示账号:")
    print("    系统管理员: admin / admin123")
    print("    物业主管:   supervisor / sup123")
    print("    巡更人员1:  patrol1 / patrol123")
    print("    巡更人员2:  patrol2 / patrol123")
    print("    巡更人员3:  patrol3 / patrol123")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
