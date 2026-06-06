"""Patrol auto-checker: calculates completed rounds and auto-detects absences/insufficient patrols."""

from datetime import date, datetime

from models import db, User, Camera, PatrolRecord, Absence, InsufficientPatrol


def calculate_rounds(user_id, patrol_date):
    """
    Calculate completed patrol rounds for a user on a given date.
    A complete round = visiting every camera in the user's area at least once.
    rounds = min(visit_count per camera in area).
    """
    user = User.query.get(user_id)
    if not user or not user.area:
        return 0

    cameras = Camera.query.filter_by(area=user.area, status='normal').all()
    if not cameras:
        return 0

    camera_ids = [c.id for c in cameras]
    visit_counts = []
    for cid in camera_ids:
        count = PatrolRecord.query.filter_by(
            user_id=user_id,
            camera_id=cid,
            patrol_date=patrol_date
        ).count()
        visit_counts.append(count)

    return min(visit_counts) if visit_counts else 0


def check_daily_patrol():
    """
    Check all patrol staff for today:
    - If 0 records → create absence record (if not exists)
    - If < 4 rounds → create insufficient patrol record (if not exists)
    Returns dict with counts of what was detected.
    """
    today = date.today()
    patrol_users = User.query.filter_by(role='patrol').all()
    new_absences = 0
    new_insufficient = 0

    for user in patrol_users:
        # Count today's patrol records
        record_count = PatrolRecord.query.filter_by(
            user_id=user.id,
            patrol_date=today
        ).count()

        if record_count == 0:
            # Check if absence already recorded for today
            existing = Absence.query.filter_by(
                user_id=user.id,
                absence_date=today
            ).first()
            if not existing:
                absence = Absence(user_id=user.id, absence_date=today, status='pending')
                db.session.add(absence)
                new_absences += 1
        else:
            # Calculate rounds
            rounds = calculate_rounds(user.id, today)
            if rounds < 4:
                existing = InsufficientPatrol.query.filter_by(
                    user_id=user.id,
                    patrol_date=today
                ).first()
                if not existing:
                    insuf = InsufficientPatrol(
                        user_id=user.id,
                        patrol_date=today,
                        required_rounds=4,
                        actual_rounds=rounds,
                        status='pending'
                    )
                    db.session.add(insuf)
                    new_insufficient += 1

    if new_absences or new_insufficient:
        db.session.commit()

    return {
        'new_absences': new_absences,
        'new_insufficient': new_insufficient,
    }
