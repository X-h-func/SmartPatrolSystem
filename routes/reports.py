from datetime import date, datetime, timedelta
from collections import defaultdict

from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
import csv
import io

from models import db, User, PatrolRecord, Absence, InsufficientPatrol, CameraFault
from decorators import role_required

reports_bp = Blueprint('reports', __name__)


def get_week_range():
    """Get start and end of current ISO week (Monday-Sunday)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_month_range():
    """Get start and end of current month."""
    today = date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return first_day, last_day


def aggregate_stats(start_date, end_date):
    """Aggregate patrol statistics for a date range."""
    patrol_users = User.query.filter_by(role='patrol').all()

    total_absences = Absence.query.filter(
        Absence.absence_date >= start_date,
        Absence.absence_date <= end_date
    ).count()

    approved_absences = Absence.query.filter(
        Absence.absence_date >= start_date,
        Absence.absence_date <= end_date,
        Absence.status == 'approved'
    ).count()

    rejected_absences = Absence.query.filter(
        Absence.absence_date >= start_date,
        Absence.absence_date <= end_date,
        Absence.status == 'rejected'
    ).count()

    insufficient_count = InsufficientPatrol.query.filter(
        InsufficientPatrol.patrol_date >= start_date,
        InsufficientPatrol.patrol_date <= end_date
    ).count()

    camera_faults_count = CameraFault.query.filter(
        CameraFault.fault_time >= start_date,
        CameraFault.fault_time <= end_date
    ).count()

    # Per-user stats
    user_stats = []
    for u in patrol_users:
        records = PatrolRecord.query.filter(
            PatrolRecord.user_id == u.id,
            PatrolRecord.patrol_date >= start_date,
            PatrolRecord.patrol_date <= end_date
        ).count()
        abs_count = Absence.query.filter(
            Absence.user_id == u.id,
            Absence.absence_date >= start_date,
            Absence.absence_date <= end_date
        ).count()
        insuf_count = InsufficientPatrol.query.filter(
            InsufficientPatrol.user_id == u.id,
            InsufficientPatrol.patrol_date >= start_date,
            InsufficientPatrol.patrol_date <= end_date
        ).count()
        user_stats.append({
            'name': u.name,
            'area': u.area or '-',
            'records': records,
            'absences': abs_count,
            'insufficient': insuf_count,
        })

    # Daily breakdown for chart
    daily_data = []
    current = start_date
    while current <= end_date:
        day_records = PatrolRecord.query.filter_by(patrol_date=current).count()
        day_absences = Absence.query.filter_by(absence_date=current).count()
        daily_data.append({
            'date': current.isoformat(),
            'records': day_records,
            'absences': day_absences,
        })
        current += timedelta(days=1)

    return {
        'total_absences': total_absences,
        'approved_absences': approved_absences,
        'rejected_absences': rejected_absences,
        'insufficient_count': insufficient_count,
        'camera_faults_count': camera_faults_count,
        'user_stats': user_stats,
        'daily_data': daily_data,
        'total_users': len(patrol_users),
    }


@reports_bp.route('/reports/weekly')
@login_required
@role_required('admin', 'supervisor')
def weekly():
    start, end = get_week_range()
    stats = aggregate_stats(start, end)
    # Average completion rate
    total_possible = stats['total_users'] * 7  # days * users
    total_absent = stats['total_absences']
    completion_rate = round((1 - total_absent / max(total_possible, 1)) * 100)
    return render_template('reports.html',
                           report_type='weekly',
                           start_date=start,
                           end_date=end,
                           stats=stats,
                           completion_rate=completion_rate)


@reports_bp.route('/reports/monthly')
@login_required
@role_required('admin', 'supervisor')
def monthly():
    start, end = get_month_range()
    stats = aggregate_stats(start, end)
    total_days = (end - start).days + 1
    total_possible = stats['total_users'] * total_days
    total_absent = stats['total_absences']
    completion_rate = round((1 - total_absent / max(total_possible, 1)) * 100)
    return render_template('reports.html',
                           report_type='monthly',
                           start_date=start,
                           end_date=end,
                           stats=stats,
                           completion_rate=completion_rate)


@reports_bp.route('/reports/export/<report_type>')
@login_required
@role_required('admin', 'supervisor')
def export_report(report_type):
    """Export report as CSV."""
    if report_type == 'weekly':
        start, end = get_week_range()
    else:
        start, end = get_month_range()

    stats = aggregate_stats(start, end)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['智能巡更系统 - 报表导出'])
    writer.writerow([f'报表类型: {report_type}', f'时间范围: {start} ~ {end}'])
    writer.writerow([])
    writer.writerow(['统计概览'])
    writer.writerow(['总缺勤次数', stats['total_absences']])
    writer.writerow(['已审批缺勤', stats['approved_absences']])
    writer.writerow(['已驳回缺勤', stats['rejected_absences']])
    writer.writerow(['巡更不足次数', stats['insufficient_count']])
    writer.writerow(['摄像头故障次数', stats['camera_faults_count']])
    writer.writerow([])
    writer.writerow(['人员详情'])
    writer.writerow(['姓名', '区域', '巡更记录数', '缺勤次数', '巡更不足次数'])
    for us in stats['user_stats']:
        writer.writerow([us['name'], us['area'], us['records'], us['absences'], us['insufficient']])

    output.seek(0)
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=patrol_report_{report_type}_{start}_{end}.csv'}
    )
