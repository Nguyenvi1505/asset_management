import os
import re
import hashlib
import difflib
import shutil
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.utils import editor_required, log_action, calculate_file_hash, get_abs_upload_path, get_abs_trash_path
from models import Factory, Machine, Device, Version

version_bp = Blueprint('version', __name__)

# ================= VERSION MANAGEMENT =================
@version_bp.route('/device/<int:device_id>/versions')
@login_required
def manage_versions(device_id):
    device = db.get_or_404(Device, device_id)
    machine = db.get_or_404(Machine, device.machine_id)
    factory = db.get_or_404(Factory, machine.factory_id)
   
    versions = Version.query.filter_by(device_id=device_id, deleted_at=None).order_by(Version.created_at.desc()).all()
    return render_template('versions.html', device=device, machine=machine, factory=factory, versions=versions)

@version_bp.route('/device/<int:device_id>/versions/add', methods=['POST'])
@login_required
@editor_required
def add_version(device_id):
    device = db.get_or_404(Device, device_id)
    version_number = request.form.get('version_number')
    if not version_number or not version_number.strip():
        flash('Số phiên bản không được để trống!', 'danger')
        return redirect(url_for('version.manage_versions', device_id=device_id))
    version_number = version_number.strip()
    
    # Kiểm tra trùng lặp tên phiên bản trong cùng 1 thiết bị
    if Version.query.filter_by(device_id=device_id, version_number=version_number).first():
        flash(f'Phiên bản "{version_number}" đã tồn tại trong thiết bị này! Vui lòng đặt tên khác.', 'danger')
        return redirect(url_for('version.manage_versions', device_id=device_id))
    
    changelog = request.form.get('changelog')
    if not changelog or not changelog.strip():
        flash('Mô tả thay đổi không được để trống!', 'danger')
        return redirect(url_for('version.manage_versions', device_id=device_id))
    changelog = changelog.strip()
   
    file = request.files.get('program_file')
    text_file = request.files.get('text_file')
    backup_file = request.files.get('backup_file')
   
    if not file or file.filename == '':
        flash('Vui lòng chọn file chương trình gốc!', 'warning')
        return redirect(url_for('version.manage_versions', device_id=device_id))

    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [ext.strip() for ext in device.allowed_exts.split(',')]
   
    if file_ext not in allowed_exts:
        flash(f'Định dạng {file_ext} không hợp lệ! Vui lòng tải lên các file: {device.allowed_exts}', 'danger')
        return redirect(url_for('version.manage_versions', device_id=device_id))

    # ================= 1. XÁC ĐỊNH ĐƯỜNG DẪN THƯ MỤC BẰNG ID =================
    factory_id = device.machine.factory_id
    machine_id = device.machine_id
   
    # Cấu trúc: uploads/factory_1/machine_2/device_3
    save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{factory_id}', f'machine_{machine_id}', f'device_{device_id}')
   
    # Đề phòng trường hợp lỗi chưa có folder (VD: do admin tự tay xóa nhầm trên ổ cứng) thì tạo lại
    os.makedirs(save_dir, exist_ok=True)
   
    # ================= 2. TẠO TÊN FILE MỚI =================
    current_time = datetime.now().strftime('%d%m%Y_%H%M%S')
    safe_version = version_number.replace('.', '_')
   
    safe_filename = secure_filename(file.filename)
    orig_name, orig_ext = os.path.splitext(safe_filename)

    save_name = f"{orig_name}_{safe_version}_{current_time}{orig_ext}"
    file_path = os.path.join(save_dir, save_name)
   
    file.save(file_path)
   
    file_size = os.path.getsize(file_path)
    file_hash = calculate_file_hash(file_path)
   
    # Convert to relative paths
    rel_file_path = os.path.relpath(file_path, current_app.config['UPLOAD_FOLDER']).replace('\\', '/')
    
    # ================= KIỂM TRA TRÙNG LẶP =================
    existing_version = Version.query.filter_by(device_id=device_id, file_hash=file_hash).first()

    if existing_version:
        if os.path.exists(file_path):
            os.remove(file_path)
        flash(f'Tải lên thất bại: File này giống hệt phiên bản {existing_version.version_number} từng được upload! Không có sự thay đổi logic nào.', 'danger')
        return redirect(url_for('version.manage_versions', device_id=device_id))

    # ================= 3. XỬ LÝ LƯU FILE TEXT (.CXT) =================
    text_save_path = None
    rel_text_save_path = None
    if text_file and text_file.filename != '':
        safe_text_filename = secure_filename(text_file.filename)
        orig_text_name, orig_text_ext = os.path.splitext(safe_text_filename)
        
        text_save_name = f"{orig_text_name}_TEXT_{safe_version}_{current_time}{orig_text_ext}"
        text_save_path = os.path.join(save_dir, text_save_name)
        text_file.save(text_save_path)
        rel_text_save_path = os.path.relpath(text_save_path, current_app.config['UPLOAD_FOLDER']).replace('\\', '/')

    # ================= 4. XỬ LÝ LƯU FILE BACKUP (.ZIP/.RAR) =================
    rel_backup_save_path = None
    if device.requires_backup and backup_file and backup_file.filename != '':
        safe_backup_filename = secure_filename(backup_file.filename)
        orig_backup_name, orig_backup_ext = os.path.splitext(safe_backup_filename)
        
        backup_save_name = f"{orig_backup_name}_BACKUP_{safe_version}_{current_time}{orig_backup_ext}"
        backup_save_path = os.path.join(save_dir, backup_save_name)
        backup_file.save(backup_save_path)
        rel_backup_save_path = os.path.relpath(backup_save_path, current_app.config['UPLOAD_FOLDER']).replace('\\', '/')

    # Lưu vào Database
    new_version = Version(
        device_id=device_id,
        version_number=version_number,
        user_id=current_user.id,
        changelog=changelog,
        file_path=rel_file_path,
        file_hash=file_hash,
        file_size=file_size,
        text_file_path=rel_text_save_path,
        backup_file_path=rel_backup_save_path
    )
    db.session.add(new_version)
    db.session.commit()
   
    # Ghi Log
    log_detail = f'Tải lên Version {version_number} cho thiết bị "{device.name}" (Máy: {device.machine.name} - Xưởng: {device.machine.factory.name}). Mã băm: {file_hash[:8]}...'
    log_action('UPLOAD', 'Version', log_detail)
    db.session.commit()
   
    flash(f'Đã tải lên phiên bản {version_number} thành công!', 'success')
    return redirect(url_for('version.manage_versions', device_id=device_id))

