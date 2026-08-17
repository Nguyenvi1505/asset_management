import os
import shutil
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required
from app.extensions import db
from app.utils import editor_required, log_action, update_info_file
from models import Factory, Machine, Device, Version

factory_bp = Blueprint('factory', __name__)

# ================= FACTORY MANAGEMENT =================
@factory_bp.route('/factories')
@login_required
def manage_factories():
    # Lọc bỏ các xưởng đã nằm trong thùng rác
    factories = Factory.query.filter_by(deleted_at=None).order_by(Factory.created_at.desc()).all()
    return render_template('factories.html', factories=factories)

@factory_bp.route('/factories/add', methods=['POST'])
@login_required
@editor_required
def add_factory():
    name = request.form.get('name')
    if not name or not name.strip():
        flash('Tên xưởng không được để trống!', 'danger')
        return redirect(url_for('factory.manage_factories'))
    name = name.strip()
    description = request.form.get('description', '').strip()
   
    if Factory.query.filter_by(name=name).first():
        flash(f'Xưởng "{name}" đã tồn tại!', 'danger')
    else:
        new_factory = Factory(name=name, description=description)
        db.session.add(new_factory)
       
        # PHẢI COMMIT TRƯỚC ĐỂ DATABASE CẤP ID CHO XƯỞNG MỚI
        db.session.commit()
       
        # Khởi tạo thư mục vật lý theo ID và sinh file _INFO
        os.makedirs(os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{new_factory.id}'), exist_ok=True)
        update_info_file('factory')
       
        # Ghi log thao tác
        log_detail = f'Thêm xưởng sản xuất mới: "{name}"'
        log_action('THÊM', 'Xưởng', log_detail)
        db.session.commit()
       
        flash(f'Đã thêm xưởng "{name}" thành công!', 'success')
       
    return redirect(url_for('factory.manage_factories'))

@factory_bp.route('/factories/edit/<int:factory_id>', methods=['POST'])
@login_required
@editor_required
def edit_factory(factory_id):
    factory = db.get_or_404(Factory, factory_id)
    new_name = request.form.get('name')
   
    if new_name != factory.name and Factory.query.filter_by(name=new_name).first():
        flash(f'Tên xưởng "{new_name}" đã được sử dụng!', 'danger')
    else:
        factory.name = new_name
        factory.description = request.form.get('description')
        db.session.commit()
       
        # Cập nhật lại file _INFO.txt ngoài thư mục gốc vì tên Xưởng đã đổi
        update_info_file('factory')
       
        flash('Đã cập nhật thông tin xưởng!', 'success')
       
    return redirect(url_for('factory.manage_factories'))

@factory_bp.route('/factories/delete/<int:factory_id>', methods=['POST'])
@login_required
@editor_required
def delete_factory(factory_id):
    factory = db.get_or_404(Factory, factory_id)
    now = datetime.now()
    timestamp = now.strftime('%d%m%Y_%H%M%S')
   
    # 1. Đánh dấu xóa mềm và Đổi tên (Giải phóng tên gốc)
    original_name = factory.name
    factory.name = f"{original_name}_deleted_{timestamp}"
    factory.deleted_at = now
    
    for machine in factory.machines:
        machine.deleted_at = now
        for device in machine.devices:
            device.deleted_at = now
            for version in device.versions:
                version.deleted_at = now

    # 2. Di chuyển thư mục vật lý sang ổ rác
    src_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f'factory_{factory_id}')
    if os.path.exists(src_dir):
        trash_dir_rel = f'factory_{factory_id}_deleted_{timestamp}'
        dst_dir = os.path.join(current_app.config['TRASH_FOLDER'], trash_dir_rel)
        shutil.move(src_dir, dst_dir)
        factory.trash_path = trash_dir_rel # Lưu lại vết để sau này khôi phục

    db.session.commit()
    log_action('XÓA (MỀM)', 'Xưởng', f'Chuyển Xưởng "{original_name}" và toàn bộ dữ liệu vào Thùng rác.')
    db.session.commit()
    flash(f'Đã chuyển Xưởng "{original_name}" vào thùng rác!', 'success')
    return redirect(url_for('factory.manage_factories'))
