import os
import shutil
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required
from app.extensions import db
from app.utils import editor_required, log_action, update_info_file
from models import Factory, Machine, Device, Version

machine_bp = Blueprint('machine', __name__)

# ================= MACHINE MANAGEMENT =================
@machine_bp.route('/factory/<int:factory_id>/machines')
@login_required
def manage_machines(factory_id):
    factory = db.get_or_404(Factory, factory_id)
    # Lấy danh sách máy của xưởng hiện tại
    machines = Machine.query.filter_by(factory_id=factory_id, deleted_at=None).order_by(Machine.created_at.desc()).all()
    
    all_factories = Factory.query.filter_by(deleted_at=None).all()
    
    return render_template('machines.html', factory=factory, machines=machines, all_factories=all_factories)

@machine_bp.route('/factory/<int:factory_id>/machines/add', methods=['POST'])
@login_required
@editor_required
def add_machine(factory_id):
    factory = db.get_or_404(Factory, factory_id)
    name = request.form.get('name')
    if not name or not name.strip():
        flash('Tên máy không được để trống!', 'danger')
        return redirect(url_for('machine.manage_machines', factory_id=factory_id))
    name = name.strip()
    description = request.form.get('description', '').strip()
   
    if Machine.query.filter_by(factory_id=factory_id, name=name).first():
        flash(f'Máy "{name}" đã tồn tại trong xưởng này!', 'danger')
    else:
        new_machine = Machine(factory_id=factory_id, name=name, description=description)
        db.session.add(new_machine)
        db.session.commit() # Cấp ID cho máy mới
       
        # Tạo thư mục con cấp máy và sinh file info
        os.makedirs(os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{factory_id}', f'machine_{new_machine.id}'), exist_ok=True)
        update_info_file('machine', factory_id)
       
        log_detail = f'Khai báo máy mới: "{name}" thuộc xưởng "{factory.name}"'
        log_action('THÊM', 'Máy', log_detail)
        db.session.commit()
       
        flash(f'Đã thêm máy "{name}" thành công!', 'success')
       
    return redirect(url_for('machine.manage_machines', factory_id=factory_id))

@machine_bp.route('/machines/edit/<int:machine_id>', methods=['POST'])
@login_required
@editor_required
def edit_machine(machine_id):
    machine = db.get_or_404(Machine, machine_id)
    
    new_name = request.form.get('name')
    if not new_name or not new_name.strip():
        flash('Tên máy không được để trống!', 'danger')
        return redirect(url_for('machine.manage_machines', factory_id=machine.factory_id))
    new_name = new_name.strip()
    new_factory_id = int(request.form.get('factory_id', machine.factory_id))
    old_factory_id = machine.factory_id
    
    # 1. Kiểm tra trùng lặp tên ở XƯỞNG ĐÍCH (Chỉ kiểm tra các máy chưa bị xóa)
    if (new_name != machine.name or new_factory_id != old_factory_id) and \
       Machine.query.filter_by(factory_id=new_factory_id, name=new_name, deleted_at=None).first():
        flash(f'Tên máy "{new_name}" đã tồn tại trong xưởng đích!', 'danger')
        return redirect(url_for('machine.manage_machines', factory_id=old_factory_id))
        
    # 2. Cập nhật thông tin cơ bản
    machine.name = new_name
    machine.description = request.form.get('description')
    
    # 3. NẾU CÓ ĐIỀU CHUYỂN SANG XƯỞNG KHÁC
    if new_factory_id != old_factory_id:
        src_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{old_factory_id}', f'machine_{machine_id}')
        dst_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{new_factory_id}', f'machine_{machine_id}')
        
        # a. Di chuyển thư mục vật lý nếu tồn tại
        if os.path.exists(src_dir):
            os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
            shutil.move(src_dir, dst_dir)
            
        # b. Cập nhật lại đường dẫn tuyệt đối cho TOÀN BỘ file Version cũ
        old_path_segment = f'factory_{old_factory_id}'
        new_path_segment = f'factory_{new_factory_id}'
        
        for device in machine.devices:
            for version in device.versions:
                if version.file_path:
                    version.file_path = version.file_path.replace(old_path_segment, new_path_segment)
                if version.text_file_path:
                    version.text_file_path = version.text_file_path.replace(old_path_segment, new_path_segment)
                    
        # c. Đổi ID Xưởng
        machine.factory_id = new_factory_id
        db.session.commit()
        
        # d. Cập nhật lại file _INFO_MACHINES.txt cho cả 2 xưởng
        update_info_file('machine', old_factory_id)
        update_info_file('machine', new_factory_id)
        
        # e. Ghi Log
        log_action('SỬA', 'Máy', f'Đổi tên thành "{new_name}" và CHUYỂN từ Xưởng ID {old_factory_id} sang Xưởng ID {new_factory_id}')
        db.session.commit()
        flash(f'Đã cập nhật và điều chuyển máy "{new_name}" sang xưởng mới thành công!', 'success')
        return redirect(url_for('machine.manage_machines', factory_id=new_factory_id))
        
    else:
        # Nếu chỉ sửa tên bình thường trong cùng 1 xưởng
        db.session.commit()
        update_info_file('machine', old_factory_id)
        flash('Cập nhật thông tin máy thành công!', 'success')
        return redirect(url_for('machine.manage_machines', factory_id=old_factory_id))

@machine_bp.route('/machines/delete/<int:machine_id>', methods=['POST'])
@login_required
@editor_required
def delete_machine(machine_id):
    machine = db.get_or_404(Machine, machine_id)
    now = datetime.now()
    timestamp = now.strftime('%d%m%Y_%H%M%S')
    factory_id = machine.factory_id
   
    # Đánh dấu xóa mềm cho Máy và Đổi tên
    original_name = machine.name
    machine.name = f"{original_name}_deleted_{timestamp}"
    machine.deleted_at = now
    
    for device in machine.devices:
        device.deleted_at = now
        for version in device.versions:
            version.deleted_at = now

    # Di chuyển thư mục máy sang ổ rác
    src_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{factory_id}', f'machine_{machine_id}')
    if os.path.exists(src_dir):
        trash_dir_rel = f'machine_{machine_id}_deleted_{timestamp}'
        dst_dir = os.path.join(current_app.config['TRASH_FOLDER'], trash_dir_rel)
        shutil.move(src_dir, dst_dir)
        machine.trash_path = trash_dir_rel

    db.session.commit()
    log_action('XÓA (MỀM)', 'Máy', f'Chuyển Máy "{original_name}" vào Thùng rác.')
    db.session.commit()
    flash(f'Đã chuyển máy "{original_name}" vào thùng rác!', 'success')
    return redirect(url_for('machine.manage_machines', factory_id=factory_id))
    