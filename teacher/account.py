# 资金管理相关路由和逻辑
from flask import Blueprint, render_template, flash, session, jsonify, request, redirect
from extensions import get_db, login_required, role_required

# 创建蓝图对象，设置URL前缀为/teacher
bp = Blueprint('teacher_account', __name__, url_prefix='/teacher')

@bp.route('/account')
@login_required
@role_required('teacher')
def account():
    """
    资金管理主页面，展示剩余资金、分配和奖励历史
    """
    db = get_db()
    # 总资金常量
    TOTAL_FUNDS = 200000
    # 查询已分配资金总额
    allocated = db.execute('SELECT COALESCE(SUM(allocated_funds), 0) as allocated FROM activities').fetchone()['allocated']
    # 查询已发放奖励总预算
    rewards_sum = db.execute('SELECT COALESCE(SUM(total_budget), 0) as rewards_sum FROM rewards').fetchone()['rewards_sum']
    # 计算剩余资金
    funds = TOTAL_FUNDS - allocated - rewards_sum
    # 查询待分配资金的活动（status=approved且allocated_funds=0）
    pending_allocations = db.execute('''
        SELECT a.*, u.name as organizer, u.college
        FROM activities a
        JOIN users u ON a.organizer_id = u.user_id
        WHERE a.status = 'approved' AND (a.allocated_funds IS NULL OR a.allocated_funds = 0)
        ORDER BY a.created_at DESC
    ''').fetchall()
    # 查询已分配资金的活动（status=approved且allocated_funds>0）
    history = db.execute('''
        SELECT a.*, u.name as organizer, u.college
        FROM activities a
        JOIN users u ON a.organizer_id = u.user_id
        WHERE a.status = 'approved' AND a.allocated_funds > 0
        ORDER BY a.created_at DESC
    ''').fetchall()
    # 查询奖励发放历史记录
    rewards_history = db.execute('SELECT * FROM rewards ORDER BY reward_id DESC').fetchall()
    db.close()
    return render_template('teacher/account.html',
                         funds=funds,
                         pending_allocations=pending_allocations,
                         history=history,
                         rewards_history=rewards_history)

@bp.route('/allocate-funds', methods=['POST'])
@login_required
@role_required('teacher')
def allocate_funds():
    """
    资金分配处理，分配资金给活动
    """
    db = get_db()
    activity_id = request.form.get('activity_id')
    allocated_funds = float(request.form.get('allocated_funds', 0))
    remaining_funds = float(request.form.get('remaining_funds', 0))
    TOTAL_FUNDS = 200000
    # 查询已分配资金总额
    allocated = db.execute('SELECT COALESCE(SUM(allocated_funds), 0) as allocated FROM activities').fetchone()['allocated']
    if allocated_funds <= 0:
        return jsonify({'success': False, 'msg': '分配金额必须大于0'})
    if allocated + allocated_funds > TOTAL_FUNDS:
        return jsonify({'success': False, 'msg': '分配后超出总资金'})
    # 更新活动的已分配资金和剩余金额
    db.execute('UPDATE activities SET allocated_funds = allocated_funds + ?, remaining_funds = ? WHERE activity_id = ?', (allocated_funds, remaining_funds, activity_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@bp.route('/grant-reward', methods=['POST'])
@login_required
@role_required('teacher')
def grant_reward():
    """
    奖励发放处理，写入rewards表
    """
    db = get_db()
    quarter = request.form.get('quarter')
    year = request.form.get('year')
    total_budget = request.form.get('total_budget')
    reward_name = request.form.get('reward_name')
    reward_type = request.form.get('reward_type')
    quantity = request.form.get('quantity')
    year = int(year) if year else None
    total_budget = float(total_budget) if total_budget else None
    quantity = int(quantity) if quantity else None
    db.execute('INSERT INTO rewards (quarter, year, total_budget, reward_name, reward_type, quantity) VALUES (?, ?, ?, ?, ?, ?)',
               (quarter, year, total_budget, reward_name, reward_type, quantity))
    db.commit()
    db.close()
    return redirect('/teacher/account') 