from datetime import date, datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from models import db, User, Camera, Absence, InsufficientPatrol, CameraFault
from decorators import role_required

exceptions_bp = Blueprint('exceptions', __name__)


# ============ ABSENCES ============

@exceptions_bp.route('/absences')
@login_required
@role_required('admin', 'supervisor')
def absences():
    status_filter = request.args.get('status', '')
    query = Absence.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    absences_list = query.order_by(Absence.absence_date.desc()).all()
    users = User.query.filter_by(role='patrol').all()
    return render_template('absences.html', absences=absences_list, users=users,
                           status_filter=status_filter)


@exceptions_bp.route('/absences/<int:id>/approve', methods=['POST'])
@login_required
@role_required('admin', 'supervisor')
def approve_absence(id):
    absence = Absence.query.get_or_404(id)
    comment = request.form.get('comment', '')
    absence.status = 'approved'
    absence.comment = comment
    absence.reviewed_by = current_user.id
    absence.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash('缺勤已审批通过', 'success')
    return redirect(url_for('exceptions.absences'))


@exceptions_bp.route('/absences/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin', 'supervisor')
def reject_absence(id):
    absence = Absence.query.get_or_404(id)
    comment = request.form.get('comment', '')
    absence.status = 'rejected'
    absence.comment = comment
    absence.reviewed_by = current_user.id
    absence.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash('缺勤已驳回', 'warning')
    return redirect(url_for('exceptions.absences'))


# ============ INSUFFICIENT PATROL ============

@exceptions_bp.route('/insufficient')
@login_required
def insufficient():
    status_filter = request.args.get('status', '')
    query = InsufficientPatrol.query
    if current_user.is_patrol:
        query = query.filter_by(user_id=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    records = query.order_by(InsufficientPatrol.patrol_date.desc()).all()
    users = User.query.filter_by(role='patrol').all()
    return render_template('insufficient.html', records=records, users=users,
                           status_filter=status_filter)


@exceptions_bp.route('/insufficient/<int:id>/confirm', methods=['POST'])
@login_required
def confirm_insufficient(id):
    record = InsufficientPatrol.query.get_or_404(id)
    # Patrol can only confirm their own; supervisor/admin can confirm any
    if current_user.is_patrol and record.user_id != current_user.id:
        flash('您只能确认自己的巡更不足记录', 'danger')
        return redirect(url_for('exceptions.insufficient'))

    comment = request.form.get('comment', '')
    record.status = 'confirmed'
    record.comment = comment
    record.confirmed_by = current_user.id
    record.confirmed_at = datetime.utcnow()
    db.session.commit()
    flash('巡更不足已确认', 'success')
    return redirect(url_for('exceptions.insufficient'))


# ============ CAMERA FAULTS ============

@exceptions_bp.route('/camera-faults')
@login_required
@role_required('admin', 'supervisor')
def camera_faults():
    status_filter = request.args.get('status', '')
    query = CameraFault.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    faults = query.order_by(CameraFault.fault_time.desc()).all()
    cameras = Camera.query.all()
    return render_template('camera_faults.html', faults=faults, cameras=cameras,
                           status_filter=status_filter)


@exceptions_bp.route('/camera-faults/report', methods=['POST'])
@login_required
def report_fault():
    camera_id = request.form.get('camera_id', '')
    description = request.form.get('description', '')

    if not camera_id:
        flash('请选择摄像头', 'danger')
        return redirect(request.referrer or url_for('dashboard.index'))

    cam = Camera.query.get(int(camera_id))
    if cam:
        cam.status = 'fault'
    fault = CameraFault(
        camera_id=int(camera_id),
        reported_by=current_user.id,
        fault_time=datetime.utcnow(),
        description=description,
        status='pending'
    )
    db.session.add(fault)
    db.session.commit()
    flash('摄像头故障已上报', 'success')
    return redirect(url_for('exceptions.camera_faults'))


@exceptions_bp.route('/camera-faults/<int:id>/confirm', methods=['POST'])
@login_required
@role_required('admin', 'supervisor')
def confirm_fault(id):
    fault = CameraFault.query.get_or_404(id)
    resolution = request.form.get('resolution', '')
    fault.status = 'confirmed'
    fault.resolution = resolution
    fault.resolved_by = current_user.id
    fault.resolved_at = datetime.utcnow()
    db.session.commit()
    flash('摄像头故障已确认', 'success')
    return redirect(url_for('exceptions.camera_faults'))


@exceptions_bp.route('/camera-faults/<int:id>/resolve', methods=['POST'])
@login_required
@role_required('admin', 'supervisor')
def resolve_fault(id):
    fault = CameraFault.query.get_or_404(id)
    resolution = request.form.get('resolution', '')
    fault.status = 'resolved'
    fault.resolution = resolution
    fault.resolved_by = current_user.id
    fault.resolved_at = datetime.utcnow()

    # Restore camera status
    cam = Camera.query.get(fault.camera_id)
    if cam:
        cam.status = 'normal'

    db.session.commit()
    flash('摄像头故障已标记为已解决，摄像头状态已恢复', 'success')
    return redirect(url_for('exceptions.camera_faults'))
