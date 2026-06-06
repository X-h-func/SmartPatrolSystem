from datetime import date, datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models import db, User, Camera, PatrolRecord, Absence, InsufficientPatrol, CameraFault
from services.patrol_checker import check_daily_patrol, calculate_rounds

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    # Auto-check today's patrol status
    detection = check_daily_patrol()
    today = date.today()

    if current_user.is_patrol:
        # Patrol staff: show own stats
        rounds = calculate_rounds(current_user.id, today)
        total_cameras = Camera.query.filter_by(area=current_user.area).count()
        today_records = PatrolRecord.query.filter_by(
            user_id=current_user.id, patrol_date=today
        ).count()
        my_cameras = Camera.query.filter_by(area=current_user.area).all()

        # My recent exceptions
        my_insufficient = InsufficientPatrol.query.filter_by(
            user_id=current_user.id
        ).order_by(InsufficientPatrol.patrol_date.desc()).limit(5).all()

        return render_template('dashboard.html',
                               rounds=rounds,
                               total_cameras=total_cameras,
                               today_records=today_records,
                               my_cameras=my_cameras,
                               my_insufficient=my_insufficient,
                               detection=detection)

    # Admin / Supervisor view
    patrol_users = User.query.filter_by(role='patrol').all()
    total_patrol = len(patrol_users)

    # Count today's patrols
    patrolled_today = set()
    for u in patrol_users:
        count = PatrolRecord.query.filter_by(user_id=u.id, patrol_date=today).count()
        if count > 0:
            patrolled_today.add(u.id)
    actual_patrol = len(patrolled_today)
    absent_count = total_patrol - actual_patrol

    # Count insufficient today
    insufficient_count = InsufficientPatrol.query.filter_by(
        patrol_date=today, status='pending'
    ).count()
    # Also count those with < 4 rounds who haven't been flagged yet
    for u in patrol_users:
        if u.id in patrolled_today:
            rounds = calculate_rounds(u.id, today)
            if rounds < 4 and not InsufficientPatrol.query.filter_by(user_id=u.id, patrol_date=today).first():
                insufficient_count += 1

    # Cameras
    cameras = Camera.query.all()
    normal_cams = sum(1 for c in cameras if c.status == 'normal')
    fault_cams = sum(1 for c in cameras if c.status == 'fault')
    pending_faults = CameraFault.query.filter_by(status='pending').count()

    # Recent exceptions
    recent_absences = Absence.query.filter_by(status='pending').order_by(
        Absence.absence_date.desc()).limit(5).all()
    recent_insufficient = InsufficientPatrol.query.filter_by(status='pending').order_by(
        InsufficientPatrol.patrol_date.desc()).limit(5).all()
    recent_faults = CameraFault.query.filter_by(status='pending').order_by(
        CameraFault.fault_time.desc()).limit(5).all()

    return render_template('dashboard.html',
                           total_patrol=total_patrol,
                           actual_patrol=actual_patrol,
                           absent_count=absent_count,
                           insufficient_count=insufficient_count,
                           cameras=cameras,
                           normal_cams=normal_cams,
                           fault_cams=fault_cams,
                           pending_faults=pending_faults,
                           recent_absences=recent_absences,
                           recent_insufficient=recent_insufficient,
                           recent_faults=recent_faults,
                           detection=detection)