@version_bp.route('/versions/compare/<int:version_id>', methods=['POST'])
@login_required
def compare_version(version_id):
    # Lấy đích danh phiên bản được chọn làm tham chiếu
    target_version = db.get_or_404(Version, version_id)
    device_id = target_version.device_id
    device = db.get_or_404(Device, device_id)
    machine = db.get_or_404(Machine, device.machine_id)
    factory = db.get_or_404(Factory, machine.factory_id)
   
    # Lấy toàn bộ lịch sử để dò tìm file trùng (nếu có sai khác)
    versions = Version.query.filter_by(device_id=device_id).order_by(Version.created_at.desc()).all()
   
    file = request.files.get('compare_file')
    if not file or file.filename == '':
        flash('Vui lòng chọn file chương trình để so sánh!', 'warning')
        return redirect(url_for('version.manage_versions', device_id=device_id))

    hasher = hashlib.sha256()
    file_content = file.read()
    hasher.update(file_content)
    file_hash = hasher.hexdigest()

    # Kịch bản 1: File y hệt bản tham chiếu đang chọn
    if file_hash == target_version.file_hash:
        flash(f'✅ KHÔNG CÓ SAI KHÁC: File giống y hệt phiên bản tham chiếu ({target_version.version_number}).', 'success')
    else:
        is_text_file = file.filename.lower().endswith(('.cxt', '.st', '.xml', '.txt', '.scl'))
       
        # Kịch bản 2: Có sai khác & Hỗ trợ so sánh dòng
        abs_text_file_path = get_abs_upload_path(target_version.text_file_path)
        if is_text_file and abs_text_file_path and os.path.exists(abs_text_file_path):
            file.seek(0)
            try:
                with open(abs_text_file_path, 'r', encoding='utf-8-sig', errors='replace') as f1:
                    old_lines_raw = f1.read().splitlines()
               
                new_lines_raw = file.read().decode('utf-8-sig', errors='replace').splitlines()

                def get_omron_time(lines_raw):
                    raw_str, fmt_str = "Không xác định", "Không xác định"
                    for line in lines_raw:
                        match = re.search(r'Modified:=\"([^\"]+)\"', line)
                        if match:
                            raw_str = match.group(1)
                            parts = raw_str.split()
                            if len(parts) >= 6:
                                fmt_str = f"{parts[0].zfill(2)}/{parts[1].zfill(2)}/{parts[2]} {parts[3].zfill(2)}:{parts[4].zfill(2)}:{parts[5].zfill(2)}"
                            else:
                                fmt_str = raw_str
                            break
                    return raw_str, fmt_str
               
                old_time_raw, old_time_fmt = get_omron_time(old_lines_raw)
                new_time_raw, new_time_fmt = get_omron_time(new_lines_raw)
               
                def sanitize_omron_cxt(lines):
                    sanitized = []
                    for line in lines:
                        line = re.sub(r'Modified:=\"[^\"]+\";', 'Modified:="[IGNORED_TIMESTAMP]";', line)
                        line = re.sub(r'\$\?St\$Bk\?_#\[\d+\]', '$?St$Bk?_#[ID_IGNORED]', line)
                        line = re.sub(r'BEGIN_LIST_\$#\[\d+\]', 'BEGIN_LIST_$#[ID_IGNORED]', line)
                        line = re.sub(r'END_LIST_\$#\[\d+\]', 'END_LIST_$#[ID_IGNORED]', line)
                        sanitized.append(line)
                    return sanitized

                old_lines = sanitize_omron_cxt(old_lines_raw)
                new_lines = sanitize_omron_cxt(new_lines_raw)

                if old_lines == new_lines:
                    flash(f'✅ KHÔNG CÓ SAI KHÁC LOGIC: File giống hoàn toàn bản {target_version.version_number}.', 'success')
                    return redirect(url_for('version.manage_versions', device_id=device_id))

                sm = difflib.SequenceMatcher(None, old_lines, new_lines)
                change_summary = []
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag == 'replace':
                        text = f"Sửa đổi ở dòng {i1+1}" if i1+1 == i2 else f"Sửa đổi từ dòng {i1+1} đến {i2}"
                        change_summary.append(text)
                    elif tag == 'delete':
                        text = f"Xóa dòng {i1+1}" if i1+1 == i2 else f"Xóa từ dòng {i1+1} đến {i2}"
                        change_summary.append(text)
                    elif tag == 'insert':
                        change_summary.append(f"Thêm code mới vào sau dòng {i1}")
               
                if len(change_summary) > 15:
                    change_summary = change_summary[:15] + ["... và nhiều thay đổi khác (Xem chi tiết bên dưới)."]

                db_upload_time = target_version.created_at.strftime('%d/%m/%Y %H:%M:%S')

                html_differ = difflib.HtmlDiff(wrapcolumn=80)
                diff_html = html_differ.make_table(
                    old_lines, new_lines,
                    fromdesc=f'Bản tham chiếu {target_version.version_number} (CXP Lưu: {old_time_fmt} | Up Server: {db_upload_time})',
                    todesc=f'File kiểm tra (CXP Lưu: {new_time_fmt})',
                    context=False
                )

                diff_html = diff_html.replace('[IGNORED_TIMESTAMP]', old_time_raw, 1)
                diff_html = diff_html.replace('[IGNORED_TIMESTAMP]', new_time_raw, 1)

                flash(f'⚠️ CÓ SAI KHÁC SO VỚI BẢN {target_version.version_number}: Vui lòng xem báo cáo.', 'warning')
                return render_template('versions.html', device=device, machine=machine, factory=factory, versions=versions, diff_html=diff_html, change_summary=change_summary)
               
            except Exception as e:
                flash(f'Lỗi đọc file so sánh: {e}', 'danger')
        else:
            # Kịch bản 3: Có sai khác & Không thể so sánh dòng (File nhị phân)
            # Kiểm tra xem có tình cờ giống một bản nào khác trong lịch sử không
            matched_version = next((v for v in versions if v.file_hash == file_hash and v.id != target_version.id), None)
            if matched_version:
                flash(f'⚠️ CÓ SAI KHÁC với bản {target_version.version_number}, nhưng lại vô tình giống hệt bản {matched_version.version_number}.', 'warning')
            else:
                flash(f'❌ CÓ SAI KHÁC với bản {target_version.version_number}. Đây là một file chương trình hoàn toàn lạ!', 'danger')

    return redirect(url_for('version.manage_versions', device_id=device_id))

