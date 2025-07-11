import sqlite3
from datetime import datetime, timedelta

def add_activities():
    """添加与张三特长相关的活动"""
    conn = sqlite3.connect('University_activit.db')
    cursor = conn.cursor()
    
    # 新活动数据
    activities_data = [
        # 编程相关活动
        (1, 6, 9, '软件开发大赛', '面向全校学生的软件开发比赛，需要良好的编程和设计能力', 
         datetime.now() + timedelta(days=30), datetime.now() + timedelta(days=35),
         '编程,设计', 0, 40, 'approved', 6000.0, 5000.0, 5000.0, 'indoor', 0),
         
        (1, 6, 9, '网页设计竞赛', '校园网页设计大赛，考验参与者的编程和设计水平', 
         datetime.now() + timedelta(days=20), datetime.now() + timedelta(days=21),
         '编程,设计', 0, 30, 'approved', 3000.0, 2500.0, 2500.0, 'indoor', 0),
         
        (1, 6, 9, 'UI设计工作坊', '为期两天的UI设计实践活动，需要具备基本设计能力', 
         datetime.now() + timedelta(days=15), datetime.now() + timedelta(days=16),
         '设计', 0, 25, 'approved', 2000.0, 1500.0, 1500.0, 'indoor', 0),
         
        (1, 6, 9, '人工智能编程实践', '人工智能算法实现与应用，需要较强的编程能力', 
         datetime.now() + timedelta(days=25), datetime.now() + timedelta(days=27),
         '编程', 0, 35, 'approved', 4000.0, 3500.0, 3500.0, 'indoor', 0),
         
        (1, 6, 9, '创新设计展', '校园创新设计作品展示与交流活动', 
         datetime.now() + timedelta(days=40), datetime.now() + timedelta(days=41),
         '设计', 0, 50, 'approved', 3500.0, 3000.0, 3000.0, 'indoor', 0)
    ]
    
    try:
        # 插入活动信息
        cursor.executemany('''
            INSERT INTO activities (
                organizer_id, supervisor_id, admin_id, activity_name, description, 
                start_time, end_time, required_skills, participant_count, max_participants, 
                status, applied_funds, allocated_funds, remaining_funds, activity_type, total_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', activities_data)
        
        conn.commit()
        print('成功添加新活动！')
        
    except Exception as e:
        conn.rollback()
        print(f'添加活动失败：{str(e)}')
    finally:
        conn.close()

if __name__ == '__main__':
    add_activities() 