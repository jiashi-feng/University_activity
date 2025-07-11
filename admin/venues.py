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
        
        # 获取所有预约信息
        venue_bookings = get_all_bookings(conn)
        
        # 为每个场地添加当前预约信息
        for venue in venues:
            current_booking = get_current_booking(conn, venue['venue_id'])
            venue['current_booking'] = dict_from_row(current_booking) if current_booking else None
        
        # 添加管理员信息
        admin_info = {
            'name': session.get('username'),
            'college': session.get('college')
        }
        
        return render_template('admin/venues.html', 
                            venues=venues,
                            venue_stats=stats,
                            venue_bookings=venue_bookings,
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
    booking = cursor.fetchone()
    if booking:
        booking_dict = dict_from_row(booking)
        return convert_datetime_fields(booking_dict)
    return None

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

def convert_datetime_fields(booking_dict):
    """将预约信息中的时间字符串转换为datetime对象"""
    if not booking_dict:
        return booking_dict
    
    datetime_fields = ['start_time', 'end_time', 'created_at']
    for field in datetime_fields:
        if field in booking_dict and booking_dict[field]:
            try:
                booking_dict[field] = datetime.fromisoformat(booking_dict[field])
            except (ValueError, TypeError):
                # 如果转换失败，保持原值
                pass
    return booking_dict

def get_all_bookings(conn):
    """获取所有预约信息"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            vb.*,
            v.venue_name,
            a.activity_name,
            a.max_participants as expected_participants
        FROM venue_bookings vb
        JOIN venues v ON vb.venue_id = v.venue_id
        JOIN activities a ON vb.activity_id = a.activity_id
        WHERE vb.start_time >= datetime('now', '-1 day')
        ORDER BY vb.start_time DESC
        LIMIT 50
    ''')
    bookings = [dict_from_row(row) for row in cursor.fetchall()]
    return [convert_datetime_fields(booking) for booking in bookings]

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
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '未接收到数据'}), 400

        # 验证必需的字段
        required_fields = ['venue_name', 'location', 'capacity', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'缺少必需字段：{field}'}), 400

        # 验证数据类型
        try:
            capacity = int(data['capacity'])
            if capacity <= 0:
                return jsonify({'status': 'error', 'message': '容量必须大于0'}), 400
        except ValueError:
            return jsonify({'status': 'error', 'message': '容量必须是有效的数字'}), 400

        # 验证状态值
        valid_statuses = ['available', 'maintenance', 'unavailable']
        if data['status'] not in valid_statuses:
            return jsonify({'status': 'error', 'message': '无效的状态值'}), 400

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # 首先检查场地是否存在
            cursor.execute('SELECT venue_id FROM venues WHERE venue_id = ?', (venue_id,))
            if not cursor.fetchone():
                return jsonify({'status': 'error', 'message': '场地不存在'}), 404

            # 更新场地信息
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
                capacity,
                data.get('facilities', ''),  # 设施是可选的
                data['status'],
                venue_id
            ))
            
            if cursor.rowcount == 0:
                return jsonify({'status': 'error', 'message': '更新失败，没有记录被修改'}), 400

            conn.commit()
            return jsonify({'status': 'success', 'message': '场地信息更新成功'})
            
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': f'数据库错误：{str(e)}'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'服务器错误：{str(e)}'}), 500

@venues_bp.route('/api/venues/<int:venue_id>/book', methods=['POST'])
@admin_required
def book_venue(venue_id):
    """预约场地"""
    data = request.get_json()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 检查场地是否可用
        cursor.execute('SELECT status, capacity FROM venues WHERE venue_id = ?', (venue_id,))
        venue = cursor.fetchone()
        
        if not venue:
            return jsonify({'status': 'error', 'message': '场地不存在'})
        
        if venue['status'] != 'available':
            return jsonify({'status': 'error', 'message': '场地当前不可用'})
        
        # 检查预约时间是否有冲突
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        
        cursor.execute('''
            SELECT COUNT(*) as count FROM venue_bookings
            WHERE venue_id = ?
            AND booking_status = 'approved'
            AND NOT (end_time <= ? OR start_time >= ?)
        ''', (venue_id, start_time.isoformat(), end_time.isoformat()))
        
        if cursor.fetchone()['count'] > 0:
            return jsonify({'status': 'error', 'message': '所选时间段已被预约'})
        
        # 检查预计人数是否超过场地容量
        if int(data['expected_participants']) > venue['capacity']:
            return jsonify({'status': 'error', 'message': '预计人数超过场地容量'})
        
        # 创建活动记录
        cursor.execute('''
            INSERT INTO activities (
                organizer_id,
                admin_id,
                activity_name,
                start_time,
                end_time,
                max_participants,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, 'approved')
        ''', (
            session['user_id'],
            session['user_id'],
            data['activity_name'],
            start_time.isoformat(),
            end_time.isoformat(),
            data['expected_participants'],
        ))
        
        activity_id = cursor.lastrowid
        
        # 创建场地预约记录
        cursor.execute('''
            INSERT INTO venue_bookings (
                venue_id,
                activity_id,
                start_time,
                end_time,
                booking_status,
                organizer_id,
                admin_id
            ) VALUES (?, ?, ?, ?, 'approved', ?, ?)
        ''', (
            venue_id,
            activity_id,
            start_time.isoformat(),
            end_time.isoformat(),
            session['user_id'],
            session['user_id']
        ))
        
        conn.commit()
        return jsonify({'status': 'success', 'message': '场地预约成功'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        conn.close()

@venues_bp.route('/api/venues/<int:venue_id>/bookings')
@admin_required
def get_venue_bookings(venue_id):
    """获取场地预约信息"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT vb.*, a.activity_name, u.name as organizer_name
            FROM venue_bookings vb
            JOIN activities a ON vb.activity_id = a.activity_id
            JOIN users u ON vb.organizer_id = u.user_id
            WHERE vb.venue_id = ?
            AND vb.start_time >= datetime('now', '-1 day')
            ORDER BY vb.start_time
        ''', (venue_id,))
        
        bookings = [dict_from_row(row) for row in cursor.fetchall()]
        bookings = [convert_datetime_fields(booking) for booking in bookings]
        return jsonify({'status': 'success', 'bookings': bookings})
    finally:
        conn.close() 