# 高校活动管理系统

一个基于 Flask 的高校活动管理系统，用于管理和组织校园活动。系统支持学生、教师和管理员三种角色，实现了活动的发布、审核、报名、管理等完整功能。

## 功能特性

### 用户角色

1. **学生**
   - 浏览和报名参加校园活动
   - 创建和组织新活动
   - 查看个人活动记录
   - 管理个人特长信息

2. **教师**
   - 审核和指导学生活动
   - 管理活动资金
   - 查看活动进展
   - 评估活动成效

3. **管理员**
   - 系统级活动审核
   - 场地资源管理
   - 活动数据统计
   - 用户管理

### 核心功能

- 活动全生命周期管理
- 实时活动状态更新
- 场地预约和管理
- 活动资金管理
- 用户权限控制
- 数据统计和分析

## 技术栈

### 后端
- Python 3.x
- Flask Web 框架
- SQLite 数据库
- Flask-Session 会话管理

### 前端
- HTML5 + CSS3
- Bootstrap 5.3.0
- JavaScript
- Bootstrap Icons

## 安装说明

1. **克隆项目**
   ```bash
   git clone [项目地址]
   cd university-activity-management
   ```

2. **安装依赖**
   ```bash
   pip install Flask
   ```

3. **初始化数据库**
   ```bash
   python init_db.py
   ```

4. **启动应用**
   ```bash
   python app.py
   ```

5. **访问系统**
   打开浏览器访问 `http://localhost:5000`

## 演示账户

### 学生账户
- 用户名：张三
- 密码：password123
- 角色：学生

### 教师账户
- 用户名：陈老师
- 密码：teacher123
- 角色：教师

### 管理员账户
- 用户名：李晓峰
- 密码：admin123
- 角色：管理员

## 项目结构

```
university-activity-management/
├── app.py                 # 主应用程序
├── init_db.py            # 数据库初始化脚本
├── requirements.txt      # 项目依赖
├── static/              # 静态资源
│   ├── css/
│   ├── js/
│   └── img/
├── templates/           # HTML模板
│   ├── admin/          # 管理员页面
│   ├── student/        # 学生页面
│   ├── teacher/        # 教师页面
│   ├── base.html       # 基础模板
│   └── login.html      # 登录页面
└── README.md           # 项目文档
```

## 数据库设计

### 主要表结构

1. **users** - 用户基础信息
   - user_id (主键)
   - user_type (用户类型)
   - name (姓名)
   - college (学院)
   - password (密码)
   - phone (联系电话)

2. **students** - 学生信息
   - student_id (主键，关联users)
   - student_number (学号)
   - grade (年级)
   - major (专业)
   - class_name (班级)
   - score (积分)

3. **teachers** - 教师信息
   - teacher_id (主键，关联users)
   - employee_number (工号)
   - position (职位)
   - is_admin (管理员标识)

4. **activities** - 活动信息
   - activity_id (主键)
   - title (活动名称)
   - description (活动描述)
   - organizer_id (组织者ID)
   - supervisor_id (指导教师ID)
   - status (活动状态)
   - start_time (开始时间)
   - end_time (结束时间)

## 开发规范

1. **代码风格**
   - 遵循 PEP 8 Python代码规范
   - 使用4空格缩进
   - 类名使用驼峰命名
   - 函数和变量使用下划线命名

2. **注释规范**
   - 每个函数都应有文档字符串
   - 复杂逻辑需要添加行内注释
   - 重要的业务逻辑需要详细说明

3. **Git提交规范**
   - feat: 新功能
   - fix: 修复bug
   - docs: 文档更新
   - style: 代码格式调整
   - refactor: 代码重构

## 安全特性

- 密码加密存储
- 会话管理
- 权限控制
- SQL注入防护
- XSS防护
- CSRF防护

## 部署说明

1. **环境要求**
   - Python 3.x
   - SQLite 3
   - 现代浏览器（支持ES6）

2. **生产环境配置**
   - 使用生产级别的Web服务器（如Gunicorn）
   - 启用HTTPS
   - 配置错误日志
   - 设置安全的密钥

## 维护和支持

- 定期备份数据库
- 监控系统性能
- 及时更新依赖包
- 处理用户反馈

## 许可证

MIT License

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 联系方式

- 项目维护者：[jiashi-feng]
- 项目地址：[https://github.com/jiashi-feng/university-activity]
- 问题反馈：请使用 GitHub Issues 