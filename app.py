from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
from datetime import datetime, timedelta
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 生产环境请使用更安全的密钥

# 数据库文件路径
DATABASE = 'University_activit.db'

# 数据库连接封装
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # 使查询结果可以像字典一样访问
    return conn

def init_db():
    """初始化数据库"""
    if not os.path.exists(DATABASE):
        # 如果数据库不存在，运行初始化脚本
        from init_db import init_database
        init_database()
        print("数据库已初始化")

# 装饰器：登录验证
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 装饰器：角色验证
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_type' not in session or session['user_type'] != role:
                flash('权限不足', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 装饰器：管理员验证
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'teacher':
            flash('权限不足', 'error')
            return redirect(url_for('login'))
        
        # 检查是否为管理员
        db = get_db()
        teacher = db.execute(
            'SELECT is_admin FROM teachers WHERE teacher_id = ?',
            (session['user_id'],)
        ).fetchone()
        db.close()
        
        if not teacher or not teacher['is_admin']:
            flash('需要管理员权限', 'error')
            return redirect(url_for('teacher_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# 首页路由
@app.route('/')
def index():
    """首页，根据登录状态重定向"""
    if 'user_id' in session:
        user_type = session.get('user_type')
        if user_type == 'student':
            return redirect(url_for('student_dashboard'))
        elif user_type == 'teacher':
            return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('login'))

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('login.html')
        
        db = get_db()
        try:
            # 查询用户信息
            user = db.execute(
                'SELECT * FROM users WHERE name = ? AND password = ?',
                (username, password)
            ).fetchone()
            
            if user:
                # 登录成功，设置session
                session['user_id'] = user['user_id']
                session['user_type'] = user['user_type']
                session['username'] = user['name']
                session['college'] = user['college']
                
                # 根据用户类型重定向
                if user['user_type'] == 'student':
                    return redirect(url_for('student_dashboard'))
                elif user['user_type'] == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
            else:
                flash('用户名或密码错误', 'error')
        
        except Exception as e:
            flash(f'登录失败：{str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('login.html')

# 登出路由
@app.route('/logout')
def logout():
    """用户登出"""
    session.clear()
    flash('已成功登出', 'success')
    return redirect(url_for('login'))

# ==================== 学生(参与者)路由 ====================

@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    """学生主页 - 显示可报名活动列表"""
    db = get_db()
    try:
        # 获取学生信息
        student_info = db.execute('''
            SELECT s.*, u.name, u.college 
            FROM students s
            JOIN users u ON s.student_id = u.user_id
            WHERE s.student_id = ?
        ''', (session['user_id'],)).fetchone()
        
        # 获取学生特长
        student_skills = db.execute('''
            SELECT skill_name, skill_level 
            FROM student_skills 
            WHERE student_id = ?
        ''', (session['user_id'],)).fetchall()
        
        # 获取可报名的活动（状态为已批准且未过期）
        available_activities = db.execute('''
            SELECT a.*, u.name as organizer_name, t.name as supervisor_name
            FROM activities a
            JOIN users u ON a.organizer_id = u.user_id
            LEFT JOIN users t ON a.supervisor_id = t.user_id
            WHERE a.status = 'approved' 
            AND a.start_time > datetime('now')
            AND a.participant_count < a.max_participants
            ORDER BY a.start_time
        ''').fetchall()
        
        # 获取已报名的活动
        my_activities = db.execute('''
            SELECT a.*, ap.status as participation_status, u.name as organizer_name
            FROM activities a
            JOIN activity_participants ap ON a.activity_id = ap.activity_id
            JOIN users u ON a.organizer_id = u.user_id
            WHERE ap.student_id = ?
            ORDER BY a.start_time DESC
        ''', (session['user_id'],)).fetchall()
        
        return render_template('student/dashboard.html', 
                             student_info=student_info,
                             student_skills=student_skills,
                             available_activities=available_activities,
                             my_activities=my_activities)
    
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('student/dashboard.html', 
                             student_info=None,
                             student_skills=[],
                             available_activities=[],
                             my_activities=[])
    finally:
        db.close()

@app.route('/student/apply_activity/<int:activity_id>', methods=['POST'])
@login_required
@role_required('student')
def apply_activity(activity_id):
    """学生报名活动"""
    db = get_db()
    try:
        # 检查活动是否存在且可报名
        activity = db.execute('''
            SELECT * FROM activities 
            WHERE activity_id = ? AND status = 'approved' 
            AND start_time > datetime('now')
            AND participant_count < max_participants
        ''', (activity_id,)).fetchone()
        
        if not activity:
            flash('活动不存在或无法报名', 'error')
            return redirect(url_for('student_dashboard'))
        
        # 检查是否已经报名
        existing = db.execute('''
            SELECT * FROM activity_participants 
            WHERE activity_id = ? AND student_id = ?
        ''', (activity_id, session['user_id'])).fetchone()
        
        if existing:
            flash('您已经报名过此活动', 'warning')
            return redirect(url_for('student_dashboard'))
        
        # 插入报名记录
        db.execute('''
            INSERT INTO activity_participants (activity_id, student_id, status)
            VALUES (?, ?, 'applied')
        ''', (activity_id, session['user_id']))
        
        # 更新活动参与人数
        db.execute('''
            UPDATE activities 
            SET participant_count = participant_count + 1
            WHERE activity_id = ?
        ''', (activity_id,))
        
        db.commit()
        flash('报名成功！', 'success')
        
    except Exception as e:
        db.rollback()
        flash(f'报名失败：{str(e)}', 'error')
    finally:
        db.close()
    
    return redirect(url_for('student_dashboard'))

@app.route('/student/organizer')
@login_required
@role_required('student')
def student_organizer():
    """学生组织者功能页面"""
    db = get_db()
    try:
        # 获取我组织的活动
        my_organized_activities = db.execute('''
            SELECT a.*, u.name as supervisor_name
            FROM activities a
            LEFT JOIN users u ON a.supervisor_id = u.user_id
            WHERE a.organizer_id = ?
            ORDER BY a.created_at DESC
        ''', (session['user_id'],)).fetchall()
        
        return render_template('student/organizer.html',
                             my_organized_activities=my_organized_activities)
    
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('student/organizer.html',
                             my_organized_activities=[])
    finally:
        db.close()

@app.route('/student/organizer_activities')
@login_required
@role_required('student')
def organizer_activities():
    """我组织的活动页面"""
    db = get_db()
    try:
        activities = db.execute('''
            SELECT * FROM activities
            WHERE organizer_id = ?
            ORDER BY start_time DESC
        ''', (session['user_id'],)).fetchall()
        now = datetime.now()
        ongoing = []
        ended = []
        for act in activities:
            end_time = act['end_time']
            # 兼容字符串和datetime类型
            if isinstance(end_time, str):
                try:
                    end_time_dt = datetime.fromisoformat(end_time)
                except Exception:
                    end_time_dt = now
            else:
                end_time_dt = end_time
            if end_time_dt > now:
                ongoing.append(act)
            else:
                ended.append(act)
    finally:
        db.close()
    return render_template('student/organizer_activities.html', ongoing=ongoing, ended=ended)

@app.route('/student/create_activity', methods=['GET', 'POST'])
@login_required
@role_required('student')
def create_activity():
    """创建活动"""
    if request.method == 'POST':
        db = get_db()
        try:
            # 获取表单数据
            activity_name = request.form.get('activity_name')
            description = request.form.get('description')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            required_skills = request.form.get('required_skills')
            max_participants = int(request.form.get('max_participants', 0))
            applied_funds = float(request.form.get('applied_funds', 0))
            activity_type = request.form.get('activity_type')
            
            # 插入活动记录
            db.execute('''
                INSERT INTO activities (
                    organizer_id, activity_name, description, start_time, end_time,
                    required_skills, max_participants, applied_funds, activity_type, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review')
            ''', (session['user_id'], activity_name, description, start_time, end_time,
                  required_skills, max_participants, applied_funds, activity_type))
            
            db.commit()
            flash('活动创建成功，等待审核！', 'success')
            return redirect(url_for('student_organizer'))
            
        except Exception as e:
            db.rollback()
            flash(f'创建活动失败：{str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('student/create_activity.html')

@app.route('/student/apply', methods=['GET'])
@login_required
@role_required('student')
def student_apply():
    """学生活动申请页面，技能选项从数据库获取"""
    db = get_db()
    try:
        skills = db.execute('SELECT DISTINCT skill_name FROM student_skills').fetchall()
        skill_options = [row['skill_name'] for row in skills]
    finally:
        db.close()
    return render_template('student/activity_apply.html', skill_options=skill_options)

# ==================== 教师路由 ====================

@app.route('/teacher/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    """教师主页"""
    db = get_db()
    try:
        # 获取教师信息
        teacher_info = db.execute('''
            SELECT t.*, u.name, u.college 
            FROM teachers t
            JOIN users u ON t.teacher_id = u.user_id
            WHERE t.teacher_id = ?
        ''', (session['user_id'],)).fetchone()
        
        # 获取我指导的活动
        supervised_activities = db.execute('''
            SELECT a.*, u.name as organizer_name
            FROM activities a
            JOIN users u ON a.organizer_id = u.user_id
            WHERE a.supervisor_id = ?
            ORDER BY a.created_at DESC
        ''', (session['user_id'],)).fetchall()
        
        # 如果是管理员，获取待审核的活动
        pending_activities = []
        if teacher_info and teacher_info['is_admin']:
            pending_activities = db.execute('''
                SELECT a.*, u.name as organizer_name
                FROM activities a
                JOIN users u ON a.organizer_id = u.user_id
                WHERE a.status = 'pending_review'
                ORDER BY a.created_at DESC
            ''').fetchall()
        
        return render_template('teacher/dashboard.html',
                             teacher_info=teacher_info,
                             supervised_activities=supervised_activities,
                             pending_activities=pending_activities)
    
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('teacher/dashboard.html',
                             teacher_info=None,
                             supervised_activities=[],
                             pending_activities=[])
    finally:
        db.close()

@app.route('/teacher/approve_activity/<int:activity_id>', methods=['POST'])
@login_required
@admin_required
def approve_activity(activity_id):
    """管理员审批活动"""
    db = get_db()
    try:
        action = request.form.get('action')
        allocated_funds = float(request.form.get('allocated_funds', 0))
        
        if action == 'approve':
            # 批准活动
            db.execute('''
                UPDATE activities 
                SET status = 'approved', admin_id = ?, allocated_funds = ?, remaining_funds = ?
                WHERE activity_id = ?
            ''', (session['user_id'], allocated_funds, allocated_funds, activity_id))
            flash('活动已批准', 'success')
        
        elif action == 'reject':
            # 拒绝活动
            db.execute('''
                UPDATE activities 
                SET status = 'cancelled', admin_id = ?
                WHERE activity_id = ?
            ''', (session['user_id'], activity_id))
            flash('活动已拒绝', 'info')
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        flash(f'操作失败：{str(e)}', 'error')
    finally:
        db.close()
    
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/funding')
@login_required
@role_required('teacher')
def teacher_funding():
    """教师资金拨款界面"""
    db = get_db()
    try:
        # 获取我指导的活动的资金信息
        funding_activities = db.execute('''
            SELECT a.*, u.name as organizer_name
            FROM activities a
            JOIN users u ON a.organizer_id = u.user_id
            WHERE a.supervisor_id = ? AND a.status = 'approved'
            ORDER BY a.start_time DESC
        ''', (session['user_id'],)).fetchall()
        
        return render_template('teacher/funding.html',
                             funding_activities=funding_activities)
    
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('teacher/funding.html',
                             funding_activities=[])
    finally:
        db.close()

# ==================== 管理员路由 ====================

@app.route('/admin/venues')
@login_required
@admin_required
def admin_venues():
    """管理员场地管理"""
    db = get_db()
    try:
        # 获取所有场地信息
        venues = db.execute('SELECT * FROM venues ORDER BY venue_name').fetchall()
        
        # 获取场地预约信息
        venue_bookings = db.execute('''
            SELECT vb.*, v.venue_name, a.activity_name, u.name as organizer_name
            FROM venue_bookings vb
            JOIN venues v ON vb.venue_id = v.venue_id
            JOIN activities a ON vb.activity_id = a.activity_id
            JOIN users u ON vb.organizer_id = u.user_id
            ORDER BY vb.start_time DESC
        ''').fetchall()
        
        return render_template('admin/venues.html',
                             venues=venues,
                             venue_bookings=venue_bookings)
    
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('admin/venues.html',
                             venues=[],
                             venue_bookings=[])
    finally:
        db.close()

# ==================== API路由 ====================

@app.route('/api/activities')
@login_required
def api_activities():
    """API: 获取活动列表"""
    db = get_db()
    try:
        activities = db.execute('''
            SELECT a.*, u.name as organizer_name
            FROM activities a
            JOIN users u ON a.organizer_id = u.user_id
            WHERE a.status = 'approved'
            ORDER BY a.start_time
        ''').fetchall()
        
        return jsonify([dict(activity) for activity in activities])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return render_template('errors/500.html'), 500

# ==================== 应用启动 ====================

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动Flask应用
    app.run(debug=True, host='0.0.0.0', port=5000)