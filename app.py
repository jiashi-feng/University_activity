from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
import sqlite3
from datetime import datetime, timedelta
import os
from functools import wraps
from teacher.dashboard import bp as teacher_dashboard_bp
from teacher.stats import bp as teacher_stats_bp
from teacher.evaluation import bp as teacher_evaluation_bp
from teacher.account import bp as teacher_account_bp
from teacher.personcenter import bp as teacher_personcenter_bp
from teacher.funding import bp as teacher_funding_bp
from teacher.approval import bp as teacher_approval_bp
from extensions import get_db, init_db, login_required, role_required, admin_required
from admin.routes import admin_bp  # 导入管理员蓝图
from admin.venues import venues_bp
from admin.activity_routes import admin_activity

app = Flask(__name__)
app.secret_key = 'tP6Xe8mZ3vQJyKfBwN2Lc7sD1gH5Yr9VnM4kT0xGpU'  # 添加密钥用于session

# 注册蓝图
app.register_blueprint(admin_bp)  # admin_bp已经有/admin前缀
app.register_blueprint(venues_bp)  # venues_bp已经有/admin前缀
app.register_blueprint(admin_activity, url_prefix='/admin')

# 数据库文件路径
DATABASE = 'University_activit.db'

# 数据库连接封装

# 装饰器：登录验证

# 装饰器：角色验证

# 装饰器：管理员验证
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'teacher' or not session.get('is_admin'):
            flash('需要管理员权限', 'error')
            return redirect(url_for('login'))
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
            return redirect(url_for('teacher_dashboard.dashboard'))
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
                
                # 如果是教师，检查是否为管理员
                if user['user_type'] == 'teacher':
                    teacher = db.execute(
                        'SELECT is_admin FROM teachers WHERE teacher_id = ?',
                        (user['user_id'],)
                    ).fetchone()
                    
                    if teacher and teacher['is_admin']:
                        session['is_admin'] = True
                        return redirect(url_for('admin.dashboard'))  # 使用蓝图的URL
                    else:
                        session['is_admin'] = False
                        return redirect(url_for('teacher_dashboard.dashboard'))
                elif user['user_type'] == 'student':
                    session['is_admin'] = False
                    return redirect(url_for('student_dashboard'))
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

