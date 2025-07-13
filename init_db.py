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
    
    # 16. 参与者评价表
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
    
    # 17. 组织者更换信息表
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
    
    # 丰富用户基础信息
    users_data = [
        # 学生用户
        ('student', '张三', '计算机学院', 'password123', '13800138001'),
        ('student', '李四', '计算机学院', 'password123', '13800138002'),
        ('student', '王五', '电子工程学院', 'password123', '13800138003'),
        ('student', '赵六', '艺术学院', 'password123', '13800138004'),
        ('student', '孙七', '体育学院', 'password123', '13800138005'),
        ('student', '周八', '人工智能学院', 'password123', '13800138006'),
        ('student', '吴九', '网络工程学院', 'password123', '13800138007'),
        ('student', '郑十', '物联网学院', 'password123', '13800138008'),
        ('student', '钱十一', '管理学院', 'password123', '13800138009'),
        ('student', '冯十二', '外国语学院', 'password123', '13800138010'),
        # 教师用户
        ('teacher', '陈老师', '计算机学院', 'teacher123', '13900139001'),
        ('teacher', '刘老师', '电子工程学院', 'teacher123', '13900139002'),
        ('teacher', '杨老师', '艺术学院', 'teacher123', '13900139003'),
        ('teacher', '管理员', '学生处', 'admin123', '13900139004'),
        ('teacher', '王老师', '人工智能学院', 'teacher123', '13900139005'),
        ('teacher', '李老师', '网络工程学院', 'teacher123', '13900139006'),
        ('teacher', '赵老师', '管理学院', 'teacher123', '13900139007'),
        ('teacher', '钱老师', '外国语学院', 'teacher123', '13900139008'),
        ('teacher', '李晓峰', '学生处', 'admin123', '13900139004'),
    ]
    cursor.executemany('''
        INSERT INTO users (user_type, name, college, password, phone) 
        VALUES (?, ?, ?, ?, ?)
    ''', users_data)

    # 丰富学生信息
    students_data = [
        (1, '2021001', 2021, '计算机科学与技术', '计科1班', 85, None, 0.8),
        (2, '2021002', 2021, '软件工程', '软工1班', 90, None, 0.9),
        (3, '2020001', 2020, '电子信息工程', '电信1班', 88, None, 0.7),
        (4, '2022001', 2022, '音乐表演', '音乐1班', 92, None, 0.85),
        (5, '2021003', 2021, '体育教育', '体育1班', 86, None, 0.75),
        (6, '2021007', 2021, '人工智能', 'AI1班', 95, None, 0.95),
        (7, '2021008', 2021, '网络工程', '网工1班', 80, None, 0.7),
        (8, '2021009', 2021, '物联网', '物联1班', 78, None, 0.6),
        (9, '2021010', 2021, '工商管理', '管1班', 82, None, 0.8),
        (10, '2021011', 2021, '英语', '英1班', 88, None, 0.9),
    ]
    cursor.executemany('''
        INSERT INTO students (student_id, student_number, grade, major, class_name, score, leave_records, activity_completion_rate) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', students_data)

    # 丰富教师信息
    teachers_data = [
        (11, 'T001', '副教授', 0),
        (12, 'T002', '讲师', 0),
        (13, 'T003', '助教', 0),
        (14, 'T004', '主任', 1),  # 管理员
        (15, 'T005', '教授', 0),
        (16, 'T006', '讲师', 0),
        (17, 'T007', '副教授', 0),
        (18, 'T008', '讲师', 0),
        (19, 'T009', '教授', 0),
        (20, 'T010', '讲师', 0),
    ]
    cursor.executemany('''
        INSERT INTO teachers (teacher_id, employee_number, position, is_admin) 
        VALUES (?, ?, ?, ?)
    ''', teachers_data)

    # 丰富活动信息
    activities_data = [
        (1, 1, 14, '编程竞赛', '面向全校学生的编程竞赛活动', datetime.now() + timedelta(days=7), datetime.now() + timedelta(days=14), '编程', 10, 50, 'approved', 5000.0, 4000.0, 3500.0, 'indoor', 0),
        (2, 2, 14, '音乐会', '校园音乐会表演活动', datetime.now() - timedelta(days=10), datetime.now() - timedelta(days=7), '声乐,舞蹈', 30, 30, 'completed', 3000.0, 2500.0, 0.0, 'indoor', 0),
        (3, 3, 14, '体育节', '校园体育节活动', datetime.now() + timedelta(days=1), datetime.now() + timedelta(days=2), '篮球,足球', 50, 100, 'in_progress', 8000.0, 6000.0, 2000.0, 'outdoor', 0),
        (4, 6, 11, 'AI创新大赛', '人工智能创新项目比赛', datetime.now() + timedelta(days=5), datetime.now() + timedelta(days=8), 'AI,编程', 20, 40, 'pending_review', 6000.0, 0.0, 0.0, 'indoor', 0),
        (5, 7, 12, '网络安全讲座', '网络安全知识普及讲座', datetime.now() + timedelta(days=3), datetime.now() + timedelta(days=3, hours=2), '网络,安全', 10, 60, 'cancelled', 2000.0, 0.0, 0.0, 'indoor', 0),
        (6, 8, 13, '物联网实训', '物联网设备实训活动', datetime.now() + timedelta(days=12), datetime.now() + timedelta(days=13), '物联网', 5, 30, 'approved', 4000.0, 3000.0, 1000.0, 'indoor', 0),
        (7, 9, 15, '管理论坛', '管理学院学术论坛', datetime.now() + timedelta(days=2), datetime.now() + timedelta(days=3), '管理', 15, 40, 'approved', 3500.0, 2000.0, 1500.0, 'indoor', 0),
        (8, 10, 16, '英语演讲比赛', '外国语学院英语演讲比赛', datetime.now() + timedelta(days=4), datetime.now() + timedelta(days=5), '英语', 12, 30, 'approved', 2500.0, 2000.0, 500.0, 'indoor', 0),
        (9, 1, 17, '创新创业大赛', '全校创新创业大赛', datetime.now() + timedelta(days=6), datetime.now() + timedelta(days=9), '创新,创业', 25, 60, 'pending_review', 7000.0, 0.0, 0.0, 'indoor', 0),
        (10, 2, 18, '外语配音大赛', '外国语学院配音大赛', datetime.now() + timedelta(days=8), datetime.now() + timedelta(days=9), '配音', 8, 25, 'approved', 1800.0, 1500.0, 300.0, 'indoor', 0),
        # 真实风格：申请中且未分配资金
        (1, 3, 14, '校园科技节', '展示学生科技创新成果的活动', datetime.now() + timedelta(days=10), datetime.now() + timedelta(days=12), '科技,创新', 0, 80, 'approved', 5000.0, 0.0, 0.0, 'indoor', 0),
        (2, 4, 11, '志愿服务活动', '社区志愿服务与公益宣传', datetime.now() + timedelta(days=15), datetime.now() + timedelta(days=16), '志愿,公益', 0, 60, 'approved', 2000.0, 0.0, 0.0, 'outdoor', 0),
        # 真实风格：申请中且已分配资金
        (3, 5, 12, '大学生创新创业讲座', '创业经验分享与项目路演', datetime.now() + timedelta(days=18), datetime.now() + timedelta(days=19), '创业,讲座', 0, 100, 'approved', 3000.0, 1500.0, 1500.0, 'indoor', 0),
        (4, 6, 13, '绿色校园环保行动', '环保知识宣传与实践', datetime.now() + timedelta(days=20), datetime.now() + timedelta(days=21), '环保,宣传', 0, 120, 'approved', 4000.0, 2000.0, 2000.0, 'outdoor', 0),
    ]
    cursor.executemany('''
        INSERT INTO activities (organizer_id, supervisor_id, admin_id, activity_name, description, start_time, end_time, required_skills, participant_count, max_participants, status, applied_funds, allocated_funds, remaining_funds, activity_type, total_score) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', activities_data)

    # 丰富活动参与信息
    participants_data = [
        (1, 1, 'approved', datetime.now() - timedelta(days=1), datetime.now()),
        (1, 2, 'approved', datetime.now() - timedelta(days=1), datetime.now()),
        (2, 3, 'completed', datetime.now() - timedelta(days=10), datetime.now() - timedelta(days=7)),
        (2, 4, 'completed', datetime.now() - timedelta(days=10), datetime.now() - timedelta(days=7)),
        (3, 5, 'approved', datetime.now() - timedelta(days=1), None),  # 修正此处
        (4, 6, 'applied', datetime.now() - timedelta(days=2), None),
        (5, 7, 'rejected', datetime.now() - timedelta(days=3), None),
        (6, 8, 'approved', datetime.now() - timedelta(days=4), datetime.now() - timedelta(days=3)),
        (7, 9, 'approved', datetime.now() - timedelta(days=5), datetime.now() - timedelta(days=4)),
        (8, 10, 'approved', datetime.now() - timedelta(days=6), datetime.now() - timedelta(days=5)),
        (9, 1, 'applied', datetime.now() - timedelta(days=7), None),
        (10, 2, 'approved', datetime.now() - timedelta(days=8), datetime.now() - timedelta(days=7)),
    ]
    cursor.executemany('''
        INSERT INTO activity_participants (activity_id, student_id, status, applied_at, approved_at) 
        VALUES (?, ?, ?, ?, ?)
    ''', participants_data)

    # 丰富活动进度信息
    progress_data = [
        (1, 1, '准备阶段：完成题目设计', 30.0, datetime.now() - timedelta(days=2), 11, 'approved'),
        (1, 2, '准备阶段：完成个人技能评估', 25.0, datetime.now() - timedelta(days=1), 11, 'pending'),
        (2, 3, '排练阶段：完成个人曲目练习', 100.0, datetime.now() - timedelta(days=3), 12, 'approved'),
        (3, 5, '报名阶段：完成个人信息登记', 20.0, datetime.now() - timedelta(hours=12), 13, 'rejected'),
        (4, 6, 'AI项目立项', 10.0, datetime.now() - timedelta(days=2), 15, 'pending'),
        (5, 7, '网络安全讲座准备', 50.0, datetime.now() - timedelta(days=1), 16, 'approved'),
        (6, 8, '物联网设备调试', 60.0, datetime.now() - timedelta(days=3), 17, 'pending'),
        (7, 9, '论坛宣传', 80.0, datetime.now() - timedelta(days=2), 18, 'approved'),
        (8, 10, '演讲稿撰写', 90.0, datetime.now() - timedelta(days=1), 19, 'approved'),
        (9, 1, '创业计划书提交', 40.0, datetime.now() - timedelta(days=4), 20, 'pending'),
        (10, 2, '配音样本录制', 70.0, datetime.now() - timedelta(days=3), 12, 'approved'),
    ]
    cursor.executemany('''
        INSERT INTO activity_progress (activity_id, participant_id, progress_content, completion_percentage, submitted_at, reviewer_id, review_status) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', progress_data)

    # 丰富组织者更换信息
    organizer_changes_data = [
        (1, 1, 2, '原组织者请假', 'pending', datetime.now() - timedelta(days=5), None),
        (2, 3, 4, '原组织者毕业', 'approved', datetime.now() - timedelta(days=10), datetime.now() - timedelta(days=9)),
        (3, 5, 6, '原组织者因个人原因无法继续', 'pending', datetime.now() - timedelta(days=1), None),
        (4, 7, 8, '原组织者调岗', 'rejected', datetime.now() - timedelta(days=3), datetime.now() - timedelta(days=2)),
        (5, 9, 10, '原组织者出国交流', 'pending', datetime.now() - timedelta(days=2), None),
        (6, 1, 3, '原组织者身体原因', 'approved', datetime.now() - timedelta(days=7), datetime.now() - timedelta(days=6)),
        (7, 2, 4, '原组织者家庭原因', 'pending', datetime.now() - timedelta(days=4), None),
        (8, 5, 6, '原组织者转专业', 'approved', datetime.now() - timedelta(days=8), datetime.now() - timedelta(days=7)),
        (9, 7, 8, '原组织者请假', 'pending', datetime.now() - timedelta(days=6), None),
        (10, 9, 10, '原组织者毕业', 'rejected', datetime.now() - timedelta(days=9), datetime.now() - timedelta(days=8)),
    ]
    cursor.executemany('''
        INSERT INTO organizer_changes (activity_id, original_organizer_id, new_organizer_id, reason, change_status, requested_at, processed_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', organizer_changes_data)

    # 丰富活动评价信息
    activity_evaluations_data = [
        (1, 1, 4, '活动组织得很好，题目有挑战性'),
        (1, 2, 5, '非常有意义的活动，学到了很多'),
        (2, 3, 5, '音乐会很精彩，参与体验很好'),
        (3, 4, 4, '体育节很有趣'),
        (4, 5, 3, 'AI创新大赛收获很大'),
        (5, 6, 5, '网络安全讲座内容丰富'),
        (6, 7, 4, '物联网实训很实用'),
        (7, 8, 5, '管理论坛干货满满'),
        (8, 9, 4, '英语演讲比赛锻炼了口语'),
        (9, 10, 5, '创新创业大赛激发了灵感'),
        (10, 1, 4, '配音大赛很有趣'),
    ]
    cursor.executemany('''
        INSERT INTO activity_evaluations (activity_id, participant_id, rating, comment) 
        VALUES (?, ?, ?, ?)
    ''', activity_evaluations_data)

    # 丰富组织者评价信息
    organizer_evaluations_data = [
        (1, 1, 11, 5, '组织能力强，活动策划周密'),
        (2, 2, 12, 4, '活动执行良好，但沟通有待加强'),
        (3, 3, 13, 3, '活动申请材料不够完善'),
        (4, 6, 15, 5, 'AI创新大赛组织得很好'),
        (5, 7, 16, 4, '网络安全讲座讲师讲解清晰'),
        (6, 8, 17, 5, '物联网实训安排合理'),
        (7, 9, 18, 4, '管理论坛组织有序'),
        (8, 10, 19, 5, '英语演讲比赛流程顺畅'),
        (9, 1, 20, 4, '创新创业大赛指导到位'),
        (10, 2, 12, 5, '配音大赛气氛活跃'),
    ]
    cursor.executemany('''
        INSERT INTO organizer_evaluations (activity_id, organizer_id, evaluator_id, rating, comment) 
        VALUES (?, ?, ?, ?, ?)
    ''', organizer_evaluations_data)

    # 丰富奖励信息
    rewards_data = [
        ('Q1', 2024, 10000.0, '优秀组织奖', 'certificate', 10),
        ('Q1', 2024, 5000.0, '活动参与奖', 'money', 50),
        ('Q2', 2024, 15000.0, '创新活动奖', 'material', 20),
        ('Q2', 2024, 8000.0, 'AI创新奖', 'certificate', 5),
        ('Q2', 2024, 3000.0, '网络安全奖', 'money', 10),
        ('Q3', 2024, 12000.0, '管理之星', 'certificate', 8),
        ('Q3', 2024, 7000.0, '英语达人', 'certificate', 6),
        ('Q3', 2024, 9000.0, '创业先锋', 'money', 12),
        ('Q4', 2024, 11000.0, '年度创新奖', 'material', 15),
        ('Q4', 2024, 6000.0, '年度参与奖', 'money', 20),
    ]
    cursor.executemany('''
        INSERT INTO rewards (quarter, year, total_budget, reward_name, reward_type, quantity) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', rewards_data)

    # 丰富奖励分配信息
    reward_distributions_data = [
        (1, 1, 11, 'distributed', datetime.now() - timedelta(days=10)),
        (2, 2, 12, 'distributed', datetime.now() - timedelta(days=9)),
        (3, 3, 13, 'pending', None),
        (4, 4, 15, 'distributed', datetime.now() - timedelta(days=8)),
        (5, 5, 16, 'pending', None),
        (6, 6, 17, 'distributed', datetime.now() - timedelta(days=7)),
        (7, 7, 18, 'pending', None),
        (8, 8, 19, 'distributed', datetime.now() - timedelta(days=6)),
        (9, 9, 20, 'pending', None),
        (10, 10, 12, 'distributed', datetime.now() - timedelta(days=5)),
    ]
    cursor.executemany('''
        INSERT INTO reward_distributions (reward_id, student_id, supervisor_id, distribution_status, distributed_at) 
        VALUES (?, ?, ?, ?, ?)
    ''', reward_distributions_data)
    
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
    
    # 插入活动参与信息
    participants_data = [
        (1, 1, 'approved', datetime.now() - timedelta(days=1), datetime.now()),
        (1, 2, 'approved', datetime.now() - timedelta(days=1), datetime.now()),
        (2, 4, 'approved', datetime.now() - timedelta(days=2), datetime.now()),
        (2, 5, 'applied', datetime.now() - timedelta(hours=5), None),
        (3, 5, 'applied', datetime.now() - timedelta(hours=2), None),
        (10, 10, 'approved', datetime.now() - timedelta(days=1), datetime.now()),
        (10, 11, 'approved', datetime.now() - timedelta(days=1), datetime.now()),
        (11, 12, 'applied', datetime.now() - timedelta(hours=5), None),
        (11, 1, 'approved', datetime.now() - timedelta(days=2), datetime.now()),
        (12, 2, 'applied', datetime.now() - timedelta(hours=2), None),
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
        ('Q2', 2024, 8000.0, 'AI创新奖', 'certificate', 5),
        ('Q2', 2024, 3000.0, '网络安全奖', 'money', 10),
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
        (10, 10, 5, 'AI大赛很有挑战性'),
        (10, 11, 4, '收获很多'),
        (11, 12, 5, '讲座内容丰富'),
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
        (4, 10, 13, 'distributed', datetime.now() - timedelta(days=2)),
        (5, 11, 14, 'pending', None),
    ]
    
    cursor.executemany('''
        INSERT INTO reward_distributions (reward_id, student_id, supervisor_id, distribution_status, distributed_at) 
        VALUES (?, ?, ?, ?, ?)
    ''', reward_distributions_data)
    
    
    # 插入组织者评价信息
    organizer_evaluations_data = [
        (1, 1, 6, 5, '组织能力强，活动策划周密'),
        (2, 2, 7, 4, '活动执行良好，但沟通有待加强'),
        (3, 3, 8, 3, '活动申请材料不够完善'),
        (10, 10, 13, 5, '组织得很好'),
        (11, 11, 14, 4, '讲师讲解清晰'),
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
    
    # 新增几条已完成的活动
    completed_activities_data = [
        (3, 2, 12, '数学建模大赛', '全国大学生数学建模竞赛', datetime.now() - timedelta(days=20), datetime.now() - timedelta(days=15), '数学,建模', 20, 30, 'completed', 4000.0, 4000.0, 0.0, 'indoor', 0),
        (2, 4, 13, '舞蹈大赛', '校园舞蹈大赛', datetime.now() - timedelta(days=18), datetime.now() - timedelta(days=14), '舞蹈', 15, 25, 'completed', 3500.0, 3500.0, 0.0, 'indoor', 0),
        (4, 6, 15, 'AI挑战赛', '人工智能挑战赛', datetime.now() - timedelta(days=16), datetime.now() - timedelta(days=12), 'AI,编程', 18, 40, 'completed', 6000.0, 6000.0, 0.0, 'indoor', 0),
    ]
    cursor.executemany('''
        INSERT INTO activities (organizer_id, supervisor_id, admin_id, activity_name, description, start_time, end_time, required_skills, participant_count, max_participants, status, applied_funds, allocated_funds, remaining_funds, activity_type, total_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', completed_activities_data)

    # 新增对应的组织者评价（假设组织者id分别为2,4,6，评价人为教师12,13,15）
    organizer_evaluations_data = [
        (15, 2, 12, 5, '组织能力突出，活动效果很好'),
        (16, 4, 13, 4, '舞蹈大赛组织有序，参与度高'),
        (17, 6, 15, 5, 'AI挑战赛创新性强，组织得力'),
    ]
    cursor.executemany('''
        INSERT INTO organizer_evaluations (activity_id, organizer_id, evaluator_id, rating, comment)
        VALUES (?, ?, ?, ?, ?)
    ''', organizer_evaluations_data)

    # 同步增加被评分组织者（学生）的score积分
    cursor.execute('UPDATE students SET score = score + 10 WHERE student_id = 2')
    cursor.execute('UPDATE students SET score = score + 10 WHERE student_id = 4')
    cursor.execute('UPDATE students SET score = score + 10 WHERE student_id = 6')
    


if __name__ == "__main__":
    # 初始化数据库
    init_database()
