import sqlite3
from datetime import datetime, timedelta

def add_participants():
    conn = sqlite3.connect('University_activit.db')
    cursor = conn.cursor()
    
    try:
        # 获取编程竞赛的活动ID
        cursor.execute("SELECT activity_id FROM activities WHERE activity_name = '编程竞赛'")
        activity = cursor.fetchone()
        
        if not activity:
            print("未找到编程竞赛活动")
            return
        
        activity_id = activity[0]
        
        # 获取学生ID（李四、王五、赵六）
        cursor.execute("SELECT user_id FROM users WHERE name IN ('李四', '王五', '赵六') AND user_type = 'student'")
        students = cursor.fetchall()
        
        if len(students) < 3:
            print("未找到足够的学生")
            return
        
        # 准备插入数据
        current_time = datetime.now()
        participants_data = [
            (activity_id, students[0][0], 'applied', current_time - timedelta(hours=2)),  # 李四
            (activity_id, students[1][0], 'applied', current_time - timedelta(hours=1)),  # 王五
            (activity_id, students[2][0], 'applied', current_time - timedelta(minutes=30))  # 赵六
        ]
        
        # 插入参与记录
        cursor.executemany('''
            INSERT INTO activity_participants (activity_id, student_id, status, applied_at)
            VALUES (?, ?, ?, ?)
        ''', participants_data)
        
        conn.commit()
        print("成功添加三条申请记录:")
        print("1. 李四 - 申请参加编程竞赛")
        print("2. 王五 - 申请参加编程竞赛") 
        print("3. 赵六 - 申请参加编程竞赛")
        
    except Exception as e:
        conn.rollback()
        print(f"添加失败: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_participants() 