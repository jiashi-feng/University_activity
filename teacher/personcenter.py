# 教师个人中心相关路由和逻辑
from flask import Blueprint, render_template, session, flash
from extensions import get_db, login_required, role_required

# 创建蓝图对象，设置URL前缀为/teacher
bp = Blueprint('teacher_personcenter', __name__, url_prefix='/teacher')

@bp.route('/personcenter')
@login_required
@role_required('teacher')
def personcenter():
    """
    教师个人中心页面，展示教师基础信息
    """
    db = get_db()
    # 查询当前教师信息
    teacher = db.execute('''
        SELECT t.*, u.name, u.college, u.phone, u.created_at
        FROM teachers t
        JOIN users u ON t.teacher_id = u.user_id
        WHERE t.teacher_id = ?
    ''', (session['user_id'],)).fetchone()
    # 渲染模板并传递数据
    return render_template('teacher/personcenter.html', teacher=teacher)