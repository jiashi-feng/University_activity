# 活动评价相关路由和逻辑
from flask import Blueprint, render_template, session, flash, jsonify, request
from extensions import get_db, login_required, role_required

# 创建蓝图对象，设置URL前缀为/teacher
bp = Blueprint('teacher_evaluation', __name__, url_prefix='/teacher')

@bp.route('/evaluation')
@login_required
@role_required('teacher')
def evaluation():
    """
    活动评价主页面，展示已完成活动和组织者活动
    """
    db = get_db()
    # 查询已完成活动
    completed_activities = db.execute('''
        SELECT a.*, u.name as organizer_name, u.college
        FROM activities a
        JOIN users u ON a.organizer_id = u.user_id
        WHERE a.status = 'completed'
        ORDER BY a.end_time DESC
    ''').fetchall()
    # 查询组织者活动及评分
    organizer_activities = db.execute('''
        SELECT a.*, u.name as organizer_name, u.college,
               oe.rating as teacher_score, oe.comment as teacher_comment
        FROM activities a
        JOIN users u ON a.organizer_id = u.user_id
        LEFT JOIN organizer_evaluations oe ON a.activity_id = oe.activity_id AND oe.evaluator_id = ?
        WHERE a.status = 'completed'
        ORDER BY a.created_at DESC
    ''', (session['user_id'],)).fetchall()
    # 渲染模板并传递数据
    return render_template('teacher/evaluation.html',
                          completed_activities=completed_activities,
                          organizer_activities=organizer_activities)

@bp.route('/activity-evaluations/<int:activity_id>')
@login_required
@role_required('teacher')
def get_activity_evaluations(activity_id):
    """
    获取某活动的所有评价详情
    """
    db = get_db()
    # 查询评价详情
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

@bp.route('/participant-evaluations/<int:activity_id>')
@login_required
@role_required('teacher')
def get_participant_evaluations(activity_id):
    """
    获取某活动的所有参与者评价详情
    """
    db = get_db()
    # 查询参与者评价详情
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

@bp.route('/submit-organizer-rating', methods=['POST'])
@login_required
@role_required('teacher')
def submit_organizer_rating():
    """
    提交组织者评分和评语
    """
    db = get_db()
    activity_id = request.form.get('activity_id')
    organizer_id = request.form.get('organizer_id')
    score_raw = request.form.get('score')
    comment = request.form.get('comment')
    evaluator_id = session['user_id']
    # 校验分数
    if not score_raw or not score_raw.isdigit():
        return jsonify({'success': False, 'message': '评分不能为空且必须为数字'})
    score = int(score_raw)
    rating = min(5, max(1, round(score / 2)))
    # 判断是否已存在评分
    exists = db.execute('SELECT 1 FROM organizer_evaluations WHERE activity_id = ? AND organizer_id = ? AND evaluator_id = ?', (activity_id, organizer_id, evaluator_id)).fetchone()
    if exists:
        # 已有则更新
        db.execute('UPDATE organizer_evaluations SET rating = ?, comment = ?, created_at = datetime("now") WHERE activity_id = ? AND organizer_id = ? AND evaluator_id = ?', (rating, comment, activity_id, organizer_id, evaluator_id))
    else:
        # 没有则插入
        db.execute('INSERT INTO organizer_evaluations (activity_id, organizer_id, evaluator_id, rating, comment) VALUES (?, ?, ?, ?, ?)', (activity_id, organizer_id, evaluator_id, rating, comment))
    db.commit()
    return jsonify({'success': True})