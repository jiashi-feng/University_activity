import sqlite3

def verify_participants():
    conn = sqlite3.connect('University_activit.db')
    cursor = conn.cursor()
    
    # 查询编程竞赛的所有参与者
    cursor.execute('''
        SELECT u.name, ap.status, ap.applied_at 
        FROM activity_participants ap 
        JOIN activities a ON ap.activity_id = a.activity_id 
        JOIN users u ON ap.student_id = u.user_id 
        WHERE a.activity_name = '编程竞赛'
        ORDER BY ap.applied_at DESC
    ''')
    
    results = cursor.fetchall()
    
    print('编程竞赛的所有参与者:')
    print('=' * 50)
    
    for i, row in enumerate(results, 1):
        print(f'{i}. 学生: {row[0]}')
        print(f'   状态: {row[1]}')
        print(f'   申请时间: {row[2]}')
        print('-' * 30)
    
    conn.close()

if __name__ == '__main__':
    verify_participants() 