@app.route('/student/dashboard', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_dashboard():
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
        # 获取筛选条件
        activity_type = ''
        status = ''
        start_date = ''
        if request.method == 'POST':
            activity_type = request.form.get('activity_type', '').strip()
            status = request.form.get('status', '').strip()
            start_date = request.form.get('start_date', '').strip()
        # 构建SQL
        sql = '''
            SELECT a.*, u.name as organizer_name, t.name as supervisor_name
            FROM activities a
            JOIN users u ON a.organizer_id = u.user_id
            LEFT JOIN users t ON a.supervisor_id = t.user_id
            WHERE a.status = 'approved' 
            AND a.start_time > datetime('now')
            AND a.participant_count < a.max_participants
        '''
        params = []
        if activity_type:
            sql += ' AND a.activity_type = ?'
            params.append(activity_type)
        if start_date:
            sql += ' AND date(a.start_time) = ?'
            params.append(start_date)
        if status == '报名中':
            sql += ' AND a.start_time > datetime("now")'
        elif status == '即将开始':
            sql += ' AND a.start_time > datetime("now") AND a.start_time <= datetime("now", "+3 days")'
        elif status == '进行中':
            sql += ' AND a.start_time <= datetime("now") AND a.end_time > datetime("now")'
        sql += ' ORDER BY a.start_time'
        available_activities = db.execute(sql, tuple(params)).fetchall()
        # 获取已报名的活动
        my_activities = db.execute('''
            SELECT a.*, ap.status as participation_status, ap.activity_id as ap_activity_id, ap.status as ap_status, ap.approved_at, u.name as organizer_name
            FROM activities a
            JOIN activity_participants ap ON a.activity_id = ap.activity_id
            JOIN users u ON a.organizer_id = u.user_id
            WHERE ap.student_id = ?
            ORDER BY a.start_time DESC
        ''', (session['user_id'],)).fetchall()

        
        # 获取已组织的活动数量
        organized_count = db.execute('''
            SELECT COUNT(*) FROM activities WHERE organizer_id = ?
        ''', (session['user_id'],)).fetchone()[0]
        
        return render_template('student/dashboard.html', 
                             student_info=student_info,
                             student_skills=student_skills,
                             available_activities=available_activities,
                             my_activities=my_activities,

                             organized_count=organized_count)
    
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('student/dashboard.html', 
                             student_info=None,
                             student_skills=[],
                             available_activities=[],
                             my_activities=[],
                             filter_activity_type='',
                             filter_status='',
                             filter_start_date='',
                             count_applied=0,
                             count_in_progress=0,
                             count_pending=0,
                             count_completed=0)
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

@app.route('/student/apply', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_apply():
    """学生活动申请页面"""
    db = get_db()
    try:
        if request.method == 'POST':
            # 获取表单数据
            activity_name = request.form.get('activity_name')
            supervisor_name = request.form.get('supervisor')
            activity_type = request.form.get('activity_type')
            skills_list = request.form.getlist('skills')
            activity_start_time = request.form.get('activity_start_time')
            activity_end_time = request.form.get('activity_end_time')
            activity_participants = request.form.get('activity_participants', '0')
            activity_desc = request.form.get('activity_desc')
            
            # 校验必填
            if not all([activity_name, supervisor_name, activity_type, skills_list, 
                       activity_start_time, activity_end_time, activity_participants, activity_desc]):
                flash('请填写所有必填字段', 'error')
                return redirect(url_for('student_apply'))
            
            # 校验技能多选
            skills = ','.join(skills_list)
            
            try:
                # 校验时间
                if activity_start_time and activity_end_time:
                    start_time = datetime.fromisoformat(activity_start_time.replace('T', ' '))
                    end_time = datetime.fromisoformat(activity_end_time.replace('T', ' '))
                    if start_time >= end_time:
                        flash('结束时间必须晚于开始时间', 'error')
                        return redirect(url_for('student_apply'))
                    if start_time.date() < datetime.now().date():
                        flash('开始时间不能早于今天', 'error')
                        return redirect(url_for('student_apply'))
                else:
                    flash('请填写开始和结束时间', 'error')
                    return redirect(url_for('student_apply'))

                # 转换参与者数量
                try:
                    activity_participants = int(activity_participants)
                except ValueError:
                    flash('参与者数量必须为数字', 'error')
                    return redirect(url_for('student_apply'))
                
                # 校验未完结活动数
                unfinished_count = db.execute('''
                    SELECT COUNT(*) FROM activities 
                    WHERE organizer_id = ? AND status NOT IN ('completed', 'cancelled') AND end_time > datetime('now')
                ''', (session['user_id'],)).fetchone()[0]
                if unfinished_count >= 3:
                    flash('你有超过3个未结束的活动，无法继续申请', 'error')
                    return redirect(url_for('student_apply'))
                
                # 查找指导教师
                supervisor = db.execute('''
                    SELECT user_id FROM users 
                    WHERE name = ? AND user_type = 'teacher'
                ''', (supervisor_name,)).fetchone()
                if not supervisor:
                    flash('指导教师不存在，请检查姓名是否正确', 'error')
                    return redirect(url_for('student_apply'))
                
                # 活动类型映射
                db_activity_type = 'indoor' if activity_type in ['学术', '文艺'] else 'outdoor'
                
                # 插入活动
                db.execute('''
                    INSERT INTO activities (
                        organizer_id, supervisor_id, activity_name, description, 
                        start_time, end_time, required_skills, max_participants, 
                        activity_type, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review')
                ''', (session['user_id'], supervisor['user_id'], activity_name, activity_desc,
                      start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S'),
                      skills, activity_participants, db_activity_type))
                db.commit()
                flash('活动申请提交成功，等待审核！', 'success')
                return redirect(url_for('organizer_activities'))
            except ValueError as e:
                flash(f'数据格式错误：{str(e)}', 'error')
            except Exception as e:
                db.rollback()
                flash(f'申请提交失败：{str(e)}', 'error')
            return redirect(url_for('student_apply'))

        # GET请求处理
        skills = db.execute('SELECT DISTINCT skill_name FROM student_skills').fetchall()
        skill_options = [row['skill_name'] for row in skills]
        teachers = db.execute('''
            SELECT name FROM users 
            WHERE user_type = 'teacher' 
            ORDER BY name
            ''').fetchall()
        teacher_options = [row['name'] for row in teachers]
        return render_template('student/activity_apply.html', 
                             skill_options=skill_options,
                             teacher_options=teacher_options)
    finally:
        db.close()

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
                SELECT evaluation_id FROM activity_evaluations
                WHERE activity_id = ? AND participant_id = ?
            ''', (activity_id, student_id)).fetchone()
            if existing:
                db.execute('''
                    UPDATE activity_evaluations
                    SET rating = ?, created_at = CURRENT_TIMESTAMP
                    WHERE evaluation_id = ?
                ''', (score, existing['evaluation_id']))
            else:
                db.execute('''
                    INSERT INTO activity_evaluations (activity_id, participant_id, rating)
                    VALUES (?, ?, ?)
                ''', (activity_id, student_id, score))
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
                   COALESCE(ae.rating, 0) as score
            FROM activities a
            JOIN activity_participants ap ON a.activity_id = ap.activity_id
            JOIN students s ON ap.student_id = s.student_id
            JOIN users u ON s.student_id = u.user_id
            LEFT JOIN activity_evaluations ae 
                ON ae.activity_id = a.activity_id AND ae.participant_id = ap.student_id
            WHERE a.organizer_id = ? AND ap.status = 'approved'
            ORDER BY a.start_time DESC, u.name
        ''', (session['username'], session['user_id'])).fetchall()
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
            SELECT evaluation_id FROM activity_evaluations
            WHERE activity_id = ? AND participant_id = ?
        ''', (activity_id, student_id)).fetchone()
        if existing:
            db.execute('''
                UPDATE activity_evaluations
                SET rating = ?, created_at = CURRENT_TIMESTAMP
                WHERE evaluation_id = ?
            ''', (score, existing['evaluation_id']))
        else:
            db.execute('''
                INSERT INTO activity_evaluations (activity_id, participant_id, rating)
                VALUES (?, ?, ?)
            ''', (activity_id, student_id, score))
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
    db = get_db()
    try:
        if request.method == 'GET':
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
        
        elif request.method == 'POST':
            activity_id = request.form.get('activity_id')
            new_organizer_id = request.form.get('new_organizer_id')
            reason = request.form.get('reason')
            
            if not all([activity_id, new_organizer_id, reason]):
                return jsonify({'success': False, 'message': '请填写完整信息'})
            
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


@app.route('/student/query_activities', methods=['POST'])
@login_required
@role_required('student')
def query_activities():
    """多条件查询活动"""
    data = request.get_json()
    name = data.get('activity_name', '').strip()
    time = data.get('activity_time', '').strip()
    level = data.get('activity_level', '').strip()
    db = get_db()
    try:
        sql = '''SELECT a.*, u.name as organizer_name FROM activities a JOIN users u ON a.organizer_id = u.user_id WHERE a.status = 'approved' '''
        params = []
        if name:
            sql += ' AND a.activity_name LIKE ?'
            params.append(f'%{name}%')
        if time:
            sql += ' AND a.start_time = ?'
            params.append(time)
        if level:
            sql += ' AND a.activity_type = ?'
            params.append(level)
        sql += ' ORDER BY a.start_time'
        activities = db.execute(sql, tuple(params)).fetchall()
        # 组装返回数据
        result = []
        for a in activities:
            result.append({
                'activity_name': a['activity_name'],
                'start_time': a['start_time'],
                'required_skills': a['required_skills'],
                'balance': f"{a['participant_count']}/{a['max_participants']}",
                'status': a['status']
            })
        return jsonify({'success': True, 'activities': result})
    except Exception as e:
        return jsonify({'success': False, 'msg': f'查询失败: {str(e)}'}), 500
    finally:
        db.close()

@app.route('/student/recommend_activities', methods=['GET'])
@login_required
@role_required('student')
def recommend_activities():
    """返回推荐活动列表"""
    db = get_db()
    try:
        student_skills = db.execute('''SELECT skill_name FROM student_skills WHERE student_id = ?''', (session['user_id'],)).fetchall()
        skill_names = [row['skill_name'] for row in student_skills]
        if skill_names:
            placeholders = ','.join(['?'] * len(skill_names))
            recommend_activities = db.execute(f'''
            SELECT a.*, u.name as organizer_name
            FROM activities a
            JOIN users u ON a.organizer_id = u.user_id
                WHERE a.status = 'approved'
                  AND a.start_time > datetime('now')
                  AND (
                    {' OR '.join(['a.required_skills LIKE ?' for _ in skill_names])}
                  )
                  AND a.activity_id NOT IN (
                    SELECT activity_id FROM activity_participants WHERE student_id = ?
                  )
                ORDER BY a.start_time
            ''', tuple([f'%{s}%' for s in skill_names] + [session['user_id']])).fetchall()
        else:
            recommend_activities = []
        result = []
        for a in recommend_activities:
            result.append({
                'activity_name': a['activity_name'],
                'start_time': a['start_time'],
                'required_skills': a['required_skills'],
                'balance': f"{a['participant_count']}/{a['max_participants']}",
                'status': a['status']
            })
        return jsonify({'success': True, 'activities': result})
    except Exception as e:
        return jsonify({'success': False, 'msg': f'推荐失败: {str(e)}'}), 500
    finally:
        db.close()

@app.route('/student/doing_activity', methods=['GET', 'POST'])
@login_required
@role_required('student')
def doing_activity():
    db = get_db()
    msg = ''
    try:
        user_id = session['user_id']
        # 处理进度填写
        if request.method == 'POST':
            activity_id_str = request.form.get('activity_id')
            node_str = request.form.get('node')
            content = request.form.get('content', '').strip()
            
            # 验证和转换输入
            try:
                activity_id = int(activity_id_str) if activity_id_str else None
                node = int(node_str) if node_str else None
                if activity_id is None or node is None:
                    msg = '请提供有效的活动ID和节点编号'
                    return render_template('student/doing_activity.html',
                                        doing_activities=[],
                                        activity_progress={},
                                        total_nodes=4,
                                        msg=msg)
            except ValueError:
                msg = '活动ID和节点编号必须为数字'
                return render_template('student/doing_activity.html',
                                    doing_activities=[],
                                    activity_progress={},
                                    total_nodes=4,
                                    msg=msg)
            
            # 检查是否已填写该节点
            existing = db.execute('''SELECT * FROM activity_progress WHERE activity_id=? AND participant_id=? AND progress_content=?''', 
                                (activity_id, user_id, f'节点{node}')).fetchone()
            if existing:
                msg = '该节点已填写过！'
            else:
                db.execute('''INSERT INTO activity_progress (activity_id, participant_id, progress_content, completion_percentage, submitted_at) 
                            VALUES (?, ?, ?, ?, datetime('now'))''', 
                         (activity_id, user_id, f'节点{node}', node*25))
                db.commit()
                msg = '进度已保存！'
        
        # 查询进行中活动（已报名且未完成）
        doing_activities = db.execute('''
            SELECT a.activity_id, a.activity_name, ap.applied_at, a.total_score
            FROM activities a
            JOIN activity_participants ap ON a.activity_id = ap.activity_id
            WHERE ap.student_id = ? AND ap.status IN ('applied','in_progress') AND a.status = 'approved'
        ''', (user_id,)).fetchall()
        
        # 查询每个活动的已完成节点数
        activity_progress = {}
        for act in doing_activities:
            count = db.execute('''SELECT COUNT(*) FROM activity_progress WHERE activity_id=? AND participant_id=?''', 
                             (act['activity_id'], user_id)).fetchone()[0]
            activity_progress[act['activity_id']] = count
        
        # 总节点数（假设4）
        total_nodes = 4
        return render_template('student/doing_activity.html',
                             doing_activities=doing_activities,
                             activity_progress=activity_progress,
                             total_nodes=total_nodes,
                             msg=msg)
    except Exception as e:
        return render_template('student/doing_activity.html',
                             doing_activities=[],
                             activity_progress={},
                             total_nodes=4,
                             msg=f'发生错误: {str(e)}')
    finally:
        db.close()

@app.route('/student/finished_activity', methods=['GET', 'POST'])
@login_required
@role_required('student')
def finished_activity():
    db = get_db()
    msg = ''
    eval_success = False
    progress_nodes = []
    selected_activity_id = None
    try:
        user_id = session['user_id']
        # 查询所有已完成活动
        finished_activities = db.execute('''
            SELECT a.activity_id, a.activity_name, ap.applied_at,
                   (SELECT COUNT(*) FROM activity_evaluations e WHERE e.activity_id=a.activity_id AND e.participant_id=ap.student_id) as evaluated
            FROM activities a
            JOIN activity_participants ap ON a.activity_id = ap.activity_id
            WHERE ap.student_id = ? AND ap.status = 'completed' AND a.status = 'approved'
        ''', (user_id,)).fetchall()
        # 评价提交
        if request.method == 'POST':
            activity_id_str = request.form.get('activity_id', '').strip()
            rating_str = request.form.get('rating', '').strip()
            if not activity_id_str or not rating_str:
                msg = '请选择活动并填写评分！'
            else:
                selected_activity_id = int(activity_id_str)
                rating = int(rating_str)
                record = request.form.get('record', '').strip()
                comment = request.form.get('comment', '').strip()
                # 校验活动是否属于该用户已完成活动
                valid = any(a['activity_id'] == selected_activity_id for a in finished_activities)
                if not valid:
                    msg = '活动尚未完成'
                else:
                    # 检查是否已评价
                    already = db.execute('''SELECT * FROM activity_evaluations WHERE activity_id=? AND participant_id=?''', (selected_activity_id, user_id)).fetchone()
                    if already:
                        msg = '您已评价过该活动'
                    else:
                        db.execute('''INSERT INTO activity_evaluations (activity_id, participant_id, rating, comment) VALUES (?, ?, ?, ?)''', (selected_activity_id, user_id, rating, comment))
                        db.commit()
                        msg = '评价成功'
                        eval_success = True
                # 查询该活动4个节点的进度内容
                progress_nodes = db.execute('''SELECT progress_content FROM activity_progress WHERE activity_id=? AND participant_id=? ORDER BY progress_id''', (selected_activity_id, user_id)).fetchall()
        else:
            # GET请求，支持activity_id参数
            activity_id_str = request.args.get('activity_id', '').strip()
            if activity_id_str:
                selected_activity_id = int(activity_id_str)
                progress_nodes = db.execute('''SELECT progress_content FROM activity_progress WHERE activity_id=? AND participant_id=? ORDER BY progress_id''', (selected_activity_id, user_id)).fetchall()
        return render_template('student/finished_activity.html',
                              finished_activities=finished_activities,
                              msg=msg,
                              eval_success=eval_success,
                              progress_nodes=progress_nodes,
                              selected_activity_id=selected_activity_id)
    except Exception as e:
        return render_template('student/finished_activity.html',
                              finished_activities=[],
                              msg=f'发生错误: {str(e)}',
                              eval_success=False,
                              progress_nodes=[],
                              selected_activity_id=None)
    finally:
        db.close()

@app.route('/student/profile_view')
@login_required
@role_required('student')
def profile_view():
    db = get_db()
    try:
        user_id = session['user_id']
        # 获取学生基本信息（只用存在的字段）
        student_info = db.execute('''
            SELECT s.student_number, s.grade, s.major, s.class_name, s.score, s.activity_completion_rate, u.name, u.college, u.phone
            FROM students s
            JOIN users u ON s.student_id = u.user_id
            WHERE s.student_id = ?
        ''', (user_id,)).fetchone()
        # 获取学生特长
        student_skills = db.execute('''
            SELECT skill_name, skill_level FROM student_skills WHERE student_id = ?
        ''', (user_id,)).fetchall()
        # 获取已完成活动
        finished_activities = db.execute('''
            SELECT a.activity_name
            FROM activities a
            JOIN activity_participants ap ON a.activity_id = ap.activity_id
            WHERE ap.student_id = ? AND ap.status = 'completed' AND a.status = 'approved'
        ''', (user_id,)).fetchall()
        return render_template('student/profile_view.html', student_info=student_info, student_skills=student_skills, finished_activities=finished_activities)
    except Exception as e:
        flash(f'获取个人信息失败：{str(e)}', 'error')
        return render_template('student/profile_view.html', student_info=None, student_skills=[], finished_activities=[])
    finally:
        db.close()

@app.route('/student/profile_edit', methods=['GET', 'POST'])
@login_required
@role_required('student')
def profile_edit():
    db = get_db()
    user_id = session['user_id']
    msg = ''
    try:
        if request.method == 'POST':
            # 只允许修改部分字段
            name = request.form.get('name', '').strip()
            student_number = request.form.get('student_number', '').strip()
            grade = request.form.get('grade', '').strip()
            major = request.form.get('major', '').strip()
            class_name = request.form.get('class_name', '').strip()
            college = request.form.get('college', '').strip()
            phone = request.form.get('phone', '').strip()
            # 简单校验
            if not all([name, student_number, grade, major, class_name, college]):
                msg = '请填写完整信息！'
            else:
                db.execute('UPDATE users SET name=?, college=?, phone=? WHERE user_id=?', (name, college, phone, user_id))
                db.execute('UPDATE students SET student_number=?, grade=?, major=?, class_name=? WHERE student_id=?', (student_number, grade, major, class_name, user_id))
                db.commit()
                msg = '信息已更新！'
        # 查询当前信息
        student_info = db.execute('''
            SELECT s.student_number, s.grade, s.major, s.class_name, s.score, s.activity_completion_rate, u.name, u.college, u.phone
            FROM students s
            JOIN users u ON s.student_id = u.user_id
            WHERE s.student_id = ?
        ''', (user_id,)).fetchone()
        return render_template('student/profile_edit.html', student_info=student_info, msg=msg)
    except Exception as e:
        flash(f'获取或保存信息失败：{str(e)}', 'error')
        return render_template('student/profile_edit.html', student_info=None, msg='')
    finally:
        db.close()

@app.route('/student/schedule', methods=['GET', 'POST'])
@login_required
@role_required('student')
def schedule():
    db = get_db()
    msg = ''
    try:
        user_id = session['user_id']
        if request.method == 'POST':
            action = request.form.get('action')
            weekday_str = request.form.get('weekday')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            course_name = request.form.get('course_name', '').strip()
            
            # 验证和转换weekday
            try:
                weekday = int(weekday_str) if weekday_str else None
                if weekday is None or not (0 <= weekday <= 6):
                    msg = '请提供有效的星期数（0-6）'
                    raise ValueError(msg)
            except ValueError as e:
                return render_template('student/schedule.html', 
                                     schedule_dict={}, 
                                     msg=str(e))
            
            if action == 'add':
                # 检查是否已存在
                exists = db.execute('''SELECT * FROM student_schedule 
                                     WHERE student_id=? AND weekday=? AND start_time=? AND end_time=?''', 
                                  (user_id, weekday, start_time, end_time)).fetchone()
                if exists:
                    msg = '该时间段已有课程，可选择修改！'
                else:
                    db.execute('''INSERT INTO student_schedule (student_id, weekday, start_time, end_time, course_name) 
                                VALUES (?, ?, ?, ?, ?)''', 
                             (user_id, weekday, start_time, end_time, course_name))
                    db.commit()
                    msg = '课程已添加！'
            elif action == 'update':
                db.execute('''UPDATE student_schedule 
                            SET course_name=? 
                            WHERE student_id=? AND weekday=? AND start_time=? AND end_time=?''', 
                         (course_name, user_id, weekday, start_time, end_time))
                db.commit()
                msg = '课程已更新！'
            elif action == 'delete':
                db.execute('''DELETE FROM student_schedule 
                            WHERE student_id=? AND weekday=? AND start_time=? AND end_time=?''', 
                         (user_id, weekday, start_time, end_time))
                db.commit()
                msg = '课程已删除！'
        
        # 查询当前学生所有课表
        schedule_rows = db.execute('''
            SELECT weekday, start_time, end_time, course_name
            FROM student_schedule
            WHERE student_id = ?
        ''', (user_id,)).fetchall()
        schedule_dict = {}
        for row in schedule_rows:
            key = (row['weekday'], row['start_time'], row['end_time'])
            schedule_dict[key] = row['course_name']
        return render_template('student/schedule.html', schedule_dict=schedule_dict, msg=msg)
    except Exception as e:
        flash(f'获取课表失败：{str(e)}', 'error')
        return render_template('student/schedule.html', schedule_dict={}, msg='')
    finally:
        db.close()

@app.route('/student/leave', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_leave():
    db = get_db()
    msg = ''
    try:
        user_id = session['user_id']
        # 查询进行中或未结束的活动及其指导老师
        activities = db.execute('''
            SELECT a.activity_id, a.activity_name, u.name as supervisor_name, a.supervisor_id
            FROM activities a
            JOIN activity_participants ap ON a.activity_id = ap.activity_id
            LEFT JOIN users u ON a.supervisor_id = u.user_id
            WHERE ap.student_id = ? AND ap.status IN ('applied','in_progress') AND a.status = 'approved'
        ''', (user_id,)).fetchall()
        # 统计各类活动数量
        count_applied = db.execute('''SELECT COUNT(*) FROM activity_participants WHERE student_id=? AND status='applied' ''', (user_id,)).fetchone()[0]
        count_in_progress = db.execute('''SELECT COUNT(*) FROM activity_participants WHERE student_id=? AND status='in_progress' ''', (user_id,)).fetchone()[0]
        count_pending = db.execute('''SELECT COUNT(*) FROM activity_participants WHERE student_id=? AND status='pending_review' ''', (user_id,)).fetchone()[0]
        count_completed = db.execute('''SELECT COUNT(*) FROM activity_participants WHERE student_id=? AND status='completed' ''', (user_id,)).fetchone()[0]
        if request.method == 'POST':
            activity_id = request.form.get('activity_id')
            reason = request.form.get('reason','').strip()
            teacher_id = request.form.get('teacher_id')
            leave_time = request.form.get('leave_time')
            # 简单校验
            if not activity_id or not reason or not teacher_id or not leave_time:
                msg = '请填写完整信息！'
            else:
                # 保存请假信息到 student_leave 表（如无则创建）
                db.execute('''CREATE TABLE IF NOT EXISTS student_leave (
                    leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    activity_id INTEGER,
                    teacher_id INTEGER,
                    reason TEXT,
                    leave_time TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
                db.execute('''INSERT INTO student_leave (student_id, activity_id, teacher_id, reason, leave_time) VALUES (?, ?, ?, ?, ?)''',
                    (user_id, activity_id, teacher_id, reason, leave_time))
                db.commit()
                msg = '请假申请已提交！'
        return render_template('student/leave.html', activities=activities, msg=msg,
            count_applied=count_applied, count_in_progress=count_in_progress, count_pending=count_pending, count_completed=count_completed)
    except Exception as e:
        return render_template('student/leave.html', activities=[], msg=f'发生错误: {str(e)}',
            count_applied=0, count_in_progress=0, count_pending=0, count_completed=0)
    finally:
        db.close()

@app.route('/student/message')
@login_required
@role_required('student')
def student_message():
    db = get_db()
    try:
        user_id = session['user_id']
        notifications = db.execute('''
            SELECT * FROM notifications
            WHERE recipient_id = ?
            ORDER BY created_at DESC
        ''', (user_id,)).fetchall()
        return render_template('student/message.html', notifications=notifications)
    except Exception as e:
        flash(f'获取消息失败：{str(e)}', 'error')
        return render_template('student/message.html', notifications=[])
    finally:
        db.close()

# ==================== 教师路由 ====================

# 注册所有教师子模块 Blueprint
app.register_blueprint(teacher_dashboard_bp)
app.register_blueprint(teacher_stats_bp)
app.register_blueprint(teacher_evaluation_bp)
app.register_blueprint(teacher_account_bp)
app.register_blueprint(teacher_personcenter_bp)
app.register_blueprint(teacher_funding_bp)
app.register_blueprint(teacher_approval_bp)

# ==================== 管理员路由 ====================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """管理员主页"""
    db = get_db()
    try:
        # 获取管理员信息
        admin_info = db.execute('''
            SELECT t.*, u.name, u.college 
            FROM teachers t
            JOIN users u ON t.teacher_id = u.user_id
            WHERE t.teacher_id = ? AND t.is_admin = 1
        ''', (session['user_id'],)).fetchone()
        
        # 获取所有待审核的活动
        pending_activities = db.execute('''
            SELECT a.*, u.name as organizer_name, t.name as supervisor_name
            FROM activities a
            JOIN users u ON a.organizer_id = u.user_id
            LEFT JOIN users t ON a.supervisor_id = t.user_id
            WHERE a.status = 'pending_review'
            ORDER BY a.created_at DESC
        ''').fetchall()
        

        return render_template('admin/dashboard.html',
                             admin_info=admin_info,
                             pending_activities=pending_activities,
                             )
    
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('admin/dashboard.html',
                             admin_info=None,
                             pending_activities=[],
                             )
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

# ==================== 教师评价详情API ====================

@app.route('/teacher/activity-evaluations/<int:activity_id>')
@login_required
@role_required('teacher')
def get_activity_evaluations(activity_id):
    """获取某活动的评价详情（面向教师）"""
    db = get_db()
    try:
        # 假设评价表为 organizer_evaluations，评价人为老师
        evaluations = db.execute('''
            SELECT oe.*, u.name as evaluator_name
            FROM organizer_evaluations oe
            JOIN users u ON oe.evaluator_id = u.user_id
            WHERE oe.activity_id = ?
        ''', (activity_id,)).fetchall()
        result = []
        for row in evaluations:
            result.append({
                'evaluation_id': row['evaluation_id'],
                'activity_id': row['activity_id'],
                'evaluator_id': row['evaluator_id'],
                'evaluator_name': row['evaluator_name'],
                'rating': row['rating'],
                'comment': row['comment'],
                'created_at': row['created_at']
            })
        return jsonify({'success': True, 'evaluations': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'evaluations': []})
    finally:
        db.close()

@app.route('/teacher/participant-evaluations/<int:activity_id>')
@login_required
@role_required('teacher')
def get_participant_evaluations(activity_id):
    """获取某活动下所有参与者的评价详情（面向教师）"""
    db = get_db()
    try:
        # 假设参与者评价表为 activity_participants，评价内容为 comment，评分为 rating
        evaluations = db.execute('''
            SELECT ap.*, u.name as participant_name
            FROM activity_participants ap
            JOIN users u ON ap.student_id = u.user_id
            WHERE ap.activity_id = ? AND ap.comment IS NOT NULL
        ''', (activity_id,)).fetchall()
        result = []
        for row in evaluations:
            result.append({
                'participant_id': row['student_id'],
                'participant_name': row['participant_name'],
                'rating': row['rating'],
                'comment': row['comment'],
                'created_at': row['updated_at'] if 'updated_at' in row.keys() else None
            })
        return jsonify({'success': True, 'evaluations': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'evaluations': []})
    finally:
        db.close()

@app.route('/teacher/approve_progress/<int:progress_id>', methods=['POST'])
@login_required
@role_required('teacher')
def approve_progress(progress_id):
    """审批进度（通过/打回/中断）"""
    db = get_db()
    try:
        action = request.form.get('action')  # approve/reject/interrupt
        if action == 'approve':
            db.execute('UPDATE activity_progress SET review_status = "approved" WHERE progress_id = ?', (progress_id,))
        elif action == 'reject':
            db.execute('UPDATE activity_progress SET review_status = "rejected" WHERE progress_id = ?', (progress_id,))
        else:
            return jsonify({'success': False, 'msg': '未知操作'})
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})
    finally:
        db.close()

