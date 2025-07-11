import sqlite3
from datetime import datetime, timedelta
import random

def init_database():
    """初始化高校活动管理系统数据库"""
    conn = sqlite3.connect('University_activit.db')
    cursor = conn.cursor()
    
    # 创建所有表
    create_tables(cursor)
    
    # 插入示例数据
    insert_sample_data(cursor)
    
    conn.commit()
    conn.close()
    print("数据库初始化完成！")

def create_tables(cursor):
    """创建所有数据表"""
    
    # 1. 用户基础信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT NOT NULL CHECK (user_type IN ('student', 'teacher')),
            name TEXT NOT NULL,
            college TEXT NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. 学生信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY,
            student_number TEXT UNIQUE NOT NULL,
            grade INTEGER NOT NULL,
            major TEXT NOT NULL,
            class_name TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            leave_records TEXT,
            activity_completion_rate REAL DEFAULT 0.0,
            FOREIGN KEY (student_id) REFERENCES users(user_id)
        )
    ''')
    
    # 3. 教师信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id INTEGER PRIMARY KEY,
            employee_number TEXT UNIQUE NOT NULL,
            position TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            FOREIGN KEY (teacher_id) REFERENCES users(user_id)
        )
    ''')
    
    # 4. 学生特长表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_skills (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            skill_level INTEGER DEFAULT 1,
            acquired_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    ''')
    
    # 5. 学生课表表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_schedule (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL CHECK (weekday >= 1 AND weekday <= 7),
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            course_name TEXT,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    ''')
    
    # 6. 活动基础信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            organizer_id INTEGER NOT NULL,
            supervisor_id INTEGER,
            admin_id INTEGER,
            activity_name TEXT NOT NULL,
            description TEXT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            required_skills TEXT,
            participant_count INTEGER DEFAULT 0,
            max_participants INTEGER NOT NULL,
            status TEXT DEFAULT 'planning' CHECK (status IN ('planning', 'pending_review', 'approved', 'in_progress', 'completed', 'cancelled')),
            applied_funds REAL DEFAULT 0.0,
            allocated_funds REAL DEFAULT 0.0,
            remaining_funds REAL DEFAULT 0.0,
            activity_type TEXT CHECK (activity_type IN ('indoor', 'outdoor')),
            total_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organizer_id) REFERENCES students(student_id),
            FOREIGN KEY (supervisor_id) REFERENCES teachers(teacher_id),
            FOREIGN KEY (admin_id) REFERENCES teachers(teacher_id)
        )
    ''')
    
    # 7. 活动参与信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_participants (
            participation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT DEFAULT 'applied' CHECK (status IN ('applied', 'approved', 'rejected', 'withdrawn', 'completed')),
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            completed_at TIMESTAMP,
            feedback TEXT,
            FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    ''')
    
    # 8. 活动进度信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_progress (
            progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            progress_content TEXT NOT NULL,
            completion_percentage REAL DEFAULT 0.0,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewer_id INTEGER,
            review_status TEXT DEFAULT 'pending' CHECK (review_status IN ('pending', 'approved', 'rejected')),
            interrupt_request INTEGER DEFAULT 0,
            FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
            FOREIGN KEY (participant_id) REFERENCES students(student_id),
            FOREIGN KEY (reviewer_id) REFERENCES teachers(teacher_id)
        )
    ''')
    
    # 9. 场地基础信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS venues (
            venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            venue_name TEXT NOT NULL,
            location TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            facilities TEXT,
            status TEXT DEFAULT 'available' CHECK (status IN ('available', 'maintenance', 'unavailable'))
        )
    ''')
    
    # 10. 场地预约信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS venue_bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            venue_id INTEGER NOT NULL,
            activity_id INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            booking_status TEXT DEFAULT 'pending' CHECK (booking_status IN ('pending', 'approved', 'rejected', 'cancelled')),
            organizer_id INTEGER NOT NULL,
            admin_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (venue_id) REFERENCES venues(venue_id),
            FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
            FOREIGN KEY (organizer_id) REFERENCES students(student_id),
            FOREIGN KEY (admin_id) REFERENCES teachers(teacher_id)
        )
    ''')
    
    # 11. 活动评价信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_evaluations (
            evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
            FOREIGN KEY (participant_id) REFERENCES students(student_id)
        )
    ''')
    
    # 12. 奖励信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rewards (
            reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
            quarter TEXT NOT NULL,
            year INTEGER NOT NULL,
            total_budget REAL NOT NULL,
            reward_name TEXT NOT NULL,
            reward_type TEXT CHECK (reward_type IN ('money', 'material', 'certificate', 'other')),
            quantity INTEGER DEFAULT 1
        )
    ''')
    
    # 13. 奖励分配信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reward_distributions (
            distribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reward_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            supervisor_id INTEGER NOT NULL,
            distribution_status TEXT DEFAULT 'pending' CHECK (distribution_status IN ('pending', 'distributed', 'cancelled')),
            distributed_at TIMESTAMP,
            FOREIGN KEY (reward_id) REFERENCES rewards(reward_id),
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (supervisor_id) REFERENCES teachers(teacher_id)
        )
    ''')
    
    # 14. 参与者评价表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participant_evaluations (
            evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            organizer_id INTEGER NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
            FOREIGN KEY (participant_id) REFERENCES students(student_id),
            FOREIGN KEY (organizer_id) REFERENCES students(student_id)
        )
    ''')
    
    # 15. 组织者评价表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizer_evaluations (
            evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            organizer_id INTEGER NOT NULL,
            evaluator_id INTEGER NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
            FOREIGN KEY (organizer_id) REFERENCES students(student_id),
            FOREIGN KEY (evaluator_id) REFERENCES teachers(teacher_id)
        )
    ''')
    
    # 16. 组织者更换信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizer_changes (
            change_id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            original_organizer_id INTEGER NOT NULL,
            new_organizer_id INTEGER NOT NULL,
            reason TEXT,
            change_status TEXT DEFAULT 'pending' CHECK (change_status IN ('pending', 'approved', 'rejected')),
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
            FOREIGN KEY (original_organizer_id) REFERENCES students(student_id),
            FOREIGN KEY (new_organizer_id) REFERENCES students(student_id)
        )
    ''')
    
    # 17. 系统通知表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_id INTEGER NOT NULL,
            sender_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            notification_type TEXT CHECK (notification_type IN ('system', 'activity', 'evaluation', 'reward')),
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recipient_id) REFERENCES users(user_id),
            FOREIGN KEY (sender_id) REFERENCES users(user_id)
        )
    ''')
    
    print("数据表创建完成！")

