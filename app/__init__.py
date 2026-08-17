import os
import atexit
from sqlalchemy import event
from dotenv import load_dotenv
from sqlalchemy.engine import Engine
from datetime import datetime, timedelta
from flask_login import current_user, logout_user
from config import DevelopmentConfig, ProductionConfig
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, session, redirect, url_for, flash, request

def create_app(config_class=None):
    """Application Factory: Tạo và cấu hình Flask app instance."""

    load_dotenv()

    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Chọn config dựa trên biến môi trường nếu không được truyền vào
    if config_class is None:
        env_mode = os.environ.get('FLASK_ENV', 'development').lower()
        if env_mode == 'production':
            config_class = ProductionConfig
        else:
            config_class = DevelopmentConfig

    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TRASH_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DATABASE_DIR'], exist_ok=True)

    # ================= KHỞI TẠO EXTENSIONS =================
    from app.extensions import db, csrf, login_manager, limiter, migrate

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    # ================= KÍCH HOẠT WAL CHO SQLITE =================
    # Lệnh này giúp SQLite chạy đa luồng tốt hơn, chống nghẽn Database Locked
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        import sqlite3
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()

    # ================= USER LOADER =================
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ================= ĐĂNG KÝ BLUEPRINTS =================
    from app.routes.auth import auth_bp
    from app.routes.dashboard import main_bp
    from app.routes.factory import factory_bp
    from app.routes.machine import machine_bp
    from app.routes.device import device_bp
    from app.routes.version import version_bp
    from app.routes.admin import admin_bp
    from app.routes.account_request import account_request_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(factory_bp)
    app.register_blueprint(machine_bp)
    app.register_blueprint(device_bp)
    app.register_blueprint(version_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(account_request_bp)

    # ================= INJECT PENDING COUNT CHO SIDEBAR BADGE =================
    @app.context_processor
    def inject_pending_requests_count():
        if current_user.is_authenticated and current_user.role == 'admin':
            from models import AccountRequest, PasswordResetRequest
            count = AccountRequest.query.filter_by(status='pending').count()
            pwd_count = PasswordResetRequest.query.filter_by(status='pending').count()
            return {'pending_requests_count': count, 'pending_password_requests_count': pwd_count}
        return {'pending_requests_count': 0, 'pending_password_requests_count': 0}

    # ================= KHỞI ĐỘNG HỆ THỐNG TUẦN TRA NGẦM =================
    _init_scheduler(app)

    # ================= XỬ LÝ IDLE TIMEOUT 15 PHÚT =================
    @app.before_request
    def handle_idle_timeout():
        # Bỏ qua các route không cần kiểm tra bảo mật (tránh vòng lặp vô hạn)
        if request.endpoint in ['auth.login', 'auth.logout', 'static', 'account_request.request_account']:
            return
        
        if current_user.is_authenticated:
            now = datetime.now()
            last_active = session.get('last_active')
            
            # Nếu đã có mốc thời gian cuối thao tác
            if last_active:
                last_active_dt = datetime.fromtimestamp(last_active)
                # Kiểm tra nếu khoảng cách lớn hơn 15 phút
                if now - last_active_dt > timedelta(minutes=15):
                    logout_user()
                    session.pop('last_active', None)
                    flash('Phiên làm việc đã tự động kết thúc do không có thao tác nào trong 15 phút.', 'warning')
                    return redirect(url_for('auth.login'))
            
            # Cập nhật lại thời gian thao tác cuối là hiện tại
            session['last_active'] = now.timestamp()
            
    # ================= ERROR HANDLERS (XỬ LÝ LỖI TOÀN CỤC) =================
    from sqlalchemy.exc import SQLAlchemyError
    from flask import render_template

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(e):
        db.session.rollback() # Hoàn tác transaction tránh kẹt DB
        app.logger.error(f"Database Error: {e}")
        flash('Đã xảy ra lỗi nghiêm trọng với Cơ sở dữ liệu. Vui lòng thử lại sau.', 'danger')
        # Tùy theo nơi xảy ra lỗi mà có thể redirect về dashboard hoặc home
        return redirect(url_for('main.dashboard'))

    return app


def _init_scheduler(app):
    """Khởi tạo APScheduler với app context — chỉ chạy khi app thực sự khởi động."""
    from app.routes.scheduler_tasks import auto_system_scan, auto_cleanup_logs

    scheduler = BackgroundScheduler(daemon=True)

    # Truyền app instance vào qua lambda để scheduler tasks có context
    # Lựa chọn 1: Dùng để Test (Quét lặp lại mỗi 1 phút)
    # scheduler.add_job(lambda: auto_system_scan(app), 'interval', minutes=1)

    # Lựa chọn 2: Chạy thực tế (Quét tự động vào đúng 02:00 sáng mỗi ngày)
    scheduler.add_job(lambda: auto_system_scan(app), 'cron', hour=2, minute=0)

    scheduler.add_job(lambda: auto_cleanup_logs(app), 'cron', hour=3, minute=0)
    scheduler.start()

    # Tự động tắt scheduler an toàn khi bạn tắt server (Ctrl+C)
    atexit.register(lambda: scheduler.shutdown())


def init_db(app=None):
    """Khởi tạo Database và tạo tài khoản admin mặc định nếu chưa có."""
    from app.extensions import db
    from models import User

    if app is None:
        from flask import current_app
        app = current_app._get_current_object()

    with app.app_context():
        db.create_all()
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin = User(username='admin', role='admin')
            default_pass = os.environ.get('ADMIN_DEFAULT_PASS', 'Admin@Fallback2026')
            admin.set_password(default_pass)
            db.session.add(admin)
            db.session.commit()
            print("Đã tạo tài khoản thành công!")
