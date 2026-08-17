import random
import socket
import unicodedata
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required
from app.extensions import db, limiter
from app.utils import admin_required, log_action, get_local_ip
from models import User, AccountRequest, PasswordResetRequest, get_vietnam_time

account_request_bp = Blueprint('account_request', __name__)

# ================= HÀM BỎ DẤU TIẾNG VIỆT =================
def remove_vietnamese_diacritics(text):
    """Bỏ dấu tiếng Việt: Nguyễn → Nguyen, Vĩ → Vi, Đ → D"""
    text = text.replace('Đ', 'D').replace('đ', 'd')
    normalized = unicodedata.normalize('NFD', text)
    result = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return result

def generate_username(full_name):
    """Sinh username từ họ tên tiếng Việt"""
    parts = full_name.strip().split()
    if not parts:
        return 'user'
    
    if len(parts) == 1:
        base = remove_vietnamese_diacritics(parts[0]).lower()
    else:
        first_name = remove_vietnamese_diacritics(parts[-1]).lower()
        initials = ''.join(
            remove_vietnamese_diacritics(p)[0].lower() for p in parts[:-1] if p
        )
        base = first_name + initials
    
    username = base
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base}{counter}"
        counter += 1
    
    return username

def generate_password():
    """Sinh mật khẩu ngẫu nhiên 6 chữ số"""
    return str(random.randint(100000, 999999))


