from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from functools import wraps
import sqlite3
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'teacher' or not session.get('is_admin'):
            flash('需要管理员权限', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    conn = sqlite3.connect('University_activit.db')
    conn.row_factory = sqlite3.Row
    return conn

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """管理员首页"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取管理员信息
        cursor.execute('''
            SELECT u.name, u.college, u.phone, t.employee_number, t.position
            FROM users u
            JOIN teachers t ON u.user_id = t.teacher_id
            WHERE u.user_id = ? AND t.is_admin = 1
        ''', (session.get('user_id'),))
        
        admin_data = cursor.fetchone()
        if not admin_data:
            flash('未找到管理员信息', 'error')
            return redirect(url_for('login'))
            
        admin_info = {
            'name': admin_data['name'],
            'college': admin_data['college'],
            'employee_number': admin_data['employee_number'],
            'position': admin_data['position']
        }
        
        # 获取场地使用情况
        now = datetime.now()
        cursor.execute('''
            SELECT v.*,
                   CASE 
                       WHEN EXISTS (
                           SELECT 1 FROM venue_bookings vb
                           WHERE vb.venue_id = v.venue_id
                           AND vb.booking_status = 'approved'
                           AND ? BETWEEN vb.start_time AND vb.end_time
                       ) THEN '使用中'
                       WHEN v.status = 'maintenance' THEN '维护中'
                       WHEN v.status = 'unavailable' THEN '不可用'
                       ELSE '空闲'
                   END as current_status,
                   COALESCE(
                       (SELECT MIN(vb.end_time)
                        FROM venue_bookings vb
                        WHERE vb.venue_id = v.venue_id
                        AND vb.booking_status = 'approved'
                        AND vb.start_time > ?
                        ), '当前可用'
                   ) as next_available
            FROM venues v
            ORDER BY v.venue_name
            LIMIT 3
        ''', (now.isoformat(), now.isoformat()))
        
        venues = [dict(row) for row in cursor.fetchall()]
        
        # 获取待审批活动
        cursor.execute('''
            SELECT 
                a.activity_id,
                a.activity_name,
                vb.created_at as applied_at,
                v.venue_name,
                u.name as organizer_name,
                a.max_participants,
                vb.booking_id
            FROM activities a
            JOIN venue_bookings vb ON a.activity_id = vb.activity_id
            JOIN venues v ON vb.venue_id = v.venue_id
            JOIN users u ON a.organizer_id = u.user_id
            WHERE vb.booking_status = 'pending'
            AND a.start_time > datetime('now')
            ORDER BY vb.created_at DESC
            LIMIT 2
        ''')
        
        pending_activities = []
        for row in cursor.fetchall():
            activity = dict(row)
            applied_at = datetime.fromisoformat(activity['applied_at'])
            now = datetime.now()
            diff = now - applied_at
            
            if diff.days > 0:
                time_ago = f"{diff.days}天前"
            elif diff.seconds >= 3600:
                hours = diff.seconds // 3600
                time_ago = f"{hours}小时前"
            elif diff.seconds >= 60:
                minutes = diff.seconds // 60
                time_ago = f"{minutes}分钟前"
            else:
                time_ago = "刚刚"
                
            activity['time_ago'] = time_ago
            pending_activities.append(activity)
        
        return render_template('admin/dashboard.html',
                             admin_info=admin_info,
                             venues=venues,
                             pending_activities=pending_activities)
    finally:
        conn.close()

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
    # 获取管理员信息
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取管理员基本信息
    cursor.execute('''
        SELECT u.name, u.college, u.phone, t.employee_number, t.position
        FROM users u
        JOIN teachers t ON u.user_id = t.teacher_id
        WHERE u.user_id = ? AND t.is_admin = 1
    ''', (session.get('user_id'),))
    
    admin_data = cursor.fetchone()
    
    if not admin_data:
        conn.close()
        flash('未找到管理员信息', 'error')
        return redirect(url_for('admin.dashboard'))
    
    admin_info = {
        'name': admin_data['name'],
        'college': admin_data['college'],
        'phone': admin_data['phone'],
        'employee_number': admin_data['employee_number'],
        'position': admin_data['position']
    }
    
    # 获取最近审批的活动
    cursor.execute('''
        SELECT 
            activity_name,
            created_at,
            status,
            CASE 
                WHEN status = 'approved' THEN created_at
                ELSE NULL 
            END as approved_at
        FROM activities
        WHERE admin_id = ?
        ORDER BY created_at DESC
        LIMIT 5
    ''', (session.get('user_id'),))
    
    recent_activities = cursor.fetchall()
    conn.close()
    
    return render_template('admin/profile.html', 
                         admin_info=admin_info,
                         recent_activities=recent_activities)

@admin_bp.route('/update_password', methods=['POST'])
@admin_required
def update_password():
    """更新管理员密码"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 验证当前密码
    cursor.execute('SELECT password FROM users WHERE user_id = ?', 
                  (session.get('user_id'),))
    user = cursor.fetchone()
    
    if not user or user['password'] != current_password:
        conn.close()
        flash('当前密码错误', 'error')
        return redirect(url_for('admin.profile'))
    
    # 更新密码
    cursor.execute('UPDATE users SET password = ? WHERE user_id = ?',
                  (new_password, session.get('user_id')))
    
    conn.commit()
    conn.close()
    
    flash('密码修改成功', 'success')
    return redirect(url_for('admin.profile'))