@app.route('/teacher/submit-organizer-rating', methods=['POST'])
@login_required
@role_required('teacher')
def submit_organizer_rating():
    """提交组织者评分"""
    db = get_db()
    try:
        activity_id = request.form.get('activity_id')
        organizer_id = request.form.get('organizer_id')
        score_raw = request.form.get('score')
        comment = request.form.get('comment')
        evaluator_id = session['user_id']
        if not score_raw or not score_raw.isdigit():
            return jsonify({'success': False, 'message': '评分不能为空且必须为数字'})
        score = int(score_raw)
        # 分数范围1-10，转为1-5
        rating = min(5, max(1, round(score / 2)))
        # 检查是否已评分
        exists = db.execute('SELECT 1 FROM organizer_evaluations WHERE activity_id = ? AND organizer_id = ? AND evaluator_id = ?', (activity_id, organizer_id, evaluator_id)).fetchone()
        if exists:
            db.execute('UPDATE organizer_evaluations SET rating = ?, comment = ?, created_at = datetime("now") WHERE activity_id = ? AND organizer_id = ? AND evaluator_id = ?', (rating, comment, activity_id, organizer_id, evaluator_id))
        else:
            db.execute('INSERT INTO organizer_evaluations (activity_id, organizer_id, evaluator_id, rating, comment) VALUES (?, ?, ?, ?, ?)', (activity_id, organizer_id, evaluator_id, rating, comment))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

# ==================== 错误处理 ====================

@app.errorhandler(404)
def page_not_found(e):
    return '404 Not Found', 404

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