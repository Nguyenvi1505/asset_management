from datetime import datetime, timezone, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

def get_vietnam_time():
    """Luôn trả về thời gian hiện tại theo UTC+7 (Giờ VN), bất kể múi giờ của máy chủ"""
    return (datetime.now(timezone.utc) + timedelta(hours=7)).replace(tzinfo=None)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ================= CẤU TRÚC XƯỞNG & MÁY =================
class Factory(db.Model):
    __tablename__ = 'factories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    deleted_at = db.Column(db.DateTime, nullable=True) # Lưu thời gian xóa mềm
    trash_path = db.Column(db.String(255), nullable=True) # Lưu đường dẫn folder rác
   
    # Mối quan hệ 1-N: 1 Xưởng có nhiều Máy
    machines = db.relationship('Machine', backref='factory', lazy=True, cascade="all, delete-orphan")

class Machine(db.Model):
    __tablename__ = 'machines'
    id = db.Column(db.Integer, primary_key=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('factories.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    devices = db.relationship('Device', backref='machine', lazy=True, cascade="all, delete-orphan")
    deleted_at = db.Column(db.DateTime, nullable=True) # Lưu thời gian xóa mềm
    trash_path = db.Column(db.String(255), nullable=True) # Lưu đường dẫn folder rác

class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)  # PLC, HMI, Lidar, Servo, Inverter...
    allowed_exts = db.Column(db.String(100), nullable=False) # Ví dụ: .cxp, .st, .zap16
    description = db.Column(db.String(255))
    requires_backup = db.Column(db.Boolean, default=False) # Bật/tắt tính năng upload file backup
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    versions = db.relationship('Version', backref='device', lazy=True, cascade="all, delete-orphan")
    deleted_at = db.Column(db.DateTime, nullable=True) # Lưu thời gian xóa mềm
    trash_path = db.Column(db.String(255), nullable=True) # Lưu đường dẫn folder rác

class Version(db.Model):
    __tablename__ = 'versions'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    version_number = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Lưu ID người cập nhật
    changelog = db.Column(db.Text, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True) # Lưu thời gian xóa mềm
    trash_path = db.Column(db.String(255), nullable=True) # Lưu đường dẫn folder rác
   
    # Thông tin file
    file_path = db.Column(db.String(255))
    file_hash = db.Column(db.String(64)) # Mã băm SHA-256
    file_size = db.Column(db.Integer)    # Dung lượng file (Bytes)

    text_file_path = db.Column(db.String(255), nullable=True)
    backup_file_path = db.Column(db.String(255), nullable=True)
   
    created_at = db.Column(db.DateTime, default=get_vietnam_time)

    # Lấy thông tin user (uploader) dễ dàng hơn
    uploader = db.relationship('User', backref='versions')

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
   
    action = db.Column(db.String(50), nullable=False)      # THÊM, SỬA, XÓA, TẢI VỀ
    target_type = db.Column(db.String(50), nullable=False) # Đối tượng bị tác động: Version, Device...
    details = db.Column(db.Text, nullable=False)           # Chi tiết hành động
   
    created_at = db.Column(db.DateTime, default=get_vietnam_time)

    user = db.relationship('User', backref='audit_logs')

class AccountRequest(db.Model):
    """Yêu cầu tạo tài khoản từ người chưa có TK trong hệ thống"""
    __tablename__ = 'account_requests'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)       # Họ và tên đầy đủ
    email = db.Column(db.String(150), nullable=False)            # Email để nhận thông báo TK
    factory_name = db.Column(db.String(100), nullable=False)     # Thuộc xưởng nào
    position = db.Column(db.String(100), nullable=False)         # Chức vụ
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending / approved / rejected
    generated_username = db.Column(db.String(50), nullable=True) # Username đã sinh (sau khi duyệt)
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    reviewed_at = db.Column(db.DateTime, nullable=True)

class PasswordResetRequest(db.Model):
    """Yêu cầu đặt lại mật khẩu khi quên"""
    __tablename__ = 'password_reset_requests'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending / approved / rejected
    created_at = db.Column(db.DateTime, default=get_vietnam_time)
    reviewed_at = db.Column(db.DateTime, nullable=True)
