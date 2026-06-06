"""Seed the database with initial data. Idempotent -- checks before inserting.

This module can be run standalone (`python seed.py`) or called from app.py
which already has an application context pushed.
"""

from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash

from models import db, User, Camera, PatrolRecord, Absence, InsufficientPatrol, CameraFault


def seed():
    """Seed the database. Must be called within a Flask app context."""
    db.create_all()

    # ===== Users (6) =====
    users_data = [
        {'username': 'admin', 'password': 'admin123', 'name': '李管理',
         'role': 'admin', 'area': None, 'phone': '13800000001'},
        {'username': 'supervisor', 'password': 'sup123', 'name': '王主管',
         'role': 'supervisor', 'area': None, 'phone': '13800000002'},
        {'username': 'patrol1', 'password': 'patrol123', 'name': '赵巡更',
         'role': 'patrol', 'area': 'A区', 'phone': '13800000003'},
        {'username': 'patrol2', 'password': 'patrol123', 'name': '钱巡更',
         'role': 'patrol', 'area': 'B区', 'phone': '13800000004'},
        {'username': 'patrol3', 'password': 'patrol123', 'name': '孙巡更',
         'role': 'patrol', 'area': 'C区', 'phone': '13800000005'},
        {'username': 'patrol4', 'password': 'patrol123', 'name': '李巡更',
         'role': 'patrol', 'area': 'A区', 'phone': '13800000006'},
    ]

    user_map = {}
    for u_data in users_data:
        existing = User.query.filter_by(username=u_data['username']).first()
        if not existing:
            user = User(
                username=u_data['username'],
                password_hash=generate_password_hash(u_data['password']),
                name=u_data['name'],
                role=u_data['role'],
                area=u_data['area'],
                phone=u_data['phone'],
            )
            db.session.add(user)
            db.session.flush()
            user_map[u_data['username']] = user
            print(f"  Created user: {u_data['username']} ({u_data['name']})")
        else:
            user_map[u_data['username']] = existing
            print(f"  User exists: {u_data['username']}")

    db.session.commit()

    # ===== Cameras (12, 4 per area) =====
    cameras_data = [
        {'camera_id': 'Cam-A01', 'location': '北门入口', 'area': 'A区',
         'ip_address': '192.168.1.101', 'status': 'normal'},
        {'camera_id': 'Cam-A02', 'location': '1号楼前', 'area': 'A区',
         'ip_address': '192.168.1.102', 'status': 'normal'},
        {'camera_id': 'Cam-A03', 'location': '2号楼前', 'area': 'A区',
         'ip_address': '192.168.1.103', 'status': 'normal'},
        {'camera_id': 'Cam-A04', 'location': '停车场A', 'area': 'A区',
         'ip_address': '192.168.1.104', 'status': 'normal'},
        {'camera_id': 'Cam-B01', 'location': '中心花园', 'area': 'B区',
         'ip_address': '192.168.2.101', 'status': 'normal'},
        {'camera_id': 'Cam-B02', 'location': '3号楼前', 'area': 'B区',
         'ip_address': '192.168.2.102', 'status': 'normal'},
        {'camera_id': 'Cam-B03', 'location': '4号楼前', 'area': 'B区',
         'ip_address': '192.168.2.103', 'status': 'fault'},
        {'camera_id': 'Cam-B04', 'location': '健身区', 'area': 'B区',
         'ip_address': '192.168.2.104', 'status': 'normal'},
        {'camera_id': 'Cam-C01', 'location': '南门入口', 'area': 'C区',
         'ip_address': '192.168.3.101', 'status': 'normal'},
        {'camera_id': 'Cam-C02', 'location': '5号楼前', 'area': 'C区',
         'ip_address': '192.168.3.102', 'status': 'normal'},
        {'camera_id': 'Cam-C03', 'location': '6号楼前', 'area': 'C区',
         'ip_address': '192.168.3.103', 'status': 'normal'},
        {'camera_id': 'Cam-C04', 'location': '停车场C', 'area': 'C区',
         'ip_address': '192.168.3.104', 'status': 'normal'},
    ]

    camera_map = {}
    for c_data in cameras_data:
        existing = Camera.query.filter_by(camera_id=c_data['camera_id']).first()
        if not existing:
            cam = Camera(**c_data)
            db.session.add(cam)
            db.session.flush()
            camera_map[c_data['camera_id']] = cam
            print(f"  Created camera: {c_data['camera_id']} ({c_data['location']})")
        else:
            camera_map[c_data['camera_id']] = existing
            print(f"  Camera exists: {c_data['camera_id']}")

    db.session.commit()

    # ===== Sample Patrol Records (patrol1, yesterday) =====
    yesterday = date.today() - timedelta(days=1)
    patrol1 = user_map['patrol1']
    a_cameras = [camera_map[cid] for cid in ['Cam-A01', 'Cam-A02', 'Cam-A03', 'Cam-A04']]

    existing_records = PatrolRecord.query.filter_by(
        user_id=patrol1.id, patrol_date=yesterday
    ).count()

    if existing_records == 0:
        for round_num in range(2):
            for cam in a_cameras[:3]:
                record = PatrolRecord(
                    user_id=patrol1.id, camera_id=cam.id,
                    patrol_date=yesterday,
                    capture_time=datetime.utcnow().replace(hour=9 + round_num, minute=0),
                    image_path=None, person_count=3 + round_num
                )
                db.session.add(record)
        # Add one visit to Cam-A04 to make rounds = 1
        record = PatrolRecord(
            user_id=patrol1.id, camera_id=a_cameras[3].id,
            patrol_date=yesterday,
            capture_time=datetime.utcnow().replace(hour=10, minute=0),
            image_path=None, person_count=5
        )
        db.session.add(record)
        print(f"  Created sample patrol records for patrol1 on {yesterday} (1 round)")

    db.session.commit()

    # ===== Sample Absences =====
    patrol2 = user_map['patrol2']
    two_days_ago = date.today() - timedelta(days=2)

    existing_absence = Absence.query.filter_by(
        user_id=patrol2.id, absence_date=two_days_ago
    ).first()
    if not existing_absence:
        absence = Absence(user_id=patrol2.id, absence_date=two_days_ago,
                          status='pending', comment='')
        db.session.add(absence)
        print(f"  Created absence: patrol2 on {two_days_ago}")

    # ===== Sample Insufficient Patrol =====
    patrol3 = user_map['patrol3']
    existing_insuf = InsufficientPatrol.query.filter_by(
        user_id=patrol3.id, patrol_date=yesterday
    ).first()
    if not existing_insuf:
        insuf = InsufficientPatrol(user_id=patrol3.id, patrol_date=yesterday,
                                   required_rounds=4, actual_rounds=3,
                                   status='pending', comment='')
        db.session.add(insuf)
        print(f"  Created insufficient patrol: patrol3 on {yesterday}")

    # ===== Sample Camera Fault =====
    existing_fault = CameraFault.query.filter_by(
        camera_id=camera_map['Cam-B03'].id, status='pending'
    ).first()
    if not existing_fault:
        fault = CameraFault(
            camera_id=camera_map['Cam-B03'].id,
            reported_by=user_map['patrol2'].id,
            fault_time=datetime.utcnow().replace(hour=9, minute=0) - timedelta(days=1),
            description='画面模糊，无法识别人员',
            status='pending'
        )
        db.session.add(fault)
        print(f"  Created camera fault: Cam-B03")

    db.session.commit()
    print("\n[OK] Database seeded successfully!")
    print(f"   Users: {User.query.count()}")
    print(f"   Cameras: {Camera.query.count()}")
    print(f"   Patrol Records: {PatrolRecord.query.count()}")
    print(f"   Absences: {Absence.query.count()}")
    print(f"   Insufficient Patrols: {InsufficientPatrol.query.count()}")
    print(f"   Camera Faults: {CameraFault.query.count()}")


if __name__ == '__main__':
    # When run standalone, create the app context manually
    from app import create_app
    app = create_app()
    with app.app_context():
        seed()
