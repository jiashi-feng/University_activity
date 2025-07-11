from flask import Blueprint, render_template, session, redirect, url_for, flash
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'teacher' or not session.get('is_admin'):
            flash('需要管理员权限', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """管理员首页"""
    admin_info = {
        'name': session.get('username'),
        'college': session.get('college')
    }
    return render_template('admin/dashboard.html', admin_info=admin_info)

@admin_bp.route('/seasons')
@admin_required
def seasons():
    """季度管理页面"""
    admin_info = {
        'name': session.get('username'),
        'college': session.get('college')
    }
    return render_template('admin/seasons.html', admin_info=admin_info)

@admin_bp.route('/venues')
@admin_required
def venues():
    """场地管理页面"""
    admin_info = {
        'name': session.get('username'),
        'college': session.get('college')
    }
    return render_template('admin/venues.html', admin_info=admin_info)

@admin_bp.route('/activities')
@admin_required
def activities():
    """活动审批页面"""
    admin_info = {
        'name': session.get('username'),
        'college': session.get('college')
    }
    return render_template('admin/activities.html', admin_info=admin_info)

@admin_bp.route('/statistics')
@admin_required
def statistics():
    """数据统计页面"""
    admin_info = {
        'name': session.get('username'),
        'college': session.get('college')
    }
    return render_template('admin/statistics.html', admin_info=admin_info)

@admin_bp.route('/profile')
@admin_required
def profile():
    """个人中心页面"""
    admin_info = {
        'name': session.get('username'),
        'college': session.get('college')
    }
    return render_template('admin/profile.html', admin_info=admin_info) 