# ================= TRANG PUBLIC: GỬI YÊU CẦU =================
@account_request_bp.route('/request-account', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def request_account():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        factory_name = request.form.get('factory_name', '').strip()
        position = request.form.get('position', '').strip()

        if not all([full_name, email, factory_name, position]):
            flash('Vui lòng điền đầy đủ tất cả thông tin!', 'warning')
            return redirect(url_for('account_request.request_account'))

        existing = AccountRequest.query.filter_by(email=email, status='pending').first()
        if existing:
            flash('Email này đã có yêu cầu đang chờ duyệt. Vui lòng chờ phản hồi từ quản trị viên.', 'warning')
            return redirect(url_for('account_request.request_account'))

        new_request = AccountRequest(
            full_name=full_name,
            email=email,
            factory_name=factory_name,
            position=position
        )
        db.session.add(new_request)
        db.session.commit()

        flash('Yêu cầu tạo tài khoản đã được gửi thành công! Vui lòng chờ quản trị viên phê duyệt.', 'success')
        return redirect(url_for('account_request.request_account'))

    return render_template('request_account.html')


@account_request_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()

        if not all([username, email]):
            flash('Vui lòng điền đầy đủ thông tin!', 'warning')
            return redirect(url_for('account_request.forgot_password'))

        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Tài khoản không tồn tại trong hệ thống!', 'danger')
            return redirect(url_for('account_request.forgot_password'))

        existing = PasswordResetRequest.query.filter_by(username=username, status='pending').first()
        if existing:
            flash('Tài khoản này đã có yêu cầu đang chờ duyệt. Vui lòng chờ phản hồi.', 'warning')
            return redirect(url_for('account_request.forgot_password'))

        new_request = PasswordResetRequest(
            username=username,
            email=email
        )
        db.session.add(new_request)
        db.session.commit()

        flash('Yêu cầu đặt lại mật khẩu đã được gửi! Vui lòng chờ quản trị viên phê duyệt.', 'success')
        return redirect(url_for('account_request.forgot_password'))

    return render_template('forgot_password.html')


# ================= TRANG ADMIN: QUẢN LÝ TẤT CẢ YÊU CẦU =================
@account_request_bp.route('/admin/requests')
@login_required
@admin_required
def manage_all_requests():
    acc_requests = AccountRequest.query.order_by(
        db.case(
            (AccountRequest.status == 'pending', 0),
            (AccountRequest.status == 'approved', 1),
            (AccountRequest.status == 'rejected', 2),
        ),
        AccountRequest.created_at.desc()
    ).all()
    
    pwd_requests = PasswordResetRequest.query.order_by(
        db.case(
            (PasswordResetRequest.status == 'pending', 0),
            (PasswordResetRequest.status == 'approved', 1),
            (PasswordResetRequest.status == 'rejected', 2),
        ),
        PasswordResetRequest.created_at.desc()
    ).all()
    
    server_url = f'http://{get_local_ip()}:8080'
    return render_template('requests.html', account_requests=acc_requests, password_requests=pwd_requests, server_url=server_url)


@account_request_bp.route('/admin/account-requests/approve/<int:req_id>', methods=['POST'])
@login_required
@admin_required
def approve_request(req_id):
    acc_request = AccountRequest.query.get_or_404(req_id)

    if acc_request.status != 'pending':
        return jsonify({'error': 'Yêu cầu này đã được xử lý trước đó.'}), 400

    username = generate_username(acc_request.full_name)
    password = generate_password()

    new_user = User(username=username, role='viewer')
    new_user.set_password(password)
    db.session.add(new_user)

    acc_request.status = 'approved'
    acc_request.generated_username = username
    acc_request.reviewed_at = get_vietnam_time()

    log_action('DUYỆT', 'Yêu cầu TK', f'Duyệt yêu cầu của "{acc_request.full_name}" ({acc_request.email}) — Tạo TK: {username}')
    db.session.commit()

    return jsonify({
        'success': True,
        'full_name': acc_request.full_name,
        'email': acc_request.email,
        'factory_name': acc_request.factory_name,
        'position': acc_request.position,
        'username': username,
        'password': password
    })


@account_request_bp.route('/admin/account-requests/reject/<int:req_id>', methods=['POST'])
@login_required
@admin_required
def reject_request(req_id):
    acc_request = AccountRequest.query.get_or_404(req_id)

    if acc_request.status != 'pending':
        flash('Yêu cầu này đã được xử lý trước đó.', 'warning')
        return redirect(url_for('account_request.manage_all_requests'))

    acc_request.status = 'rejected'
    acc_request.reviewed_at = get_vietnam_time()
    
    log_action('TỪ CHỐI', 'Yêu cầu TK', f'Từ chối yêu cầu tạo TK của "{acc_request.full_name}" ({acc_request.email})')
    db.session.commit()

    flash(f'Đã từ chối yêu cầu của "{acc_request.full_name}".', 'info')
    return redirect(url_for('account_request.manage_all_requests'))





@account_request_bp.route('/admin/password-requests/approve/<int:req_id>', methods=['POST'])
@login_required
@admin_required
def approve_password_request(req_id):
    pwd_request = PasswordResetRequest.query.get_or_404(req_id)

    if pwd_request.status != 'pending':
        return jsonify({'error': 'Yêu cầu này đã được xử lý trước đó.'}), 400

    user = User.query.filter_by(username=pwd_request.username).first()
    if not user:
        return jsonify({'error': 'Không tìm thấy tài khoản này trong hệ thống.'}), 404

    new_password = generate_password()
    user.set_password(new_password)

    pwd_request.status = 'approved'
    pwd_request.reviewed_at = get_vietnam_time()

    log_action('DUYỆT', 'Yêu cầu Đặt lại MK', f'Duyệt yêu cầu của TK "{pwd_request.username}" ({pwd_request.email})')
    db.session.commit()

    return jsonify({
        'success': True,
        'username': pwd_request.username,
        'email': pwd_request.email,
        'password': new_password
    })


@account_request_bp.route('/admin/password-requests/reject/<int:req_id>', methods=['POST'])
@login_required
@admin_required
def reject_password_request(req_id):
    pwd_request = PasswordResetRequest.query.get_or_404(req_id)

    if pwd_request.status != 'pending':
        flash('Yêu cầu này đã được xử lý trước đó.', 'warning')
        return redirect(url_for('account_request.manage_all_requests'))

    pwd_request.status = 'rejected'
    pwd_request.reviewed_at = datetime.now()
    
    log_action('TỪ CHỐI', 'Yêu cầu Đặt lại MK', f'Từ chối yêu cầu của TK "{pwd_request.username}" ({pwd_request.email})')
    db.session.commit()

    flash(f'Đã từ chối yêu cầu của "{pwd_request.username}".', 'info')
    return redirect(url_for('account_request.manage_all_requests'))