def insert_sample_data(cursor):
    """插入示例数据"""
    
    # 插入用户基础信息
    users_data = [
        # 学生用户
        ('student', '张三', '计算机学院', 'password123', '13800138001'),
        ('student', '李四', '计算机学院', 'password123', '13800138002'),
        ('student', '王五', '电子工程学院', 'password123', '13800138003'),
        ('student', '赵六', '艺术学院', 'password123', '13800138004'),
        ('student', '孙七', '体育学院', 'password123', '13800138005'),
        # 教师用户
        ('teacher', '陈老师', '计算机学院', 'teacher123', '13900139001'),
        ('teacher', '刘老师', '电子工程学院', 'teacher123', '13900139002'),
        ('teacher', '杨老师', '艺术学院', 'teacher123', '13900139003'),
        ('teacher', '管理员', '学生处', 'admin123', '13900139004'),
    ]
    
    cursor.executemany('''
        INSERT INTO users (user_type, name, college, password, phone) 
        VALUES (?, ?, ?, ?, ?)
    ''', users_data)
    
    # 插入学生信息
    students_data = [
        (1, '2021001', 2021, '计算机科学与技术', '计科1班', 85, None, 0.8),
        (2, '2021002', 2021, '软件工程', '软工1班', 90, None, 0.9),
        (3, '2020001', 2020, '电子信息工程', '电信1班', 88, None, 0.7),
        (4, '2022001', 2022, '音乐表演', '音乐1班', 92, None, 0.85),
        (5, '2021003', 2021, '体育教育', '体育1班', 86, None, 0.75),
    ]
    
    cursor.executemany('''
        INSERT INTO students (student_id, student_number, grade, major, class_name, score, leave_records, activity_completion_rate) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', students_data)
    
    # 插入教师信息
    teachers_data = [
        (6, 'T001', '副教授', 0),
        (7, 'T002', '讲师', 0),
        (8, 'T003', '助教', 0),
        (9, 'T004', '主任', 1),  # 管理员
    ]
    
    cursor.executemany('''
        INSERT INTO teachers (teacher_id, employee_number, position, is_admin) 
        VALUES (?, ?, ?, ?)
    ''', teachers_data)
    
    # 插入学生特长
    skills_data = [
        (1, '编程', 3),
        (1, '设计', 2),
        (2, '编程', 4),
        (2, '项目管理', 3),
        (3, '硬件开发', 3),
        (4, '声乐', 4),
        (4, '舞蹈', 3),
        (5, '篮球', 4),
        (5, '足球', 3),
    ]
    
    cursor.executemany('''
        INSERT INTO student_skills (student_id, skill_name, skill_level) 
        VALUES (?, ?, ?)
    ''', skills_data)
    
    # 插入学生课表
    schedule_data = [
        (1, 1, '08:00', '09:30', '数据结构'),
        (1, 1, '10:00', '11:30', '算法分析'),
        (1, 3, '14:00', '15:30', '数据库原理'),
        (2, 2, '08:00', '09:30', '软件工程'),
        (2, 4, '10:00', '11:30', '项目管理'),
        (3, 1, '08:00', '09:30', '信号与系统'),
        (3, 3, '14:00', '15:30', '数字电路'),
        (4, 2, '08:00', '09:30', '声乐基础'),
        (4, 4, '14:00', '15:30', '舞蹈编排'),
        (5, 1, '08:00', '09:30', '运动生理学'),
        (5, 3, '14:00', '15:30', '篮球训练'),
    ]
    
    cursor.executemany('''
        INSERT INTO student_schedule (student_id, weekday, start_time, end_time, course_name) 
        VALUES (?, ?, ?, ?, ?)
    ''', schedule_data)
    
    # 插入场地信息
    venues_data = [
        ('学术报告厅', '行政楼3楼', 200, '投影仪,音响,麦克风', 'available'),
        ('体育馆', '体育中心', 500, '篮球场,音响,更衣室', 'available'),
        ('艺术活动室', '艺术楼2楼', 50, '钢琴,音响,镜子', 'available'),
        ('多媒体教室', '教学楼A101', 100, '投影仪,电脑,音响', 'available'),
        ('户外广场', '学生活动中心前', 1000, '舞台,音响,电源', 'available'),
    ]
    
    cursor.executemany('''
        INSERT INTO venues (venue_name, location, capacity, facilities, status) 
        VALUES (?, ?, ?, ?, ?)
    ''', venues_data)
    
    # 插入活动信息
    activities_data = [
        (1, 6, 9, '编程竞赛', '面向全校学生的编程竞赛活动', 
         datetime.now() + timedelta(days=7), datetime.now() + timedelta(days=14),
         '编程', 0, 50, 'approved', 5000.0, 4000.0, 3500.0, 'indoor', 0),
        (2, 7, 9, '音乐会', '校园音乐会表演活动', 
         datetime.now() + timedelta(days=10), datetime.now() + timedelta(days=10, hours=3),
         '声乐,舞蹈', 0, 30, 'approved', 3000.0, 2500.0, 2000.0, 'indoor', 0),
        (3, 8, 9, '体育节', '校园体育节活动', 
         datetime.now() + timedelta(days=15), datetime.now() + timedelta(days=17),
         '篮球,足球', 0, 100, 'pending_review', 8000.0, 0.0, 0.0, 'outdoor', 0),
    ]
    
    cursor.executemany('''
        INSERT INTO activities (organizer_id, supervisor_id, admin_id, activity_name, description, 
                               start_time, end_time, required_skills, participant_count, max_participants, 
                               status, applied_funds, allocated_funds, remaining_funds, activity_type, total_score) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', activities_data)
    
    # 插入活动参与信息
    participants_data = [
        (1, 1, 'approved', datetime.now() - timedelta(days=1), datetime.now()),
        (1, 2, 'approved', datetime.now() - timedelta(days=1), datetime.now()),
        (2, 4, 'approved', datetime.now() - timedelta(days=2), datetime.now()),
        (2, 5, 'applied', datetime.now() - timedelta(hours=5), None),
        (3, 5, 'applied', datetime.now() - timedelta(hours=2), None),
    ]
    
    cursor.executemany('''
        INSERT INTO activity_participants (activity_id, student_id, status, applied_at, approved_at) 
        VALUES (?, ?, ?, ?, ?)
    ''', participants_data)
    
    # 插入场地预约信息
    bookings_data = [
        (4, 1, datetime.now() + timedelta(days=7), datetime.now() + timedelta(days=14), 'approved', 1, 9),
        (3, 2, datetime.now() + timedelta(days=10), datetime.now() + timedelta(days=10, hours=3), 'approved', 2, 9),
        (2, 3, datetime.now() + timedelta(days=15), datetime.now() + timedelta(days=17), 'pending', 3, None),
    ]
    
    cursor.executemany('''
        INSERT INTO venue_bookings (venue_id, activity_id, start_time, end_time, booking_status, organizer_id, admin_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', bookings_data)
    
    # 插入奖励信息
    rewards_data = [
        ('Q1', 2024, 10000.0, '优秀组织奖', 'certificate', 10),
        ('Q1', 2024, 5000.0, '活动参与奖', 'money', 50),
        ('Q2', 2024, 15000.0, '创新活动奖', 'material', 20),
    ]
    
    cursor.executemany('''
        INSERT INTO rewards (quarter, year, total_budget, reward_name, reward_type, quantity) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', rewards_data)
    
    # 插入活动进度信息
    progress_data = [
        (1, 1, '准备阶段：完成题目设计和测试环境搭建', 30.0, datetime.now() - timedelta(days=2), 6, 'approved'),
        (1, 2, '准备阶段：完成个人技能评估', 25.0, datetime.now() - timedelta(days=1), 6, 'approved'),
        (2, 4, '排练阶段：完成个人曲目练习', 40.0, datetime.now() - timedelta(days=3), 7, 'approved'),
        (2, 4, '排练阶段：参与合唱排练', 70.0, datetime.now() - timedelta(days=1), 7, 'pending'),
        (3, 5, '报名阶段：完成个人信息登记', 20.0, datetime.now() - timedelta(hours=12), 8, 'pending'),
    ]
    
    cursor.executemany('''
        INSERT INTO activity_progress (activity_id, participant_id, progress_content, completion_percentage, 
                                     submitted_at, reviewer_id, review_status) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', progress_data)
    
    # 插入活动评价信息
    activity_evaluations_data = [
        (1, 1, 4, '活动组织得很好，题目有挑战性'),
        (1, 2, 5, '非常有意义的活动，学到了很多'),
        (2, 4, 5, '音乐会很精彩，参与体验很好'),
    ]
    
    cursor.executemany('''
        INSERT INTO activity_evaluations (activity_id, participant_id, rating, comment) 
        VALUES (?, ?, ?, ?)
    ''', activity_evaluations_data)
    
    # 插入奖励分配信息
    reward_distributions_data = [
        (1, 1, 6, 'distributed', datetime.now() - timedelta(days=10)),
        (1, 2, 6, 'distributed', datetime.now() - timedelta(days=10)),
        (2, 4, 7, 'pending', None),
        (2, 5, 8, 'pending', None),
        (3, 3, 8, 'distributed', datetime.now() - timedelta(days=5)),
    ]
    
    cursor.executemany('''
        INSERT INTO reward_distributions (reward_id, student_id, supervisor_id, distribution_status, distributed_at) 
        VALUES (?, ?, ?, ?, ?)
    ''', reward_distributions_data)
    
    # 插入参与者评价信息
    participant_evaluations_data = [
        (1, 1, 1, 4, '积极参与，完成质量高'),
        (1, 2, 1, 5, '表现优秀，团队合作能力强'),
        (2, 4, 2, 5, '专业水平高，表演出色'),
        (3, 5, 3, 3, '参与度一般，需要加强'),
    ]
    
    cursor.executemany('''
        INSERT INTO participant_evaluations (activity_id, participant_id, organizer_id, rating, comment) 
        VALUES (?, ?, ?, ?, ?)
    ''', participant_evaluations_data)
    
    # 插入组织者评价信息
    organizer_evaluations_data = [
        (1, 1, 6, 5, '组织能力强，活动策划周密'),
        (2, 2, 7, 4, '活动执行良好，但沟通有待加强'),
        (3, 3, 8, 3, '活动申请材料不够完善'),
    ]
    
    cursor.executemany('''
        INSERT INTO organizer_evaluations (activity_id, organizer_id, evaluator_id, rating, comment) 
        VALUES (?, ?, ?, ?, ?)
    ''', organizer_evaluations_data)
    
    # 插入组织者更换信息
    organizer_changes_data = [
        (3, 3, 5, '原组织者因个人原因无法继续', 'pending', datetime.now() - timedelta(days=1), None),
    ]
    
    cursor.executemany('''
        INSERT INTO organizer_changes (activity_id, original_organizer_id, new_organizer_id, reason, 
                                     change_status, requested_at, processed_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', organizer_changes_data)
    
    # 插入通知信息
    notifications_data = [
        (1, 9, '活动申请通过', '您申请的编程竞赛活动已经通过审核', 'activity', 1),
        (2, 9, '活动申请通过', '您申请的音乐会活动已经通过审核', 'activity', 1),
        (3, 9, '活动申请待审核', '您申请的体育节活动正在审核中', 'activity', 0),
        (4, 6, '活动邀请', '邀请您参加音乐会活动', 'activity', 0),
        (5, 8, '活动邀请', '邀请您参加体育节活动', 'activity', 0),
        (1, 6, '进度审核通过', '您的活动进度已审核通过', 'activity', 1),
        (2, 7, '进度审核通过', '您的活动进度已审核通过', 'activity', 1),
        (4, 7, '进度待审核', '您的活动进度正在审核中', 'activity', 0),
        (1, 9, '奖励发放', '您的优秀组织奖已发放', 'reward', 1),
        (2, 9, '奖励发放', '您的优秀组织奖已发放', 'reward', 1),
        (4, 9, '奖励待发放', '您的活动参与奖待发放', 'reward', 0),
        (5, 9, '奖励待发放', '您的活动参与奖待发放', 'reward', 0),
        (6, 9, '系统消息', '欢迎使用高校活动管理系统', 'system', 1),
        (7, 9, '系统消息', '欢迎使用高校活动管理系统', 'system', 1),
        (8, 9, '系统消息', '欢迎使用高校活动管理系统', 'system', 1),
    ]
    
    cursor.executemany('''
        INSERT INTO notifications (recipient_id, sender_id, title, content, notification_type, is_read) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', notifications_data)
    
    



if __name__ == "__main__":
    # 初始化数据库
    init_database()
