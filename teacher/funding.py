# 资金分配相关路由和逻辑
from flask import Blueprint, render_template, flash
from extensions import get_db, login_required, role_required

# 创建蓝图对象，设置URL前缀为/teacher
bp = Blueprint('teacher_funding', __name__, url_prefix='/teacher')

@bp.route('/funding')
@login_required
@role_required('teacher')
def funding():
    """
    资金分配页面，展示已审批活动
    """
    db = get_db()
    # 查询已审批活动及其组织者
    funding_activities = db.execute('''
        SELECT a.*, u.name as organizer_name
        FROM activities a
        JOIN users u ON a.organizer_id = u.user_id
        WHERE a.status = 'approved'
        ORDER BY a.start_time DESC
    ''').fetchall()
    # 渲染模板并传递数据
    return render_template('teacher/funding.html',
                          funding_activities=funding_activities)