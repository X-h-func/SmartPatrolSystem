from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='patrol')  # admin, supervisor, patrol
    area = db.Column(db.String(32), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patrol_records = db.relationship('PatrolRecord', backref='user', lazy='dynamic')
    absences = db.relationship('Absence', backref='user', lazy='dynamic',
                               foreign_keys='Absence.user_id')
    insufficient_patrols = db.relationship('InsufficientPatrol', backref='user', lazy='dynamic',
                                           foreign_keys='InsufficientPatrol.user_id')

    def __repr__(self):
        return f'<User {self.username} - {self.name}>'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_supervisor(self):
        return self.role == 'supervisor'

    @property
    def is_patrol(self):
        return self.role == 'patrol'


class Camera(db.Model):
    __tablename__ = 'cameras'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    camera_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    location = db.Column(db.String(128), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='normal')  # normal, fault
    area = db.Column(db.String(32), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patrol_records = db.relationship('PatrolRecord', backref='camera', lazy='dynamic')
    faults = db.relationship('CameraFault', backref='camera', lazy='dynamic')

    def __repr__(self):
        return f'<Camera {self.camera_id} - {self.location}>'


class PatrolRecord(db.Model):
    __tablename__ = 'patrol_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=False)
    patrol_date = db.Column(db.Date, nullable=False, default=date.today)
    capture_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_path = db.Column(db.String(256), nullable=True)
    person_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_user_date_camera', 'user_id', 'patrol_date', 'camera_id'),
    )

    def __repr__(self):
        return f'<PatrolRecord User:{self.user_id} Cam:{self.camera_id} Date:{self.patrol_date}>'


class Absence(db.Model):
    __tablename__ = 'absences'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    absence_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    comment = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Reviewer relationship
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'absence_date', name='uq_user_absence_date'),
    )

    def __repr__(self):
        return f'<Absence User:{self.user_id} Date:{self.absence_date} Status:{self.status}>'


class InsufficientPatrol(db.Model):
    __tablename__ = 'insufficient_patrols'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patrol_date = db.Column(db.Date, nullable=False)
    required_rounds = db.Column(db.Integer, nullable=False, default=4)
    actual_rounds = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, confirmed
    comment = db.Column(db.Text, nullable=True)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Confirmer relationship
    confirmer = db.relationship('User', foreign_keys=[confirmed_by])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'patrol_date', name='uq_user_insufficient_date'),
    )

    def __repr__(self):
        return f'<InsufficientPatrol User:{self.user_id} Date:{self.patrol_date} Rounds:{self.actual_rounds}/{self.required_rounds}>'


class CameraFault(db.Model):
    __tablename__ = 'camera_faults'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fault_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, confirmed, resolved
    resolution = db.Column(db.Text, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reporter = db.relationship('User', foreign_keys=[reported_by])
    resolver = db.relationship('User', foreign_keys=[resolved_by])

    def __repr__(self):
        return f'<CameraFault Cam:{self.camera_id} Status:{self.status}>'
