import sqlite3
from datetime import datetime, timedelta

def add_finished_activities():
    conn = sqlite3.connect('University_activit.db')
    cursor = conn.cursor()
    # 张三的user_id和student_id为1
    student_id = 1
    now = datetime.now()
    # 新增3个活动
    activities = [
        ('算法训练营', '算法专项训练，提升编程能力', now - timedelta(days=30), now - timedelta(days=25), '编程', 1, 6, 9, 'indoor'),
        ('创新创业讲座', '创新创业知识分享，提升综合素质', now - timedelta(days=20), now - timedelta(days=19), '设计', 1, 6, 9, 'indoor'),
        ('团队协作比赛', '团队合作能力比拼', now - timedelta(days=15), now - timedelta(days=13), '编程,设计', 1, 6, 9, 'indoor'),
    ]
    for name, desc, start, end, skills, org, sup, adm, typ in activities:
        cursor.execute('''
            INSERT INTO activities (organizer_id, supervisor_id, admin_id, activity_name, description, start_time, end_time, required_skills, participant_count, max_participants, status, applied_funds, allocated_funds, remaining_funds, activity_type, total_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', 1000, 800, 800, ?, 0)
        ''', (org, sup, adm, name, desc, start, end, skills, 1, 20, typ))
        activity_id = cursor.lastrowid
        # 张三报名并完成
        cursor.execute('''
            INSERT INTO activity_participants (activity_id, student_id, status, applied_at, approved_at, completed_at)
            VALUES (?, ?, 'completed', ?, ?, ?)
        ''', (activity_id, student_id, start - timedelta(days=1), start, end))
        # 4个进度节点
        for i in range(1, 5):
            cursor.execute('''
                INSERT INTO activity_progress (activity_id, participant_id, progress_content, completion_percentage, submitted_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (activity_id, student_id, f'节点{i}说明内容', i*25, start + timedelta(days=i)))
        # 随机插入一条评价
        cursor.execute('''
            INSERT INTO activity_evaluations (activity_id, participant_id, rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (activity_id, student_id, 5, f'{name} 很有收获！', end + timedelta(days=1)))
    conn.commit()
    conn.close()
    print('已为张三添加3个已完成活动及相关数据')

if __name__ == '__main__':
    add_finished_activities() 