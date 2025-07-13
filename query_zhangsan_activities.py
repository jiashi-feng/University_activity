import sqlite3

def query_zhangsan_activities():
    conn = sqlite3.connect('University_activit.db')
    cursor = conn.cursor()
    
    # 查询张三参加的活动
    cursor.execute('''
        SELECT a.activity_name, ap.status, ap.applied_at, a.start_time, a.end_time 
        FROM activity_participants ap 
        JOIN activities a ON ap.activity_id = a.activity_id 
        JOIN users u ON ap.student_id = u.user_id 
        WHERE u.name = '张三'
    ''')
    
    results = cursor.fetchall()
    
    print('张三参加的活动:')
    print('=' * 50)
    
    if results:
        for row in results:
            print(f'活动名称: {row[0]}')
            print(f'参与状态: {row[1]}')
            print(f'申请时间: {row[2]}')
            print(f'活动时间: {row[3]} 至 {row[4]}')
            print('-' * 30)
    else:
        print('张三没有参加任何活动')
    
    conn.close()

if __name__ == '__main__':
    query_zhangsan_activities() 