from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
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

@admin_bp.route('/api/seasons/current', methods=['PUT'])
@admin_required
def update_current_season():
    """更新当前季度信息"""
    data = request.get_json()
    # 这里应该添加数据库操作，现在使用模拟数据
    response = {
        'status': 'success',
        'message': '季度信息已更新',
        'data': {
            'season_name': data.get('season_name'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date')
        }
    }
    return jsonify(response)

@admin_bp.route('/api/seasons/current/end', methods=['POST'])
@admin_required
def end_current_season():
    """提前结束当前季度"""
    # 这里应该添加数据库操作，现在使用模拟数据
    response = {
        'status': 'success',
        'message': '当前季度已结束'
    }
    return jsonify(response)

@admin_bp.route('/api/seasons/next', methods=['POST'])
@admin_required
def switch_to_next_season():
    """切换到下一季度"""
    data = request.get_json()
    # 这里应该添加数据库操作，现在使用模拟数据
    response = {
        'status': 'success',
        'message': '已切换到下一季度',
        'data': {
            'season_name': data.get('next_season_name'),
            'start_date': data.get('next_start_date'),
            'end_date': data.get('next_end_date')
        }
    }
    return jsonify(response)

@admin_bp.route('/activities')
@admin_required
def activities():
    """活动审批页面"""
    admin_info = {
        'name': session.get('username'),
        'college': session.get('college')
    }
    return render_template('admin/activities.html', admin_info=admin_info)

@admin_bp.route('/profile')
@admin_required
def profile():
    """个人中心页面"""
    admin_info = {
        'name': session.get('username'),
        'college': session.get('college')
    }
    return render_template('admin/profile.html', admin_info=admin_info) 