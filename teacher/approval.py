# 审批相关路由和逻辑
from flask import Blueprint, jsonify, request
from extensions import get_db, login_required, role_required

# 创建蓝图对象，设置URL前缀为/teacher
bp = Blueprint('teacher_approval', __name__, url_prefix='/teacher')

@bp.route('/approve_organizer_change/<int:change_id>', methods=['POST'])
@login_required
@role_required('teacher')
def approve_organizer_change(change_id):
    """
    审批组织者更换请求
    """
    db = get_db()
    action = request.form.get('action')  # 获取操作类型
    # 查询更换申请记录
    change = db.execute('SELECT * FROM organizer_changes WHERE change_id = ?', (change_id,)).fetchone()
    if not change:
        return jsonify({'success': False, 'msg': '更换申请不存在'})
    if action == 'approve':
        # 审批通过，更新活动组织者
        db.execute('UPDATE activities SET organizer_id = ? WHERE activity_id = ?', (change['new_organizer_id'], change['activity_id']))
        db.execute('UPDATE organizer_changes SET change_status = "approved", processed_at = datetime("now") WHERE change_id = ?', (change_id,))
    elif action == 'reject':
        # 审批打回
        db.execute('UPDATE organizer_changes SET change_status = "rejected", processed_at = datetime("now") WHERE change_id = ?', (change_id,))
    else:
        return jsonify({'success': False, 'msg': '未知操作'})
    db.commit()
    db.close()
    return jsonify({'success': True})

@bp.route('/approve_progress/<int:progress_id>', methods=['POST'])
@login_required
@role_required('teacher')
def approve_progress(progress_id):
    """
    审批活动进度请求
    """
    db = get_db()
    action = request.form.get('action')  # 获取操作类型
    if action == 'approve':
        # 审批通过
        db.execute('UPDATE activity_progress SET review_status = "approved" WHERE progress_id = ?', (progress_id,))
    elif action == 'reject':
        # 审批打回
        db.execute('UPDATE activity_progress SET review_status = "rejected" WHERE progress_id = ?', (progress_id,))
    db.commit()
    db.close()
    return jsonify({'success': True}) 