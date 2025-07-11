#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查看工具
用于查看University_activit.db数据库中的所有表和数据
"""

import sqlite3
import os
from datetime import datetime

def view_database():
    """查看数据库内容"""
    db_path = 'University_activit.db'
    
    if not os.path.exists(db_path):
        print(f"错误：数据库文件 {db_path} 不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("=" * 60)
        print("数据库内容查看")
        print("=" * 60)
        print(f"数据库文件: {db_path}")
        print(f"表数量: {len(tables)}")
        print()
        
        for table in tables:
            table_name = table[0]
            print(f"表名: {table_name}")
            print("-" * 40)
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("表结构:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            print()
            
            # 获取数据
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            print(f"数据行数: {len(rows)}")
            
            if rows:
                # 显示前10行数据
                print("前10行数据:")
                for i, row in enumerate(rows[:10]):
                    print(f"  行 {i+1}: {row}")
                
                if len(rows) > 10:
                    print(f"  ... 还有 {len(rows) - 10} 行数据")
            else:
                print("  无数据")
            
            print("\n" + "=" * 60 + "\n")
        
        conn.close()
        
    except Exception as e:
        print(f"查看数据库时出错: {e}")

def view_specific_table(table_name):
    """查看特定表的内容"""
    db_path = 'University_activit.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            print(f"表 '{table_name}' 不存在")
            return
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"表 '{table_name}' 的详细信息:")
        print("-" * 50)
        print("列信息:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        print()
        
        # 获取所有数据
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        print(f"总行数: {len(rows)}")
        print("所有数据:")
        for i, row in enumerate(rows):
            print(f"  行 {i+1}: {row}")
        
        conn.close()
        
    except Exception as e:
        print(f"查看表 '{table_name}' 时出错: {e}")

if __name__ == "__main__":
    print("选择查看模式:")
    print("1. 查看所有表")
    print("2. 查看特定表")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        view_database()
    elif choice == "2":
        table_name = input("请输入表名: ").strip()
        view_specific_table(table_name)
    else:
        print("无效选择，默认查看所有表")
        view_database() 