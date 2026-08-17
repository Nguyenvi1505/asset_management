import os
import csv
import glob
import shutil
import zipfile
import tempfile
from io import StringIO
from datetime import datetime, timedelta
from flask import Blueprint, Response, render_template, redirect, url_for, request, flash, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.utils import admin_required, log_action, get_abs_trash_path, get_abs_upload_path
from models import User, Factory, Machine, Device, Version, AuditLog

admin_bp = Blueprint('admin', __name__)

# ================= TRANG XEM LỊCH SỬ THAO TÁC (CHỈ ADMIN) =================
@admin_bp.route('/audit-logs')
@login_required
def view_audit_logs():
    # Chỉ Admin mới có quyền xem log
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'danger')
        return redirect(url_for('main.dashboard'))

    # Lấy tham số ngày từ URL
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    query = AuditLog.query

    # Lọc theo khoảng thời gian
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date_str:
            # Lấy đến mốc cuối cùng của ngày được chọn
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(AuditLog.created_at <= end_date)
    except ValueError:
        flash('Định dạng ngày không hợp lệ!', 'warning')

    # Lấy 500 log gần nhất theo điều kiện lọc
    logs = query.order_by(AuditLog.created_at.desc()).limit(500).all()

    return render_template(
        'audit_logs.html', 
        logs=logs, 
        start_date=start_date_str, 
        end_date=end_date_str
    )

