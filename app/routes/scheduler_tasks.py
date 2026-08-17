import os
from datetime import datetime, timedelta
from app.extensions import db
from app.utils import calculate_file_hash, get_abs_upload_path
from models import User, Version, AuditLog


def auto_system_scan(app):
    """Tác vụ quét toàn vẹn dữ liệu ngầm — nhận app instance qua tham số"""
    with app.app_context():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ [HỆ THỐNG] Đang tiến hành tuần tra toàn vẹn dữ liệu định kỳ...")
       
        # Chỉ quét các file chưa bị xóa mềm để tránh báo động giả
        all_versions = Version.query.filter_by(deleted_at=None).all()
        missing = []
        tampered = []
       
        for v in all_versions:
            abs_file_path = get_abs_upload_path(v.file_path)
            # 1. Kiểm tra file có bị mất hay không
            if not abs_file_path or not os.path.exists(abs_file_path):
                missing.append(f"V{v.version_number} ({v.device.name})")
                continue
           
            # 2. Kiểm tra mã băm (Hash) xem file có bị sửa trộm không
            if calculate_file_hash(abs_file_path) != v.file_hash:
                tampered.append(f"V{v.version_number} ({v.device.name})")
                continue

        # Nếu phát hiện gian lận/lỗi
        if missing or tampered:
            admin = User.query.filter_by(role='admin').first()
            admin_id = admin.id if admin else 1
           
            error_msg = f"BÁO ĐỘNG ĐỎ! Mất {len(missing)} file, {len(tampered)} file sai Hash."
            detail_msg = error_msg
            if missing:
                detail_msg += f" Bị xóa: {', '.join(missing[:5])}..."
            if tampered:
                detail_msg += f" Sai Hash: {', '.join(tampered[:5])}..."
           
            # Ghi Log Báo động
            new_log = AuditLog(user_id=admin_id, action='BÁO ĐỘNG', target_type='Bảo mật Dữ liệu', details=detail_msg)
            db.session.add(new_log)
            db.session.commit()
           
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {error_msg}")
           
        # NẾU MỌI THỨ AN TOÀN
        else:
            admin = User.query.filter_by(role='admin').first()
            admin_id = admin.id if admin else 1
           
            # Ghi lịch sử đi tuần vào Database
            new_log = AuditLog(
                user_id=admin_id,
                action='QUÉT TỰ ĐỘNG',
                target_type='Toàn vẹn Dữ liệu',
                details='Hoàn tất tuần tra: Hệ thống 100% an toàn, không phát hiện rủi ro.'
            )
            db.session.add(new_log)
            db.session.commit()
           
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ [HỆ THỐNG] Tuần tra hoàn tất. Dữ liệu an toàn 100%.")

def auto_cleanup_logs(app):
    """Tác vụ chạy ngầm tự động dọn dẹp log cũ hơn 365 ngày để giảm tải DB.
    Xóa theo lô nhỏ để tránh khóa bảng audit_logs quá lâu."""
    BATCH_SIZE = 500
    with app.app_context():
        target_date = datetime.now() - timedelta(days=365)
        total_deleted = 0

        while True:
            # Lấy ID của một lô bản ghi cần xóa
            batch_ids = [
                row.id for row in
                AuditLog.query.filter(AuditLog.created_at < target_date)
                .limit(BATCH_SIZE).all()
            ]

            if not batch_ids:
                break

            # Xóa theo lô ID, mỗi lô là 1 transaction riêng → giải phóng lock
            AuditLog.query.filter(AuditLog.id.in_(batch_ids)).delete(synchronize_session=False)
            db.session.commit()
            total_deleted += len(batch_ids)

        if total_deleted > 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧹 [HỆ THỐNG] Đã tự động dọn dẹp {total_deleted} bản ghi nhật ký cũ hơn 1 năm.")
