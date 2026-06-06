from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db, Camera
from decorators import role_required

cameras_bp = Blueprint('cameras', __name__)


@cameras_bp.route('/cameras')
@login_required
@role_required('admin')
def index():
    cameras = Camera.query.order_by(Camera.area, Camera.camera_id).all()
    return render_template('cameras.html', cameras=cameras)


@cameras_bp.route('/cameras/add', methods=['POST'])
@login_required
@role_required('admin')
def add():
    camera_id = request.form.get('camera_id', '').strip()
    location = request.form.get('location', '').strip()
    ip_address = request.form.get('ip_address', '').strip()
    area = request.form.get('area', '').strip()
    status = request.form.get('status', 'normal')

    if not camera_id or not location or not area:
        flash('摄像头编号、位置和区域为必填项', 'danger')
        return redirect(url_for('cameras.index'))

    if Camera.query.filter_by(camera_id=camera_id).first():
        flash(f'摄像头编号 {camera_id} 已存在', 'danger')
        return redirect(url_for('cameras.index'))

    cam = Camera(camera_id=camera_id, location=location, ip_address=ip_address,
                 area=area, status=status)
    db.session.add(cam)
    db.session.commit()
    flash(f'摄像头 {camera_id} 已添加', 'success')
    return redirect(url_for('cameras.index'))


@cameras_bp.route('/cameras/<int:id>/edit', methods=['POST'])
@login_required
@role_required('admin')
def edit(id):
    cam = Camera.query.get_or_404(id)
    cam.location = request.form.get('location', cam.location).strip()
    cam.ip_address = request.form.get('ip_address', cam.ip_address).strip()
    cam.area = request.form.get('area', cam.area).strip()
    cam.status = request.form.get('status', cam.status)
    cam.notes = request.form.get('notes', cam.notes)
    db.session.commit()
    flash(f'摄像头 {cam.camera_id} 已更新', 'success')
    return redirect(url_for('cameras.index'))


@cameras_bp.route('/cameras/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    cam = Camera.query.get_or_404(id)
    db.session.delete(cam)
    db.session.commit()
    flash(f'摄像头 {cam.camera_id} 已删除', 'success')
    return redirect(url_for('cameras.index'))


@cameras_bp.route('/cameras/<int:id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_status(id):
    cam = Camera.query.get_or_404(id)
    cam.status = 'normal' if cam.status == 'fault' else 'fault'
    db.session.commit()
    flash(f'摄像头 {cam.camera_id} 状态已切换为 {cam.status}', 'info')
    return redirect(url_for('cameras.index'))
