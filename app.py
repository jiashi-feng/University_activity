from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
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
            return redirect(url_for('index')) # 学生登录后跳转到选择界面
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
                    return redirect(url_for('dashboard_select'))
                elif user['user_type'] == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
            else:
                flash('用户名或密码错误', 'error')
        
        except Exception as e:
            flash(f'登录失败：{str(e)}', 'error')
        finally:
            db.close()
    
    return render_template('login.html')

# 新增：学生登录后选择界面
@app.route('/student/dashboard_select', methods=['GET', 'POST'])
def dashboard_select():
    if request.method == 'POST':
        role = request.form.get('role')
        if role == 'participant':
            return redirect(url_for('student_dashboard'))
        elif role == 'organizer':
            return redirect(url_for('student_dashboard2'))
    return render_template('student/dashboard_select.html')

# 新增：组织者界面（dashboard2.html）
@app.route('/student/dashboard2')
@login_required
@role_required('student')
def student_dashboard2():
    return render_template('student/dashboard.html')

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
        # 统计各类活动数量（结合节点数和审核状态）
        count_applied = 0
        count_in_progress = 0
        count_pending = 0
        count_completed = 0
        for act in my_activities:
            # 查询该活动的进度节点数
            node_count = db.execute('''SELECT COUNT(*) FROM activity_progress WHERE activity_id=? AND participant_id=?''', (act['ap_activity_id'], session['user_id'])).fetchone()[0]
            # 审核通过：ap.status in ('in_progress','completed') 或 ap.approved_at不为空
            is_approved = act['ap_status'] in ('in_progress','completed') or (act['approved_at'] is not None)
            if act['ap_status'] == 'completed':
                count_completed += 1
            elif act['ap_status'] == 'applied':
                if not is_approved:
                    if node_count == 0 or node_count == 4:
                        count_applied += 1
                    count_pending += 1
                else:
                    count_in_progress += 1
            elif act['ap_status'] == 'in_progress' or (is_approved or node_count < 4):
                count_in_progress += 1
        return render_template('student/dashboard1.html', 
                             student_info=student_info,
                             student_skills=student_skills,
                             available_activities=available_activities,
                             my_activities=my_activities,
                             filter_activity_type=activity_type,
                             filter_status=status,
                             filter_start_date=start_date,
                             count_applied=count_applied,
                             count_in_progress=count_in_progress,
                             count_pending=count_pending,
                             count_completed=count_completed)
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('student/dashboard1.html', 
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

@app.route('/student/add_activity', methods=['GET', 'POST'])
@login_required
@role_required('student')
def add_activity():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        activity_name = data.get('activity_name')
        activity_time = data.get('activity_time')  # 允许只输入日期
        activity_level = data.get('activity_level')
        print('DEBUG: activity_name:', activity_name, '| activity_time:', activity_time, '| activity_level:', activity_level)
        try:
            # 支持只输入日期匹配
            activity = db.execute('''
                SELECT * FROM activities WHERE activity_name = ? AND date(start_time) = ? AND activity_type = ?
            ''', (activity_name, activity_time, activity_level)).fetchone()
            if not activity:
                return jsonify({'success': False, 'msg': '无此项活动'}), 404
            # 检查是否已报名
            existing = db.execute('''
                SELECT * FROM activity_participants WHERE activity_id = ? AND student_id = ?
            ''', (activity['activity_id'], session['user_id'])).fetchone()
            if existing:
                return jsonify({'success': False, 'msg': '您已报名该活动'}), 400
            # 添加报名
            db.execute('''
                INSERT INTO activity_participants (activity_id, student_id, status) VALUES (?, ?, 'applied')
            ''', (activity['activity_id'], session['user_id']))
            db.execute('''
                UPDATE activities SET participant_count = participant_count + 1 WHERE activity_id = ?
            ''', (activity['activity_id'],))
            db.commit()
            return jsonify({'success': True, 'msg': '添加成功'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'msg': f'添加失败: {str(e)}'}), 500
        finally:
            db.close()
    else:
        try:
            # 获取当前学生特长
            student_skills = db.execute('''
                SELECT skill_name FROM student_skills WHERE student_id = ?
            ''', (session['user_id'],)).fetchall()
            skill_names = [row['skill_name'] for row in student_skills]
            # 推荐活动：所需特长与学生特长有交集，且未报名，且未开始
            if skill_names:
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
            return render_template('student/add_activity.html', recommend_activities=recommend_activities)
        except Exception as e:
            return render_template('student/add_activity.html', recommend_activities=[])
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
            activity_id = int(request.form.get('activity_id'))
            node = int(request.form.get('node'))
            content = request.form.get('content', '').strip()
            # 检查是否已填写该节点
            existing = db.execute('''SELECT * FROM activity_progress WHERE activity_id=? AND participant_id=? AND progress_content=?''', (activity_id, user_id, f'节点{node}')).fetchone()
            if existing:
                msg = '该节点已填写过！'
            else:
                db.execute('''INSERT INTO activity_progress (activity_id, participant_id, progress_content, completion_percentage, submitted_at) VALUES (?, ?, ?, ?, datetime('now'))''', (activity_id, user_id, f'节点{node}', node*25))
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
            count = db.execute('''SELECT COUNT(*) FROM activity_progress WHERE activity_id=? AND participant_id=?''', (act['activity_id'], user_id)).fetchone()[0]
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
            weekday = int(request.form.get('weekday'))
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            course_name = request.form.get('course_name', '').strip()
            if action == 'add':
                # 检查是否已存在
                exists = db.execute('''SELECT * FROM student_schedule WHERE student_id=? AND weekday=? AND start_time=? AND end_time=?''', (user_id, weekday, start_time, end_time)).fetchone()
                if exists:
                    msg = '该时间段已有课程，可选择修改！'
                else:
                    db.execute('''INSERT INTO student_schedule (student_id, weekday, start_time, end_time, course_name) VALUES (?, ?, ?, ?, ?)''', (user_id, weekday, start_time, end_time, course_name))
                    db.commit()
                    msg = '课程已添加！'
            elif action == 'update':
                db.execute('''UPDATE student_schedule SET course_name=? WHERE student_id=? AND weekday=? AND start_time=? AND end_time=?''', (course_name, user_id, weekday, start_time, end_time))
                db.commit()
                msg = '课程已更新！'
            elif action == 'delete':
                db.execute('''DELETE FROM student_schedule WHERE student_id=? AND weekday=? AND start_time=? AND end_time=?''', (user_id, weekday, start_time, end_time))
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