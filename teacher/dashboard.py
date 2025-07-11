# 活动管理相关路由和逻辑
from flask import Blueprint, render_template, session, flash
from extensions import get_db, login_required, role_required

# 创建蓝图对象，设置URL前缀为/teacher
bp = Blueprint('teacher_dashboard', __name__, url_prefix='/teacher')

@bp.route('/dashboard')
@login_required
@role_required('teacher')
def dashboard():
    """
    活动管理主页面，展示教师信息、活动列表、审批列表等
    """
    db = get_db()
    try:
        # 查询当前教师信息
        teacher_info = db.execute('''
            SELECT t.*, u.name, u.college, u.phone, u.created_at
            FROM teachers t
            JOIN users u ON t.teacher_id = u.user_id
            WHERE t.teacher_id = ?
        ''', (session['user_id'],)).fetchone()
        # 查询所有活动及组织者
        supervised_activities = db.execute('''
            SELECT a.*, u.name as organizer_name
            FROM activities a
            JOIN users u ON a.organizer_id = u.user_id
            ORDER BY a.created_at DESC
        ''').fetchall()
        pending_activities = []
        # 如果是管理员，查询待审批活动
        if teacher_info and teacher_info['is_admin']:
            pending_activities = db.execute('''
                SELECT a.*, u.name as organizer_name
                FROM activities a
                JOIN users u ON a.organizer_id = u.user_id
                WHERE a.status = 'pending_review'
                ORDER BY a.created_at DESC
            ''').fetchall()
        # 查询进度审批列表
        progress_list = db.execute('''
            SELECT ap.progress_id, a.activity_name, u.name as organizer, u.college, \
                   ap.progress_content, ap.completion_percentage, ap.review_status
            FROM activity_progress ap
            JOIN activities a ON ap.activity_id = a.activity_id
            JOIN users u ON a.organizer_id = u.user_id
            ORDER BY ap.submitted_at DESC
        ''').fetchall()
        # 查询更换人员审批列表
        change_list = db.execute('''
            SELECT oc.change_id, a.activity_name, u1.name as original_organizer, u2.name as new_organizer,\
                   oc.reason, oc.change_status, oc.requested_at
            FROM organizer_changes oc
            JOIN activities a ON oc.activity_id = a.activity_id
            JOIN users u1 ON oc.original_organizer_id = u1.user_id
            JOIN users u2 ON oc.new_organizer_id = u2.user_id
            ORDER BY oc.requested_at DESC
        ''').fetchall()
        # 渲染模板并传递数据
        return render_template('teacher/dashboard.html',
                             teacher_info=teacher_info,
                             supervised_activities=supervised_activities,
                             pending_activities=pending_activities,
                             progress_list=progress_list,
                             change_list=change_list)
    except Exception as e:
        flash(f'获取数据失败：{str(e)}', 'error')
        return render_template('teacher/dashboard.html',
                             teacher_info=None,
                             supervised_activities=[],
                             pending_activities=[])
    finally:
        db.close() 