from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile')
@login_required
def index():
    return render_template('profile.html')


@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update():
    phone = request.form.get('phone', '').strip()
    current_user.phone = phone
    db.session.commit()
    flash('个人信息已更新', 'success')
    return redirect(url_for('profile.index'))


@profile_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not old_password or not new_password or not confirm_password:
        flash('请填写所有密码字段', 'danger')
        return redirect(url_for('profile.index'))

    if not check_password_hash(current_user.password_hash, old_password):
        flash('旧密码不正确', 'danger')
        return redirect(url_for('profile.index'))

    if new_password != confirm_password:
        flash('两次输入的新密码不一致', 'danger')
        return redirect(url_for('profile.index'))

    if len(new_password) < 4:
        flash('新密码长度不能少于4位', 'danger')
        return redirect(url_for('profile.index'))

    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash('密码已成功修改', 'success')
    return redirect(url_for('profile.index'))
