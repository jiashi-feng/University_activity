import sqlite3
from datetime import datetime, timedelta

def add_more_unrated_finished_activities():
    conn = sqlite3.connect('University_activit.db')
    cursor = conn.cursor()
    student_id = 1  # 张三
    now = datetime.now()
    activities = [
        ('机器学习实战', '机器学习算法实践与应用', now - timedelta(days=40), now - timedelta(days=36), '编程', 1, 6, 9, 'indoor'),
        ('产品设计大赛', '创新产品设计比赛', now - timedelta(days=32), now - timedelta(days=28), '设计', 1, 6, 9, 'indoor'),
        ('数据可视化训练', '数据可视化技能提升', now - timedelta(days=25), now - timedelta(days=22), '编程,设计', 1, 6, 9, 'indoor'),
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
    conn.commit()
    conn.close()
    print('已为张三添加3个已完成但未评价的活动及相关进度数据')

if __name__ == '__main__':
    add_more_unrated_finished_activities() 