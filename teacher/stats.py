# 数据统计相关路由和逻辑
from flask import Blueprint, render_template
from extensions import get_db, login_required, role_required

# 创建蓝图对象，设置URL前缀为/teacher
bp = Blueprint('teacher_stats', __name__, url_prefix='/teacher')

@bp.route('/stats')
@login_required
@role_required('teacher')
def stats():
    """
    数据统计页面，展示活动数量、历史活动、学生积分排名
    """
    db = get_db()
    # 查询活动总数
    total_activities = db.execute('''
        SELECT COUNT(*) as count FROM activities
    ''').fetchone()['count']
    # 查询已完成活动数
    completed_activities_count = db.execute('''
        SELECT COUNT(*) as count FROM activities 
        WHERE status = 'completed'
    ''').fetchone()['count']
    # 查询进行中活动数
    in_progress_activities_count = db.execute('''
        SELECT COUNT(*) as count FROM activities 
        WHERE status = 'in_progress'
    ''').fetchone()['count']
    # 查询未开始活动数
    not_started_activities_count = db.execute('''
        SELECT COUNT(*) as count FROM activities 
        WHERE status NOT IN ('completed', 'in_progress')
    ''').fetchone()['count']
    # 查询已结束活动详细信息
    ended_activities = db.execute('''
        SELECT a.*, u.name as organizer_name, u.college
        FROM activities a
        JOIN users u ON a.organizer_id = u.user_id
        WHERE a.status = 'completed'
        ORDER BY a.end_time DESC
    ''').fetchall()
    # 查询学生积分排名
    ranking = db.execute('''
        SELECT s.student_id, u.name, 
               s.score as score,
               COUNT(DISTINCT ap.activity_id) as activity_count,
               COUNT(DISTINCT CASE WHEN ap.status = 'completed' THEN ap.activity_id END) as completed_count,
               CASE 
                   WHEN COUNT(DISTINCT ap.activity_id) > 0 
                   THEN CAST(COUNT(DISTINCT CASE WHEN ap.status = 'completed' THEN ap.activity_id END) AS FLOAT) / COUNT(DISTINCT ap.activity_id)
                   ELSE 0 
               END as activity_completion_rate
        FROM students s
        JOIN users u ON s.student_id = u.user_id
        LEFT JOIN activity_participants ap ON s.student_id = ap.student_id
        GROUP BY s.student_id, u.name, s.score
        ORDER BY score DESC, activity_completion_rate DESC
        LIMIT 20
    ''').fetchall()
    db.close()
    # 渲染模板并传递数据
    return render_template('teacher/stats.html',
                         total_activities=total_activities,
                         completed_activities_count=completed_activities_count,
                         in_progress_activities_count=in_progress_activities_count,
                         not_started_activities_count=not_started_activities_count,
                         ended_activities=ended_activities,
                         ranking=ranking)