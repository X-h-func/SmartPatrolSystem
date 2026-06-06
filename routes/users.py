from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from models import db, User
from decorators import role_required

users_bp = Blueprint('users', __name__)


@users_bp.route('/users')
@login_required
@role_required('admin')
def index():
    users = User.query.order_by(User.role, User.username).all()
    return render_template('users.html', users=users)


@users_bp.route('/users/add', methods=['POST'])
@login_required
@role_required('admin')
def add():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'patrol')
    area = request.form.get('area', '').strip()
    phone = request.form.get('phone', '').strip()

    if not username or not password or not name:
        flash('用户名、密码和姓名为必填项', 'danger')
        return redirect(url_for('users.index'))

    if User.query.filter_by(username=username).first():
        flash(f'用户名 {username} 已存在', 'danger')
        return redirect(url_for('users.index'))

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        name=name,
        role=role,
        area=area if role == 'patrol' else None,
        phone=phone
    )
    db.session.add(user)
    db.session.commit()
    flash(f'用户 {name} 已添加', 'success')
    return redirect(url_for('users.index'))


@users_bp.route('/users/<int:id>/edit', methods=['POST'])
@login_required
@role_required('admin')
def edit(id):
    user = User.query.get_or_404(id)
    user.name = request.form.get('name', user.name).strip()
    user.role = request.form.get('role', user.role)
    user.area = request.form.get('area', '').strip() if user.role == 'patrol' else None
    user.phone = request.form.get('phone', user.phone).strip()
    db.session.commit()
    flash(f'用户 {user.name} 已更新', 'success')
    return redirect(url_for('users.index'))


@users_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    if id == current_user.id:
        flash('不能删除自己的账号', 'danger')
        return redirect(url_for('users.index'))

    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash(f'用户 {user.name} 已删除', 'success')
    return redirect(url_for('users.index'))


@users_bp.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
@role_required('admin')
def reset_password(id):
    user = User.query.get_or_404(id)
    new_password = request.form.get('new_password', '123456')
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash(f'用户 {user.name} 的密码已重置', 'success')
    return redirect(url_for('users.index'))
