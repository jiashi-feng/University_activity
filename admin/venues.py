from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
import sqlite3
from functools import wraps

# 修改蓝图名称为'admin_venues'，保持URL前缀
venues_bp = Blueprint('admin_venues', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'teacher' or not session.get('is_admin'):
            flash('需要管理员权限', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    conn = sqlite3.connect('University_activit.db')
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    """将sqlite3.Row对象转换为可修改的字典"""
    if row is None:
        return None
    return dict(zip(row.keys(), row))

@venues_bp.route('/venues')
@admin_required
def venues_page():
    """场地管理页面"""
    conn = get_db_connection()
    try:
        # 获取所有场地信息并转换为可修改的字典
        venues = [dict_from_row(row) for row in get_all_venues(conn)]
        # 获取场地统计信息
        stats = dict_from_row(get_venue_stats(conn))
        # 获取今日预约信息
        today_bookings = [dict_from_row(row) for row in get_today_bookings(conn)]
        
        # 为每个场地添加当前预约信息
        for venue in venues:
            current_booking = get_current_booking(conn, venue['venue_id'])
            venue['current_booking'] = dict_from_row(current_booking) if current_booking else None
            venue['bookings'] = get_venue_bookings_by_hour(conn, venue['venue_id'])
        
        # 添加管理员信息
        admin_info = {
            'name': session.get('username'),
            'college': session.get('college')
        }
        
        return render_template('admin/venues.html', 
                            venues=venues,
                            venue_stats=stats,
                            admin_info=admin_info)
    finally:
        conn.close()

def get_all_venues(conn):
    """获取所有场地信息"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM venues
        ORDER BY venue_name
    ''')
    return cursor.fetchall()

def get_venue_stats(conn):
    """获取场地统计信息"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available,
            SUM(CASE WHEN status = 'maintenance' THEN 1 ELSE 0 END) as maintenance,
            SUM(CASE WHEN status = 'unavailable' THEN 1 ELSE 0 END) as unavailable
        FROM venues
    ''')
    return cursor.fetchone()

def get_today_bookings(conn):
    """获取今日场地预约信息"""
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute('''
        SELECT vb.*, v.venue_name, a.activity_name
        FROM venue_bookings vb
        JOIN venues v ON vb.venue_id = v.venue_id
        JOIN activities a ON vb.activity_id = a.activity_id
        WHERE DATE(vb.start_time) = ?
        AND vb.booking_status = 'approved'
        ORDER BY vb.start_time
    ''', (today.isoformat(),))
    return cursor.fetchall()

def get_current_booking(conn, venue_id):
    """获取场地当前预约信息"""
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute('''
        SELECT vb.*, a.activity_name
        FROM venue_bookings vb
        JOIN activities a ON vb.activity_id = a.activity_id
        WHERE vb.venue_id = ?
        AND vb.booking_status = 'approved'
        AND ? BETWEEN vb.start_time AND vb.end_time
        LIMIT 1
    ''', (venue_id, now.isoformat()))
    return cursor.fetchone()

def get_venue_bookings_by_hour(conn, venue_id):
    """获取场地按小时的预约信息"""
    cursor = conn.cursor()
    today = datetime.now().date()
    bookings = {}
    
    cursor.execute('''
        SELECT vb.*, a.activity_name
        FROM venue_bookings vb
        JOIN activities a ON vb.activity_id = a.activity_id
        WHERE vb.venue_id = ?
        AND DATE(vb.start_time) = ?
        AND vb.booking_status = 'approved'
    ''', (venue_id, today.isoformat()))
    
    rows = cursor.fetchall()
    for row in rows:
        start_hour = datetime.fromisoformat(row['start_time']).hour
        end_hour = datetime.fromisoformat(row['end_time']).hour
        for hour in range(start_hour, end_hour + 1):
            if 8 <= hour < 22:  # 只记录8:00-22:00的时间段
                bookings[hour] = {
                    'activity_name': row['activity_name'],
                    'booking_id': row['booking_id']
                }
    return bookings

@venues_bp.route('/api/venues', methods=['POST'])
@admin_required
def add_venue():
    """添加新场地"""
    data = request.get_json()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO venues (venue_name, location, capacity, facilities, status)
            VALUES (?, ?, ?, ?, 'available')
        ''', (
            data['venue_name'],
            data['location'],
            data['capacity'],
            data['facilities']
        ))
        conn.commit()
        return jsonify({'status': 'success', 'message': '场地添加成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        conn.close()

@venues_bp.route('/api/venues/<int:venue_id>', methods=['GET'])
@admin_required
def get_venue_details(venue_id):
    """获取场地详细信息"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 获取场地基本信息
        cursor.execute('SELECT * FROM venues WHERE venue_id = ?', (venue_id,))
        venue = cursor.fetchone()
        
        if not venue:
            return jsonify({'status': 'error', 'message': '场地不存在'})
        
        # 获取未来7天的预约信息
        cursor.execute('''
            SELECT vb.*, a.activity_name
            FROM venue_bookings vb
            JOIN activities a ON vb.activity_id = a.activity_id
            WHERE vb.venue_id = ?
            AND vb.start_time >= datetime('now')
            AND vb.start_time <= datetime('now', '+7 days')
            AND vb.booking_status = 'approved'
            ORDER BY vb.start_time
        ''', (venue_id,))
        bookings = cursor.fetchall()
        
        return jsonify({
            'status': 'success',
            'venue': dict(venue),
            'bookings': [dict(booking) for booking in bookings]
        })
    finally:
        conn.close()

@venues_bp.route('/api/venues/<int:venue_id>', methods=['PUT'])
@admin_required
def update_venue(venue_id):
    """更新场地信息"""
    data = request.get_json()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE venues
            SET venue_name = ?,
                location = ?,
                capacity = ?,
                facilities = ?,
                status = ?
            WHERE venue_id = ?
        ''', (
            data['venue_name'],
            data['location'],
            data['capacity'],
            data['facilities'],
            data['status'],
            venue_id
        ))
        conn.commit()
        return jsonify({'status': 'success', 'message': '场地信息更新成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        conn.close() 