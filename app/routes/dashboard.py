from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from models import Factory, Machine, Device, Version

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Thêm filter_by(deleted_at=None) vào tất cả các query đếm số lượng
    total_factories = Factory.query.filter_by(deleted_at=None).count()
    total_machines = Machine.query.filter_by(deleted_at=None).count()
    total_devices = Device.query.filter_by(deleted_at=None).count()
    total_versions = Version.query.filter_by(deleted_at=None).count()
   
    # Lấy 5 version gần nhất nhưng loại trừ những version đã bị xóa mềm
    recent_versions = Version.query.filter_by(deleted_at=None).order_by(Version.created_at.desc()).limit(5).all()
   
    return render_template('dashboard.html',
                           total_factories=total_factories,
                           total_machines=total_machines,
                           total_devices=total_devices,
                           total_versions=total_versions,
                           recent_versions=recent_versions)
