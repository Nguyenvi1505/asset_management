from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.utils import admin_required, log_action
from models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
       
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Sai tài khoản hoặc mật khẩu!', 'danger')
           
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# ================= USER MANAGEMENT =================
@auth_bp.route('/users')
@login_required
@admin_required
def manage_users():
    # Lấy danh sách tất cả user trừ admin hiện tại (tùy chọn)
    users = User.query.all()
    return render_template('users.html', users=users)

@auth_bp.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role') # editor hoặc viewer
   
    if not username or not password or not role:
        flash('Vui lòng điền đầy đủ thông tin!', 'warning')
        return redirect(url_for('auth.manage_users'))

    if User.query.filter_by(username=username).first():
        flash(f'Tài khoản "{username}" đã tồn tại!', 'danger')
    else:
        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Đã tạo tài khoản "{username}" thành công!', 'success')
       
    return redirect(url_for('auth.manage_users'))

# ================= API SỬA & XÓA TÀI KHOẢN =================
@auth_bp.route('/users/edit/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
   
    # Bảo vệ tài khoản admin gốc
    if user.username == 'admin':
        flash('Không thể sửa thông tin của tài khoản quản trị gốc!', 'danger')
        return redirect(url_for('auth.manage_users'))

    new_username = request.form.get('username')
    new_role = request.form.get('role')
    new_password = request.form.get('password')

    # Kiểm tra và cập nhật username nếu có sự thay đổi
    if new_username and new_username != user.username:
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user:
            flash(f'Tên đăng nhập "{new_username}" đã tồn tại! Vui lòng chọn tên khác.', 'danger')
            return redirect(url_for('auth.manage_users'))
        user.username = new_username

    # Cập nhật phân quyền
    if new_role:
        user.role = new_role
   
    # Chỉ cập nhật mật khẩu nếu người dùng nhập mật khẩu mới
    if new_password and new_password.strip() != '':
        user.set_password(new_password)

    db.session.commit()
    flash(f'Đã cập nhật tài khoản thành công!', 'success')
    return redirect(url_for('auth.manage_users'))

@auth_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
   
    # Bảo vệ tài khoản admin gốc
    if user.username == 'admin':
        flash('Không thể xóa tài khoản quản trị gốc!', 'danger')
        return redirect(url_for('auth.manage_users'))


    db.session.delete(user)
    db.session.commit()
    flash(f'Đã xóa tài khoản "{user.username}" thành công!', 'success')
    return redirect(url_for('auth.manage_users'))
