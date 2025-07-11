import sqlite3
from datetime import datetime, timedelta

def add_unrated_finished_activity():
    conn = sqlite3.connect('University_activit.db')
    cursor = conn.cursor()
    student_id = 1  # 张三
    now = datetime.now()
    # 新增1个未评价的已完成活动
    name = '数据分析实训'
    desc = '数据分析技能提升实训'
    start = now - timedelta(days=10)
    end = now - timedelta(days=7)
    skills = '编程'
    org = 1
    sup = 6
    adm = 9
    typ = 'indoor'
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
    print('已为张三添加1个已完成但未评价的活动及相关进度数据')

if __name__ == '__main__':
    add_unrated_finished_activity() 