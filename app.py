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
        # 查询我组织的所有活动，包含更多详细信息
        activities = db.execute('''
            SELECT a.*, 
                   t.name as supervisor_name,
                   COUNT(ap.participation_id) as total_applications,
                   SUM(CASE WHEN ap.status = 'approved' THEN 1 ELSE 0 END) as approved_count,
                   SUM(CASE WHEN ap.status = 'applied' THEN 1 ELSE 0 END) as pending_count,
                   vb.booking_status,
                   vb.venue_id,
                   v.venue_name,
                   CASE 
                       WHEN vb.booking_status = 'approved' THEN '已分配'
                       WHEN vb.booking_status = 'pending' THEN '待审核'
                       WHEN vb.booking_status = 'rejected' THEN '已拒绝'
                       ELSE '未申请'
                   END as venue_status
            FROM activities a
            LEFT JOIN users t ON a.supervisor_id = t.user_id
            LEFT JOIN activity_participants ap ON a.activity_id = ap.activity_id
            LEFT JOIN venue_bookings vb ON a.activity_id = vb.activity_id
            LEFT JOIN venues v ON vb.venue_id = v.venue_id
            WHERE a.organizer_id = ?
            GROUP BY a.activity_id
            ORDER BY a.start_time DESC
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

@app.route('/student/score_entry', methods=['GET', 'POST'])
@login_required
@role_required('student')
def score_entry():
    db = get_db()
    if request.method == 'POST':
        total = int(request.form.get('total', 0))
        updated = 0
        for i in range(total):
            score = request.form.get(f'score_{i}')
            activity_id = request.form.get(f'activity_id_{i}')
            student_id = request.form.get(f'student_id_{i}')
            if score is None or activity_id is None or student_id is None:
                continue
            try:
                score = int(score)
                if not (0 <= score <= 5):
                    continue
            except Exception:
                continue
            # 检查是否已有评价，存在则更新，否则插入
            existing = db.execute('''
                SELECT evaluation_id FROM participant_evaluations
                WHERE activity_id = ? AND participant_id = ? AND organizer_id = ?
            ''', (activity_id, student_id, session['user_id'])).fetchone()
            if existing:
                db.execute('''
                    UPDATE participant_evaluations
                    SET rating = ?, created_at = CURRENT_TIMESTAMP
                    WHERE evaluation_id = ?
                ''', (score, existing['evaluation_id']))
            else:
                db.execute('''
                    INSERT INTO participant_evaluations (activity_id, participant_id, organizer_id, rating)
                    VALUES (?, ?, ?, ?)
                ''', (activity_id, student_id, session['user_id'], score))
            updated += 1
        db.commit()
        flash(f'已保存{updated}条成绩', 'success')
    try:
        # 查询我组织的活动及其已批准的参与学生
        scores = db.execute('''
            SELECT a.activity_id, u.name as student_name, u.user_id as student_id,
                   a.activity_name, a.start_time || ' 至 ' || a.end_time as activity_time,
                   s.grade, a.max_participants as participants,
                   ? as input_by,
                   COALESCE(pe.rating, 0) as score
            FROM activities a
            JOIN activity_participants ap ON a.activity_id = ap.activity_id
            JOIN students s ON ap.student_id = s.student_id
            JOIN users u ON s.student_id = u.user_id
            LEFT JOIN participant_evaluations pe 
                ON pe.activity_id = a.activity_id AND pe.participant_id = ap.student_id AND pe.organizer_id = ?
            WHERE a.organizer_id = ? AND ap.status = 'approved'
            ORDER BY a.start_time DESC, u.name
        ''', (session['username'], session['user_id'], session['user_id'])).fetchall()
        return render_template('student/score_entry.html', scores=scores)
    finally:
        db.close()

@app.route('/student/save_score', methods=['POST'])
@login_required
@role_required('student')
def save_score():
    data = request.get_json()
    activity_id = data.get('activity_id')
    student_id = data.get('student_id')
    score = data.get('score')
    if not (activity_id and student_id and score is not None):
        return jsonify({'success': False, 'message': '参数不完整'})
    try:
        score = int(score)
        if not (0 <= score <= 5):
            return jsonify({'success': False, 'message': '成绩必须为0~5'})
    except Exception:
        return jsonify({'success': False, 'message': '成绩格式错误'})
    db = get_db()
    try:
        existing = db.execute('''
            SELECT evaluation_id FROM participant_evaluations
            WHERE activity_id = ? AND participant_id = ? AND organizer_id = ?
        ''', (activity_id, student_id, session['user_id'])).fetchone()
        if existing:
            db.execute('''
                UPDATE participant_evaluations
                SET rating = ?, created_at = CURRENT_TIMESTAMP
                WHERE evaluation_id = ?
            ''', (score, existing['evaluation_id']))
        else:
            db.execute('''
                INSERT INTO participant_evaluations (activity_id, participant_id, organizer_id, rating)
                VALUES (?, ?, ?, ?)
            ''', (activity_id, student_id, session['user_id'], score))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/student/activity_review')
@login_required
@role_required('student')
def activity_review():
    db = get_db()
    try:
        # 从数据库查询活动学生审核数据
        reviews = db.execute('''
            SELECT ap.participation_id, a.activity_name, u.name as student_name, 
                   a.start_time, a.end_time, s.grade, a.max_participants,
                   t.name as teacher_name, ap.status, ap.applied_at
            FROM activity_participants ap
            JOIN activities a ON ap.activity_id = a.activity_id
            JOIN users u ON ap.student_id = u.user_id
            JOIN students s ON ap.student_id = s.student_id
            LEFT JOIN users t ON a.supervisor_id = t.user_id
            WHERE a.organizer_id = ? AND ap.status = 'applied'
            ORDER BY ap.applied_at DESC
        ''', (session['user_id'],)).fetchall()
        
        return render_template('student/activity_review.html', reviews=reviews)
    finally:
        db.close()

@app.route('/student/review_participation/<int:participation_id>', methods=['POST'])
@login_required
@role_required('student')
def review_participation(participation_id):
    action = request.form.get('action')  # 'approve' or 'reject'
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': '无效的操作'})
    
    db = get_db()
    try:
        # 检查权限：只有活动组织者可以审核
        participation = db.execute('''
            SELECT ap.*, a.organizer_id 
            FROM activity_participants ap
            JOIN activities a ON ap.activity_id = a.activity_id
            WHERE ap.participation_id = ?
        ''', (participation_id,)).fetchone()
        
        if not participation:
            return jsonify({'success': False, 'message': '参与记录不存在'})
        
        if participation['organizer_id'] != session['user_id']:
            return jsonify({'success': False, 'message': '无权限审核此申请'})
        
        # 更新审核状态
        new_status = 'approved' if action == 'approve' else 'rejected'
        db.execute('''
            UPDATE activity_participants 
            SET status = ?, approved_at = CURRENT_TIMESTAMP
            WHERE participation_id = ?
        ''', (new_status, participation_id))
        
        # 如果是批准，更新活动参与人数
        if action == 'approve':
            db.execute('''
                UPDATE activities 
                SET participant_count = participant_count + 1
                WHERE activity_id = ?
            ''', (participation['activity_id'],))
        
        db.commit()
        
        return jsonify({'success': True, 'message': f'已{action}'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@app.route('/student/notification')
@login_required
@role_required('student')
def notification():
    db = get_db()
    try:
        # 从数据库查询通知数据
        notifications = db.execute('''
            SELECT n.*, u.name as sender_name
            FROM notifications n
            LEFT JOIN users u ON n.sender_id = u.user_id
            WHERE n.recipient_id = ?
            ORDER BY n.created_at DESC
        ''', (session['user_id'],)).fetchall()
        
        return render_template('student/notification.html', notifications=notifications)
    finally:
        db.close()

@app.route('/student/change_organizer', methods=['GET', 'POST'])
@login_required
@role_required('student')
def change_organizer():
    if request.method == 'GET':
        db = get_db()
        try:
            # 获取当前学生的组织者变更申请
            changes = db.execute('''
                SELECT oc.*, a.activity_name, 
                       u1.name as old_organizer, u2.name as new_organizer
                FROM organizer_changes oc
                JOIN activities a ON oc.activity_id = a.activity_id
                JOIN users u1 ON oc.original_organizer_id = u1.user_id
                JOIN users u2 ON oc.new_organizer_id = u2.user_id
                WHERE oc.original_organizer_id = ?
                ORDER BY oc.requested_at DESC
            ''', (session['user_id'],)).fetchall()
            
            # 获取当前学生组织的活动
            activities = db.execute('''
                SELECT activity_id, activity_name FROM activities 
                WHERE organizer_id = ? AND status = 'approved'
            ''', (session['user_id'],)).fetchall()
            
            # 获取已有待审核变更申请的活动ID
            pending_activities = db.execute('''
                SELECT activity_id FROM organizer_changes 
                WHERE original_organizer_id = ? AND change_status = 'pending'
            ''', (session['user_id'],)).fetchall()
            pending_activity_ids = [row['activity_id'] for row in pending_activities]
            
            # 获取所有学生信息（用于选择新组织者）
            students = db.execute('''
                SELECT s.student_id, s.student_number, u.name, s.major, s.class_name
                FROM students s
                JOIN users u ON s.student_id = u.user_id
                WHERE u.user_type = 'student'
                ORDER BY s.student_number
            ''').fetchall()
            
            return render_template('student/change_organizer.html', 
                                 changes=changes, activities=activities, 
                                 students=students, pending_activity_ids=pending_activity_ids)
        finally:
            db.close()
    
    elif request.method == 'POST':
        activity_id = request.form.get('activity_id')
        new_organizer_id = request.form.get('new_organizer_id')
        reason = request.form.get('reason')
        
        if not all([activity_id, new_organizer_id, reason]):
            return jsonify({'success': False, 'message': '请填写完整信息'})
        
        db = get_db()
        try:
            # 检查新组织者是否存在
            new_organizer = db.execute('SELECT user_id FROM users WHERE user_id = ? AND user_type = "student"', 
                                     (new_organizer_id,)).fetchone()
            if not new_organizer:
                return jsonify({'success': False, 'message': '新组织者不存在'})
            
            # 检查该活动是否已有待审核的变更申请
            existing_change = db.execute('''
                SELECT change_id FROM organizer_changes 
                WHERE activity_id = ? AND original_organizer_id = ? AND change_status = 'pending'
            ''', (activity_id, session['user_id'])).fetchone()
            
            if existing_change:
                return jsonify({'success': False, 'message': '该活动已有待审核的变更申请，请等待审核完成或取消现有申请'})
            
            # 插入变更申请
            db.execute('''
                INSERT INTO organizer_changes (activity_id, original_organizer_id, new_organizer_id, reason)
                VALUES (?, ?, ?, ?)
            ''', (activity_id, session['user_id'], new_organizer_id, reason))
            db.commit()
            
            return jsonify({'success': True, 'message': '申请提交成功'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'message': str(e)})
        finally:
            db.close()

@app.route('/student/cancel_change_request/<int:request_id>', methods=['POST'])
@login_required
@role_required('student')
def cancel_change_request(request_id):
    db = get_db()
    try:
        # 删除申请
        db.execute('DELETE FROM organizer_changes WHERE change_id = ? AND original_organizer_id = ?', 
                  (request_id, session['user_id']))
        db.commit()
        return jsonify({'success': True, 'message': '申请已取消'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

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