# ================= TÍNH NĂNG XUẤT FILE CSV =================
@admin_bp.route('/audit-logs/export')
@login_required
@admin_required
def export_audit_logs():
    # Lấy toàn bộ log (có thể giới hạn nếu DB quá lớn)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).all()
   
    def generate():
        data = StringIO()
        writer = csv.writer(data)
        # Ghi BOM (Byte Order Mark) để mở bằng Excel không bị lỗi font tiếng Việt
        data.write('\ufeff')
        writer.writerow(['ID', 'Thời gian', 'Tài khoản', 'Hành động', 'Đối tượng', 'Chi tiết'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
       
        for log in logs:
            writer.writerow([
                log.id,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username,
                log.action,
                log.target_type,
                log.details
            ])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    filename = f"AuditLogs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response

# ================= TÍNH NĂNG XÓA LOG TỪ CŨ NHẤT =================
@admin_bp.route('/audit-logs/delete', methods=['POST'])
@login_required
@admin_required
def delete_audit_logs():
    delete_type = request.form.get('delete_type')
    query = AuditLog.query

    try:
        if delete_type == 'custom':
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(AuditLog.created_at >= start_date, AuditLog.created_at <= end_date)
            else:
                flash('Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc!', 'warning')
                return redirect(url_for('admin.view_audit_logs'))
        else:
            # Tìm ngày của bản ghi cũ nhất đang tồn tại trong hệ thống
            oldest_log = AuditLog.query.order_by(AuditLog.created_at.asc()).first()
           
            if not oldest_log:
                flash('Không có dữ liệu nhật ký để xóa!', 'info')
                return redirect(url_for('admin.view_audit_logs'))
           
            oldest_date = oldest_log.created_at
           
            # Tính toán mốc thời gian cần cắt bỏ dựa trên ngày cũ nhất
            if delete_type == '1_day':
                target_date = oldest_date + timedelta(days=1)
            elif delete_type == '1_week':
                target_date = oldest_date + timedelta(days=7)
            elif delete_type == '1_month':
                target_date = oldest_date + timedelta(days=30)
            elif delete_type == '3_months':
                target_date = oldest_date + timedelta(days=90)
            elif delete_type == '6_months':
                target_date = oldest_date + timedelta(days=180)
           
            # Khoanh vùng từ ngày cũ nhất đến ngày target_date để xóa
            query = query.filter(AuditLog.created_at >= oldest_date, AuditLog.created_at <= target_date)
       
        # Thực thi xóa và lưu Database
        deleted_count = query.delete()
        db.session.commit()
       
        # Ghi lại dấu vết Admin đã thực hiện xóa log
        log_action('XÓA DỮ LIỆU', 'Audit Log', f'Admin đã dọn dẹp {deleted_count} bản ghi nhật ký (Chế độ xóa cũ nhất: {delete_type})')
        db.session.commit()
       
        flash(f'Đã dọn dẹp thành công {deleted_count} bản ghi nhật ký hệ thống!', 'success')
       
    except Exception as e:
        db.session.rollback()
        flash(f'Có lỗi xảy ra khi xóa: {str(e)}', 'danger')

    return redirect(url_for('admin.view_audit_logs'))

# ================= TRANG QUẢN LÝ THÙNG RÁC =================
@admin_bp.route('/recycle-bin')
@login_required
@admin_required
def recycle_bin():
    deleted_factories = Factory.query.filter(Factory.deleted_at.isnot(None)).all()
    deleted_machines = Machine.query.filter(Machine.deleted_at.isnot(None)).all()
    deleted_devices = Device.query.filter(Device.deleted_at.isnot(None)).all()
    deleted_versions = Version.query.filter(Version.deleted_at.isnot(None)).all()
   
    return render_template('recycle_bin.html',
                           factories=deleted_factories,
                           machines=deleted_machines,
                           devices=deleted_devices,
                           versions=deleted_versions)

@admin_bp.route('/recycle-bin/restore/factory/<int:factory_id>', methods=['POST'])
@login_required
@admin_required
def restore_factory(factory_id):
    factory = db.get_or_404(Factory, factory_id)
   
    # 1. Trả lại trạng thái cho Database
    factory.deleted_at = None
    for machine in factory.machines:
        machine.deleted_at = None
        for device in machine.devices:
            device.deleted_at = None
            for version in device.versions:
                version.deleted_at = None

    # 2. Bốc thư mục từ ổ rác trả về vị trí gốc
    abs_trash_path = get_abs_trash_path(factory.trash_path)
    if abs_trash_path and os.path.exists(abs_trash_path):
        dst_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{factory_id}')
        shutil.move(abs_trash_path, dst_dir)
        factory.trash_path = None

    db.session.commit()
    log_action('KHÔI PHỤC', 'Xưởng', f'Phục hồi Xưởng "{factory.name}" từ Thùng rác.')
    db.session.commit()
    flash(f'Đã khôi phục thành công Xưởng "{factory.name}"!', 'success')
    return redirect(url_for('admin.recycle_bin'))

# --- KHÔI PHỤC & XÓA MÁY ---
@admin_bp.route('/recycle-bin/restore/machine/<int:machine_id>', methods=['POST'])
@login_required
@admin_required
def restore_machine(machine_id):
    machine = db.get_or_404(Machine, machine_id)
    machine.deleted_at = None
    for device in machine.devices:
        device.deleted_at = None
        for version in device.versions:
            version.deleted_at = None

    abs_trash_path = get_abs_trash_path(machine.trash_path)
    if abs_trash_path and os.path.exists(abs_trash_path):
        dst_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{machine.factory_id}', f'machine_{machine_id}')
        # Đảm bảo thư mục cha tồn tại trước khi move
        os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
        shutil.move(abs_trash_path, dst_dir)
        machine.trash_path = None

    db.session.commit()
    log_action('KHÔI PHỤC', 'Máy', f'Phục hồi Máy "{machine.name}".')
    db.session.commit()
    flash(f'Đã khôi phục thành công Máy "{machine.name}"!', 'success')
    return redirect(url_for('admin.recycle_bin'))

@admin_bp.route('/recycle-bin/restore/version/<int:version_id>', methods=['POST'])
@login_required
@admin_required
def restore_version(version_id):
    version = db.get_or_404(Version, version_id)
    version.deleted_at = None
   
    # Bốc các file từ ổ rác trả về đúng đường dẫn cũ
    abs_trash_path = get_abs_trash_path(version.trash_path)
    if abs_trash_path and os.path.exists(abs_trash_path):
        abs_file_path = get_abs_upload_path(version.file_path)
        if abs_file_path:
            src_file = os.path.join(abs_trash_path, os.path.basename(abs_file_path))
            if os.path.exists(src_file):
                os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
                shutil.move(src_file, abs_file_path)
               
        abs_text_file_path = get_abs_upload_path(version.text_file_path)
        if abs_text_file_path:
            src_text = os.path.join(abs_trash_path, os.path.basename(abs_text_file_path))
            if os.path.exists(src_text):
                os.makedirs(os.path.dirname(abs_text_file_path), exist_ok=True)
                shutil.move(src_text, abs_text_file_path)
               
        # Xóa folder rác trống
        shutil.rmtree(abs_trash_path)
        version.trash_path = None

    db.session.commit()
    log_action('KHÔI PHỤC', 'Version', f'Phục hồi Version {version.version_number} của thiết bị {version.device.name}.')
    db.session.commit()
    flash(f'Đã khôi phục thành công Version {version.version_number}!', 'success')
    return redirect(url_for('admin.recycle_bin'))

@admin_bp.route('/recycle-bin/hard-delete/machine/<int:machine_id>', methods=['POST'])
@login_required
@admin_required
def hard_delete_machine(machine_id):
    machine = db.get_or_404(Machine, machine_id)
    abs_trash_path = get_abs_trash_path(machine.trash_path)
    if abs_trash_path and os.path.exists(abs_trash_path):
        shutil.rmtree(abs_trash_path)
    name = machine.name
    db.session.delete(machine)
    db.session.commit()
    log_action('XÓA VĨNH VIỄN', 'Máy', f'Tiêu hủy hoàn toàn Máy "{name}".')
    db.session.commit()
    flash(f'Đã tiêu hủy Máy "{name}"!', 'success')
    return redirect(url_for('admin.recycle_bin'))

# --- KHÔI PHỤC & XÓA THIẾT BỊ ---
@admin_bp.route('/recycle-bin/restore/device/<int:device_id>', methods=['POST'])
@login_required
@admin_required
def restore_device(device_id):
    device = db.get_or_404(Device, device_id)
    device.deleted_at = None
    for version in device.versions:
        version.deleted_at = None

    abs_trash_path = get_abs_trash_path(device.trash_path)
    if abs_trash_path and os.path.exists(abs_trash_path):
        dst_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{device.machine.factory_id}', f'machine_{device.machine_id}', f'device_{device_id}')
        os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
        shutil.move(abs_trash_path, dst_dir)
        device.trash_path = None

    db.session.commit()
    log_action('KHÔI PHỤC', 'Thiết bị', f'Phục hồi Thiết bị "{device.name}".')
    db.session.commit()
    flash(f'Đã khôi phục thành công Thiết bị "{device.name}"!', 'success')
    return redirect(url_for('admin.recycle_bin'))

@admin_bp.route('/recycle-bin/hard-delete/device/<int:device_id>', methods=['POST'])
@login_required
@admin_required
def hard_delete_device(device_id):
    device = db.get_or_404(Device, device_id)
    abs_trash_path = get_abs_trash_path(device.trash_path)
    if abs_trash_path and os.path.exists(abs_trash_path):
        shutil.rmtree(abs_trash_path)
    name = device.name
    db.session.delete(device)
    db.session.commit()
    log_action('XÓA VĨNH VIỄN', 'Thiết bị', f'Tiêu hủy hoàn toàn Thiết bị "{name}".')
    db.session.commit()
    flash(f'Đã tiêu hủy Thiết bị "{name}"!', 'success')
    return redirect(url_for('admin.recycle_bin'))

@admin_bp.route('/recycle-bin/hard-delete/factory/<int:factory_id>', methods=['POST'])
@login_required
@admin_required
def hard_delete_factory(factory_id):
    factory = db.get_or_404(Factory, factory_id)
   
    # 1. Dọn sạch rác vật lý trên ổ cứng (dùng rmtree để xóa nguyên cây thư mục)
    abs_trash_path = get_abs_trash_path(factory.trash_path)
    if abs_trash_path and os.path.exists(abs_trash_path):
        shutil.rmtree(abs_trash_path)
       
    # 2. Xóa cứng khỏi Database
    name = factory.name
    db.session.delete(factory)
    db.session.commit()
   
    log_action('XÓA VĨNH VIỄN', 'Xưởng', f'Tiêu hủy hoàn toàn Xưởng "{name}".')
    db.session.commit()
    flash(f'Đã tiêu hủy vĩnh viễn Xưởng "{name}" và giải phóng bộ nhớ!', 'success')
    return redirect(url_for('admin.recycle_bin'))

@admin_bp.route('/recycle-bin/hard-delete/version/<int:version_id>', methods=['POST'])
@login_required
@admin_required
def hard_delete_version(version_id):
    version = db.get_or_404(Version, version_id)
   
    # Tiêu hủy toàn bộ folder rác chứa file version
    abs_trash_path = get_abs_trash_path(version.trash_path)
    if abs_trash_path and os.path.exists(abs_trash_path):
        shutil.rmtree(abs_trash_path)
       
    v_num = version.version_number
    db.session.delete(version)
    db.session.commit()
   
    log_action('XÓA VĨNH VIỄN', 'Version', f'Tiêu hủy hoàn toàn Version {v_num}.')
    db.session.commit()
    flash(f'Đã tiêu hủy Version {v_num}!', 'success')
    return redirect(url_for('admin.recycle_bin'))

# ================= TÍNH NĂNG SAO LƯU & PHỤC HỒI (BACKUP / MIGRATION) =================
@admin_bp.route('/admin/export-system')
@login_required
@admin_required
def export_system():
    # 1. Tạo một file ZIP tạm thời trong bộ nhớ của hệ điều hành
    temp_dir = tempfile.mkdtemp()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f'AssetSystem_FullBackup_{timestamp}.zip'
    zip_filepath = os.path.join(temp_dir, zip_filename)
    
    # Hàm dọn dẹp chạy nền
    def cleanup_temp():
        import time
        time.sleep(300) # Đợi 5 phút để file kịp tải về
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    import threading
    threading.Thread(target=cleanup_temp).start()

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 1.1 Gom toàn bộ file Database (bao gồm cả .db, .db-wal, .db-shm nếu có)
        db_folder = current_app.config['DATABASE_DIR']
        for db_file in glob.glob(os.path.join(db_folder, 'asset_management.db*')):
            zipf.write(db_file, os.path.join('database', os.path.basename(db_file)))

        # 1.2 Nén toàn bộ thư mục Uploads (File thực tế)
        if os.path.exists(current_app.config['UPLOAD_FOLDER']):
            for root, dirs, files in os.walk(current_app.config['UPLOAD_FOLDER']):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, os.path.dirname(current_app.config['UPLOAD_FOLDER']))
                    zipf.write(abs_path, os.path.join('uploads', rel_path))

        # 1.3 Nén toàn bộ thư mục Thùng rác (Deleted Assets)
        if os.path.exists(current_app.config['TRASH_FOLDER']):
            for root, dirs, files in os.walk(current_app.config['TRASH_FOLDER']):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, os.path.dirname(current_app.config['TRASH_FOLDER']))
                    zipf.write(abs_path, os.path.join('trash', rel_path))

    log_action('XUẤT DỮ LIỆU', 'Hệ thống', 'Admin đã tải xuống bản sao lưu toàn bộ hệ thống.')
    db.session.commit()
    return send_file(zip_filepath, as_attachment=True, download_name=zip_filename)

