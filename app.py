from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 生产环境请使用更安全的密钥

# 数据库文件路径
DATABASE = 'University_activit.db'

# 数据库连接封装

# 装饰器：登录验证

# 装饰器：角色验证

# 装饰器：管理员验证

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
                
                # 根据用户类型重定向
                if user['user_type'] == 'student':
                    return redirect(url_for('student_dashboard'))
                elif user['user_type'] == 'teacher':
                    return redirect(url_for('teacher_dashboard.dashboard'))
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
    app.run(debug=True, host='0.0.0.0', port=4000)