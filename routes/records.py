import os
import uuid
from datetime import date, datetime

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db, User, Camera, PatrolRecord
from services.detector import detect_persons, get_detection_method

records_bp = Blueprint('records', __name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@records_bp.route('/records')
@login_required
def index():
    filter_date = request.args.get('date', str(date.today()))
    filter_user = request.args.get('user_id', '')

    query = PatrolRecord.query
    if current_user.is_patrol:
        query = query.filter_by(user_id=current_user.id)
    elif filter_user:
        query = query.filter_by(user_id=int(filter_user))

    if filter_date:
        query = query.filter_by(patrol_date=date.fromisoformat(filter_date))

    records = query.order_by(PatrolRecord.capture_time.desc()).limit(100).all()

    # For the upload form: show cameras in patrol user's area
    if current_user.is_patrol:
        my_cameras = Camera.query.filter_by(area=current_user.area).all()
    else:
        my_cameras = Camera.query.all()

    patrol_users = User.query.filter_by(role='patrol').all()

    return render_template('records.html',
                           records=records,
                           cameras=my_cameras,
                           patrol_users=patrol_users,
                           filter_date=filter_date,
                           filter_user=filter_user)


@records_bp.route('/records/upload', methods=['POST'])
@login_required
def upload():
    """Handle image upload with person detection. All roles can upload for demo."""
    # For non-patrol users, allow upload for demo/testing but with a note
    is_demo = not current_user.is_patrol

    if 'image' not in request.files:
        return jsonify({'success': False, 'error': '请选择图片文件'}), 400

    file = request.files['image']
    camera_id = request.form.get('camera_id', '')

    if not camera_id:
        return jsonify({'success': False, 'error': '请选择摄像头'}), 400

    if file.filename == '':
        return jsonify({'success': False, 'error': '请选择图片文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '仅支持 jpg/png/gif/bmp/webp 格式'}), 400

    # Save file
    ext = file.filename.rsplit('.', 1)[1].lower()
    today_str = date.today().isoformat()
    user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username, today_str)
    os.makedirs(user_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(user_dir, filename)
    file.save(filepath)

    # Relative path for DB storage
    relative_path = os.path.join('uploads', current_user.username, today_str, filename).replace('\\', '/')

    # Run person detection
    person_count = detect_persons(filepath)

    # Create patrol record
    cam = Camera.query.get(int(camera_id))
    record = PatrolRecord(
        user_id=current_user.id,
        camera_id=int(camera_id),
        patrol_date=date.today(),
        capture_time=datetime.utcnow(),
        image_path=relative_path,
        person_count=person_count
    )
    db.session.add(record)
    db.session.commit()

    method = get_detection_method()
    accuracy_note = ''
    if 'HOG' in method:
        accuracy_note = ' | 提示：安装 ultralytics 可大幅提升识别精度，详见 requirements.txt'

    return jsonify({
        'success': True,
        'person_count': person_count,
        'camera': cam.location if cam else '',
        'record_id': record.id,
        'detection_method': method,
        'message': f'上传成功！识别到 {person_count} 人 ({method}){accuracy_note}{" (演示模式)" if is_demo else ""}'
    })
