from flask import Blueprint, jsonify, request
import sqlite3
from datetime import datetime

admin_activity = Blueprint('admin_activity', __name__)

def get_db_connection():
    conn = sqlite3.connect('University_activit.db')
    conn.row_factory = sqlite3.Row
    return conn

@admin_activity.route('/api/admin/pending-activities', methods=['GET'])
def get_pending_activities():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取待审批的活动和场地申请信息
    cursor.execute('''
        SELECT 
            a.activity_id, 
            a.activity_name, 
            a.description, 
            a.start_time, 
            a.end_time,
            a.max_participants,
            u.name as organizer_name,
            v.venue_name,
            vb.booking_id,
            vb.booking_status,
            vb.created_at as applied_at
        FROM activities a
        JOIN users u ON a.organizer_id = u.user_id
        JOIN venue_bookings vb ON a.activity_id = vb.activity_id
        JOIN venues v ON vb.venue_id = v.venue_id
        WHERE vb.booking_status = 'pending'
        AND a.start_time > datetime('now')
        ORDER BY vb.created_at DESC
    ''')
    
    activities = cursor.fetchall()
    
    # 转换为JSON格式
    result = []
    for activity in activities:
        # 转换时间格式
        start_time = datetime.fromisoformat(activity['start_time'])
        end_time = datetime.fromisoformat(activity['end_time'])
        applied_at = datetime.fromisoformat(activity['applied_at'])
        
        result.append({
            'activity_id': activity['activity_id'],
            'activity_name': activity['activity_name'],
            'description': activity['description'],
            'start_time': start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': end_time.strftime('%Y-%m-%d %H:%M'),
            'max_participants': activity['max_participants'],
            'organizer_name': activity['organizer_name'],
            'venue_name': activity['venue_name'],
            'booking_id': activity['booking_id'],
            'booking_status': activity['booking_status'],
            'applied_at': applied_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': get_time_ago(applied_at)
        })
    
    conn.close()
    return jsonify(result)

def get_time_ago(dt):
    """计算时间差的人性化表示"""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"

@admin_activity.route('/api/admin/approve-venue', methods=['POST'])
def approve_venue():
    data = request.get_json()
    booking_id = data.get('booking_id')
    activity_id = data.get('activity_id')
    admin_id = data.get('admin_id')  # 从session或token中获取
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 更新场地预约状态
        cursor.execute('''
            UPDATE venue_bookings 
            SET booking_status = 'approved', admin_id = ?
            WHERE booking_id = ?
        ''', (admin_id, booking_id))
        
        # 更新活动状态
        cursor.execute('''
            UPDATE activities 
            SET status = 'approved', admin_id = ?
            WHERE activity_id = ?
        ''', (admin_id, activity_id))
        
        # 创建通知
        cursor.execute('''
            INSERT INTO notifications (recipient_id, sender_id, title, content, notification_type)
            SELECT organizer_id, ?, '活动场地申请已通过', 
                   '您的活动场地申请已通过审核，请按计划开展活动。', 'activity'
            FROM activities WHERE activity_id = ?
        ''', (admin_id, activity_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '场地申请已通过'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_activity.route('/api/admin/reject-venue', methods=['POST'])
def reject_venue():
    data = request.get_json()
    booking_id = data.get('booking_id')
    activity_id = data.get('activity_id')
    admin_id = data.get('admin_id')  # 从session或token中获取
    reason = data.get('reason', '未提供拒绝原因')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 更新场地预约状态
        cursor.execute('''
            UPDATE venue_bookings 
            SET booking_status = 'rejected', admin_id = ?
            WHERE booking_id = ?
        ''', (admin_id, booking_id))
        
        # 更新活动状态
        cursor.execute('''
            UPDATE activities 
            SET status = 'cancelled', admin_id = ?
            WHERE activity_id = ?
        ''', (admin_id, activity_id))
        
        # 创建通知
        cursor.execute('''
            INSERT INTO notifications (recipient_id, sender_id, title, content, notification_type)
            SELECT organizer_id, ?, '活动场地申请被拒绝', 
                   '您的活动场地申请未通过审核。原因：' || ?, 'activity'
            FROM activities WHERE activity_id = ?
        ''', (admin_id, reason, activity_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '场地申请已拒绝'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500 