@version_bp.route('/versions/download/<int:version_id>')
@login_required
def download_version(version_id):
    version = db.get_or_404(Version, version_id)
    abs_file_path = get_abs_upload_path(version.file_path)
    if abs_file_path and os.path.exists(abs_file_path):
        # as_attachment=True sẽ ép trình duyệt tải file về thay vì mở trực tiếp
        log_detail = f'Tải mã nguồn Version {version.version_number} của thiết bị "{version.device.name}" (Máy: {version.device.machine.name} - Xưởng: {version.device.machine.factory.name})'
        log_action('TẢI VỀ', 'Version', log_detail)
        db.session.commit()
        return send_file(abs_file_path, as_attachment=True)
    else:
        flash('File vật lý không tồn tại trên server!', 'danger')
        return redirect(request.referrer)
        
@version_bp.route('/versions/download_backup/<int:version_id>')
@login_required
def download_backup(version_id):
    version = db.get_or_404(Version, version_id)
    if not version.backup_file_path:
        flash('Phiên bản này không có file backup đính kèm!', 'warning')
        return redirect(request.referrer)
        
    abs_file_path = get_abs_upload_path(version.backup_file_path)
    if abs_file_path and os.path.exists(abs_file_path):
        log_detail = f'Tải Backup Folder của Version {version.version_number} thiết bị "{version.device.name}"'
        log_action('TẢI VỀ', 'Backup', log_detail)
        db.session.commit()
        return send_file(abs_file_path, as_attachment=True)
    else:
        flash('File backup vật lý không tồn tại trên server!', 'danger')
        return redirect(request.referrer)
   
