import os
import socket
import hashlib
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import redirect, url_for, request, flash
from flask_login import current_user
from app.extensions import db
from models import AuditLog, Factory, Machine, Device

def get_vietnam_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam (UTC+7) chuẩn nhất"""
    return (datetime.now(timezone.utc) + timedelta(hours=7)).replace(tzinfo=None)

def get_local_ip():
    """Lấy địa chỉ IP LAN thực tế của máy chủ"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Decorator kiểm tra quyền Admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Bạn không có quyền truy cập chức năng này!', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator kiểm tra quyền Admin hoặc Editor (Viewer không được phép)
def editor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['admin', 'editor']:
            flash('Tài khoản của bạn (Viewer) không có quyền Thêm/Sửa/Xóa dữ liệu!', 'warning')
            return redirect(request.referrer or url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def calculate_file_hash(filepath):
    """Tính mã băm SHA-256 của file để phục vụ so sánh (Diff) sau này"""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536) # Đọc từng chunk 64KB để không tràn RAM
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_abs_upload_path(relative_path):
    """Lấy đường dẫn tuyệt đối cho file trong thư mục uploads"""
    if not relative_path:
        return None
    from flask import current_app
    return os.path.join(current_app.config['UPLOAD_FOLDER'], relative_path)

def get_abs_trash_path(relative_path):
    """Lấy đường dẫn tuyệt đối cho thư mục trong thùng rác"""
    if not relative_path:
        return None
    from flask import current_app
    return os.path.join(current_app.config['TRASH_FOLDER'], relative_path)

# ================= HÀM HỖ TRỢ GHI LOG =================
def log_action(action, target_type, details):
    """Hàm âm thầm ghi lại lịch sử thao tác của User"""
    new_log = AuditLog(
        user_id=current_user.id,
        action=action,
        target_type=target_type,
        details=details
    )
    db.session.add(new_log)

def update_info_file(level, parent_id=None):
    """
    Hàm cập nhật file mục lục _INFO.txt tại các cấp thư mục tương ứng.
    """
    from flask import current_app
    base_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(base_dir, exist_ok=True)
   
    if level == 'factory':
        # Cập nhật danh sách Xưởng ở thư mục gốc uploads/
        factories = Factory.query.all()
        info_path = os.path.join(base_dir, '_INFO_FACTORIES.txt')
        with open(info_path, 'w', encoding='utf-8') as f:
            f.write("=== DANH SÁCH XƯỞNG SẢN XUẤT ===\n")
            for fac in factories:
                date_str = fac.created_at.strftime('%d/%m/%Y %H:%M:%S')
                f.write(f"ID: {fac.id} | Ten_Xuong: {fac.name} | Ngay_Tao: {date_str}\n")
               
    elif level == 'machine' and parent_id:
        # Cập nhật danh sách Máy trong uploads/factory_{id}/
        machines = Machine.query.filter_by(factory_id=parent_id).all()
        fac_dir = os.path.join(base_dir, f'factory_{parent_id}')
        os.makedirs(fac_dir, exist_ok=True)
        info_path = os.path.join(fac_dir, '_INFO_MACHINES.txt')
        with open(info_path, 'w', encoding='utf-8') as f:
            f.write("=== DANH SÁCH MÁY TRONG XƯỞNG ===\n")
            for mac in machines:
                date_str = mac.created_at.strftime('%d/%m/%Y %H:%M:%S')
                f.write(f"ID: {mac.id} | Ten_May: {mac.name} | Ngay_Tao: {date_str}\n")
               
    elif level == 'device' and parent_id:
        # Cập nhật danh sách Thiết bị trong uploads/factory_{id}/machine_{id}/
        machine = db.get_or_404(Machine, parent_id)
        devices = Device.query.filter_by(machine_id=parent_id).all()
        mac_dir = os.path.join(base_dir, f'factory_{machine.factory_id}', f'machine_{parent_id}')
        os.makedirs(mac_dir, exist_ok=True)
        info_path = os.path.join(mac_dir, '_INFO_DEVICES.txt')
        with open(info_path, 'w', encoding='utf-8') as f:
            f.write("=== DANH SÁCH THIẾT BỊ ĐIỀU KHIỂN ===\n")
            for dev in devices:
                date_str = dev.created_at.strftime('%d/%m/%Y %H:%M:%S')
                f.write(f"ID: {dev.id} | Ten_TB: {dev.name} | Loai: {dev.device_type} | Ngay_Tao: {date_str}\n")