@admin_bp.route('/admin/import-system', methods=['POST'])
@login_required
@admin_required
def import_system():
    if 'backup_file' not in request.files:
        flash('Không tìm thấy file tải lên!', 'danger')
        return redirect(url_for('main.dashboard'))
       
    file = request.files['backup_file']
    if file.filename == '':
        flash('Chưa chọn file sao lưu!', 'danger')
        return redirect(url_for('main.dashboard'))

    if not file.filename.endswith('.zip'):
        flash('Chỉ chấp nhận định dạng .zip được xuất từ hệ thống!', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        # 1. Lưu file ZIP vào thư mục tạm
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(zip_path)

        # 2. NGẮT KẾT NỐI DATABASE để tránh lỗi "File in use"
        db.session.remove()
        db.engine.dispose()

        # 3. Lấy đường dẫn tuyệt đối của các thư mục gốc để làm ranh giới an toàn (Zip Slip Prevention)
        base_instance = os.path.abspath(current_app.config['DATABASE_DIR'])
        base_uploads = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
        base_trash = os.path.abspath(current_app.config['TRASH_FOLDER'])

        # 4. Giải nén và Ghi đè dữ liệu an toàn
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            for zip_info in zipf.infolist():
                # Bỏ qua nếu entry trong zip là một thư mục (Directory)
                if zip_info.is_dir():
                    continue

                # Bóc tách đường dẫn bên trong ZIP
                parts = zip_info.filename.split('/')
                if not parts:
                    continue
                   
                folder_type = parts[0]
                
                # Phục hồi Database
                if folder_type == 'database' and len(parts) > 1:
                    # Chỉ lấy tên file, loại trừ mọi cấu trúc thư mục lồng nhau
                    safe_fn = secure_filename(parts[-1])
                    target_path = os.path.abspath(os.path.join(base_instance, safe_fn))
                    
                    # Kiểm tra ranh giới
                    if not target_path.startswith(base_instance):
                        print(f"[CẢNH BÁO BẢO MẬT] Phát hiện file độc hại: {zip_info.filename}")
                        continue
                       
                    os.makedirs(base_instance, exist_ok=True)
                    with open(target_path, 'wb') as f_out:
                        f_out.write(zipf.read(zip_info.filename))
                
                # Phục hồi Uploads
                elif folder_type == 'uploads' and len(parts) > 2:
                    rel_path = os.path.join(*parts[1:])
                    target_path = os.path.abspath(os.path.join(base_uploads, rel_path))
                    
                    # Kiểm tra ranh giới
                    if not target_path.startswith(base_uploads):
                        print(f"[CẢNH BÁO BẢO MẬT] Phát hiện file độc hại: {zip_info.filename}")
                        continue
                       
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, 'wb') as f_out:
                        f_out.write(zipf.read(zip_info.filename))
                       
                # Phục hồi Thùng rác
                elif folder_type == 'trash' and len(parts) > 2:
                    rel_path = os.path.join(*parts[1:])
                    target_path = os.path.abspath(os.path.join(base_trash, rel_path))
                    
                    # Kiểm tra ranh giới
                    if not target_path.startswith(base_trash):
                        print(f"[CẢNH BÁO BẢO MẬT] Phát hiện file độc hại: {zip_info.filename}")
                        continue
                       
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, 'wb') as f_out:
                        f_out.write(zipf.read(zip_info.filename))

        # Dọn dẹp file tạm
        shutil.rmtree(temp_dir)
        
        log_action('NHẬP DỮ LIỆU', 'Hệ thống', f'Khôi phục thành công từ file: {file.filename}')
        db.session.commit()
        flash('Phục hồi dữ liệu thành công! Khuyến cáo: Hãy khởi động lại máy chủ (server.py) để đảm bảo độ ổn định.', 'success')
        
    except Exception as e:
        flash(f'Có lỗi xảy ra trong quá trình phục hồi: {str(e)}', 'danger')

    return redirect(url_for('main.dashboard'))