@version_bp.route('/versions/edit/<int:version_id>', methods=['POST'])
@login_required
@editor_required
def edit_version(version_id):
    version = db.get_or_404(Version, version_id)
   
    # Chỉ cho phép cập nhật metadata, không cho phép đổi file
    version_number = request.form.get('version_number')
    if not version_number or not version_number.strip():
        flash('Số phiên bản không được để trống!', 'danger')
        return redirect(url_for('version.manage_versions', device_id=version.device_id))
    version_number = version_number.strip()
        
    # Kiểm tra trùng lặp tên phiên bản trong cùng 1 thiết bị (loại trừ chính bản thân nó)
    if version_number != version.version_number:
        if Version.query.filter_by(device_id=version.device_id, version_number=version_number).first():
            flash(f'Phiên bản "{version_number}" đã tồn tại trong thiết bị này! Vui lòng đặt tên khác.', 'danger')
            return redirect(url_for('version.manage_versions', device_id=version.device_id))
            
    changelog = request.form.get('changelog')
    if not changelog or not changelog.strip():
        flash('Mô tả thay đổi không được để trống!', 'danger')
        return redirect(url_for('version.manage_versions', device_id=version.device_id))
        
    version.version_number = version_number.strip()
    version.changelog = changelog.strip()

    log_detail = f'Sửa thông tin của Version {version.version_number} thuộc thiết bị "{version.device.name}" (Máy: {version.device.machine.name} - Xưởng: {version.device.machine.factory.name})'
    log_action('SỬA', 'Version', log_detail)
    db.session.commit()
    flash('Đã cập nhật thông tin Version thành công!', 'success')
    return redirect(url_for('version.manage_versions', device_id=version.device_id))

@version_bp.route('/versions/delete/<int:version_id>', methods=['POST'])
@login_required
@editor_required
def delete_version(version_id):
    version = db.get_or_404(Version, version_id)
    device_id = version.device_id
    now = datetime.now()
    timestamp = now.strftime('%d%m%Y_%H%M%S')
   
    # 1. Đánh dấu xóa mềm và Đổi tên version
    original_version_number = version.version_number
    version.version_number = f"{original_version_number}_deleted_{timestamp}"
    version.deleted_at = now
   
    # 2. Tạo folder rác riêng cho version này và di chuyển các file vật lý vào đó
    trash_dir_rel = f'version_{version.id}_deleted_{timestamp}'
    trash_dir = os.path.join(current_app.config['TRASH_FOLDER'], trash_dir_rel)
    os.makedirs(trash_dir, exist_ok=True)
    
    # Chuyển file chương trình gốc
    abs_file_path = get_abs_upload_path(version.file_path)
    if abs_file_path and os.path.exists(abs_file_path):
        shutil.move(abs_file_path, os.path.join(trash_dir, os.path.basename(abs_file_path)))
    
    # Chuyển file text (nếu có)
    abs_text_path = get_abs_upload_path(version.text_file_path)
    if abs_text_path and os.path.exists(abs_text_path):
        shutil.move(abs_text_path, os.path.join(trash_dir, os.path.basename(abs_text_path)))
        
    # Chuyển file backup (nếu có)
    abs_backup_path = get_abs_upload_path(version.backup_file_path)
    if abs_backup_path and os.path.exists(abs_backup_path):
        shutil.move(abs_backup_path, os.path.join(trash_dir, os.path.basename(abs_backup_path)))
        
    version.trash_path = trash_dir_rel

    device_name = version.device.name
    machine_name = version.device.machine.name
    factory_name = version.device.machine.factory.name
           
    log_detail = f'Xóa (Mềm) Version {original_version_number} của thiết bị "{device_name}" (Máy: {machine_name} - Xưởng: {factory_name})'
    log_action('XÓA (MỀM)', 'Version', log_detail)
    db.session.commit()
   
    db.session.commit()
   
    flash(f'Đã chuyển phiên bản {original_version_number} vào thùng rác!', 'success')
    return redirect(url_for('version.manage_versions', device_id=device_id))
