import os
import shutil
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required
from app.extensions import db
from app.utils import editor_required, log_action, update_info_file
from models import Factory, Machine, Device, Version

device_bp = Blueprint('device', __name__)

# ================= DEVICE MANAGEMENT =================
@device_bp.route('/machine/<int:machine_id>/devices')
@login_required
def manage_devices(machine_id):
    machine = db.get_or_404(Machine, machine_id)
    # Lấy factory để làm thanh điều hướng Breadcrumb: Xưởng -> Máy -> Thiết bị
    factory = db.get_or_404(Factory, machine.factory_id)
    devices = Device.query.filter_by(machine_id=machine_id, deleted_at=None).order_by(Device.created_at.desc()).all()
   
    return render_template('devices.html', machine=machine, factory=factory, devices=devices)

@device_bp.route('/machine/<int:machine_id>/devices/add', methods=['POST'])
@login_required
@editor_required
def add_device(machine_id):
    machine = db.get_or_404(Machine, machine_id)
    name = request.form.get('name')
    if not name or not name.strip():
        flash('Tên thiết bị không được để trống!', 'danger')
        return redirect(url_for('device.manage_devices', machine_id=machine_id))
    name = name.strip()
    
    device_type = request.form.get('device_type')
    raw_exts = request.form.get('allowed_exts')
    if not raw_exts or not raw_exts.strip():
        flash('Vui lòng nhập định dạng file hợp lệ!', 'danger')
        return redirect(url_for('device.manage_devices', machine_id=machine_id))
        
    allowed_exts = raw_exts.replace(' ', '').lower()
    for ext in allowed_exts.split(','):
        if not ext.startswith('.'):
            flash(f'Định dạng "{ext}" không hợp lệ. Phải bắt đầu bằng dấu chấm (vd: .cxp).', 'danger')
            return redirect(url_for('device.manage_devices', machine_id=machine_id))
            
    description = request.form.get('description', '').strip()
    requires_backup = request.form.get('requires_backup') == 'on'
   
    if Device.query.filter_by(machine_id=machine_id, name=name).first():
        flash(f'Thiết bị "{name}" đã tồn tại trong máy này!', 'danger')
    else:
        new_device = Device(machine_id=machine_id, name=name, device_type=device_type,
                            allowed_exts=allowed_exts, description=description, requires_backup=requires_backup)
        db.session.add(new_device)
        db.session.commit() # Cấp ID thiết bị
       
        # Tạo thư mục tận cùng cấp thiết bị và sinh file info
        os.makedirs(os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{machine.factory_id}', f'machine_{machine_id}', f'device_{new_device.id}'), exist_ok=True)
        update_info_file('device', machine_id)
       
        log_detail = f'Thêm thiết bị mới: "{name}" ({device_type}) cho máy "{machine.name}" (Xưởng: {machine.factory.name})'
        log_action('THÊM', 'Thiết bị', log_detail)
        db.session.commit()
       
        flash(f'Đã thêm thiết bị "{name}" thành công!', 'success')
       
    return redirect(url_for('device.manage_devices', machine_id=machine_id))

@device_bp.route('/devices/edit/<int:device_id>', methods=['POST'])
@login_required
@editor_required
def edit_device(device_id):
    device = db.get_or_404(Device, device_id)
    new_name = request.form.get('name')
   
    if new_name != device.name and Device.query.filter_by(machine_id=device.machine_id, name=new_name).first():
        flash(f'Tên thiết bị "{new_name}" đã tồn tại!', 'danger')
    else:
        device.name = new_name
        device.device_type = request.form.get('device_type')
        device.allowed_exts = request.form.get('allowed_exts').replace(' ', '').lower()
        device.description = request.form.get('description')
        device.requires_backup = request.form.get('requires_backup') == 'on'
        db.session.commit()
       
        # Cập nhật lại file _INFO_DEVICES.txt trong folder máy
        update_info_file('device', device.machine_id)
       
        flash('Đã cập nhật thông tin thiết bị!', 'success')
       
    return redirect(url_for('device.manage_devices', machine_id=device.machine_id))

@device_bp.route('/devices/delete/<int:device_id>', methods=['POST'])
@login_required
@editor_required
def delete_device(device_id):
    device = db.get_or_404(Device, device_id)
    now = datetime.now()
    timestamp = now.strftime('%d%m%Y_%H%M%S')
    machine_id = device.machine_id
   
    # Đánh dấu xóa mềm cho Thiết bị và Đổi tên
    original_name = device.name
    device.name = f"{original_name}_deleted_{timestamp}"
    device.deleted_at = now
    
    for version in device.versions:
        version.deleted_at = now

    # Di chuyển thư mục thiết bị sang ổ rác
    src_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{device.machine.factory_id}', f'machine_{machine_id}', f'device_{device_id}')
    if os.path.exists(src_dir):
        trash_dir_rel = f'device_{device_id}_deleted_{timestamp}'
        dst_dir = os.path.join(current_app.config['TRASH_FOLDER'], trash_dir_rel)
        shutil.move(src_dir, dst_dir)
        device.trash_path = trash_dir_rel

    db.session.commit()
    log_action('XÓA (MỀM)', 'Thiết bị', f'Chuyển Thiết bị "{original_name}" vào Thùng rác.')
    db.session.commit()
    flash(f'Đã chuyển thiết bị "{original_name}" vào thùng rác!', 'success')
    return redirect(url_for('device.manage_devices', machine_id=machine_id))
