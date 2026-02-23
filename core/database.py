import sqlite3
import os
from pathlib import Path
from core.logger import logger
from core.utils import get_app_path
from core.migrations import MigrationManager

class DatabaseManager:
    def __init__(self, db_name):
        # 使用专用数据库文件
        self.db_name = db_name
        self.db_path = db_name
        logger.info(f"Using dedicated database file: {self.db_name}")
        self.conn = None
        self.cursor = None
        self._ensure_db_file()
        try:
            self.conn = self._connect_to_db()
            if self.conn:
                self.cursor = self.conn.cursor()
                self._create_tables()
                # 确保启用外键约束
                self.conn.execute("PRAGMA foreign_keys = ON")
                self.conn.execute("PRAGMA journal_mode = WAL")  # 使用WAL日志模式提高性能
                
                # Run migrations
                self.migration_manager = MigrationManager(self)
                self.migration_manager.run_migrations()
                
                self.conn.commit()
            else:
                raise Exception(f"无法连接到数据库: {self.db_name}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            if self.conn:
                self.conn.close()
            raise
            
    def create_new_connection(self):
        """Create a new connection for thread safety"""
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def fetch_all_safe(self, query, params=()):
        """Execute a query safely in a separate connection (for threads)"""
        conn = None
        try:
            conn = self.create_new_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Exception as e:
            logger.error(f"Safe fetch failed: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_safe(self, query, params=()):
        """Execute a write query safely in a separate connection (for threads)"""
        conn = None
        try:
            conn = self.create_new_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
        except Exception as e:
            logger.error(f"Safe execute failed: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _ensure_db_file(self):
        """确保数据库文件存在"""
        if not os.path.exists(self.db_name):
            # 创建数据库文件目录(如果不存在)
            os.makedirs(os.path.dirname(self.db_name), exist_ok=True)

    def _check_connection(self):
        """检查数据库连接是否有效"""
        try:
            # 检查连接和游标是否存在
            if not self.conn or not self.cursor:
                raise Exception("连接或游标未初始化")
                
            # 执行简单查询测试连接
            self.cursor.execute("SELECT 1")
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            try:
                # 尝试重新连接
                if self.conn:
                    self.conn.close()
                self.conn = self._connect_to_db()
                self.cursor = self.conn.cursor()
                self.conn.execute("PRAGMA foreign_keys = ON")
                return True
            except Exception as reconnect_error:
                logger.error(f"Database reconnection failed: {reconnect_error}")
                return False
        
    def _check_and_upgrade_tables(self):
        """已废弃：逻辑已移动到 core/migrations.py"""
        pass

    def _create_business_types_table(self):
        """创建业务类型配置表"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS business_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 初始化默认数据
            cursor.execute("SELECT count(*) FROM business_types")
            if cursor.fetchone()[0] == 0:
                defaults = ['销售业务', '采购业务', '代理记账', '工商代办', '其他业务']
                for name in defaults:
                    try:
                        cursor.execute("INSERT INTO business_types (name, is_default) VALUES (?, 1)", (name,))
                    except sqlite3.IntegrityError:
                        pass
        except Exception as e:
            logger.error(f"Failed to create business_types table: {e}")
            raise

    def _create_tables(self):
        """创建必要的数据库表"""
        try:
            cursor = self.conn.cursor()
            
            # 创建customers表(如果不存在)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT UNIQUE NOT NULL,
                    contact_person TEXT NOT NULL,
                    phone TEXT,
                    status TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TEXT
                )
            """)
            
            # 创建income表(如果不存在)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS income (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    category TEXT
                )
            """)
            
            # 启用外键约束
            cursor.execute("PRAGMA foreign_keys=ON")
            
            # 创建transactions表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
            """)
            
            # 创建expenses表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    date TEXT DEFAULT CURRENT_TIMESTAMP,
                    category TEXT,
                    description TEXT
                )
            """)

            # 创建business表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS business (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    business_name TEXT,
                    secondary_business TEXT,
                    business_type TEXT,
                    company_password TEXT,
                    public_info TEXT,
                    remarks TEXT,
                    proxy_accounting_date TEXT,
                    business_date TEXT,
                    create_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    proxy_accounting INTEGER DEFAULT 0,
                    business_agent INTEGER DEFAULT 0,
                    other_business TEXT,
                    deal_business TEXT,
                    proxy_start_date TEXT,
                    proxy_end_date TEXT,
                    status TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TEXT
                )
            """)
            
            # 创建业务类型配置表
            self._create_business_types_table()

            # 创建finance表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS finance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    amount REAL,
                    cost REAL,
                    profit REAL,
                    due_date TEXT,
                    notes TEXT,
                    business_id INTEGER,
                    transaction_date TEXT,
                    description TEXT,
                    category TEXT,
                    pending_amount REAL DEFAULT 0,
                    pending_date TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TEXT,
                    FOREIGN KEY(business_id) REFERENCES business(id)
                )
            """)

            # 创建departments表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建work_arrangements表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_arrangements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    work_date TEXT NOT NULL,
                    work_time TEXT NOT NULL,
                    department_id INTEGER,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE SET NULL
                )
            """)

            # 创建work_logs表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建contract_types表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contract_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建contract_categories表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contract_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建contracts表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contracts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_number TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    business_id INTEGER,
                    contract_type TEXT NOT NULL, -- incoming/outgoing
                    category_id INTEGER,
                    category_ids TEXT, -- Store comma-separated category IDs for multi-select
                    party_a TEXT,
                    party_b TEXT,
                    signing_date TEXT,
                    effective_date TEXT,
                    expiration_date TEXT,
                    amount REAL DEFAULT 0,
                    status TEXT DEFAULT 'draft',
                    remarks TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TEXT,
                    FOREIGN KEY(business_id) REFERENCES business(id) ON DELETE CASCADE,
                    FOREIGN KEY(category_id) REFERENCES contract_categories(id) ON DELETE SET NULL
                )
            """)

            # 创建contract_attachments表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contract_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    FOREIGN KEY(contract_id) REFERENCES contracts(id) ON DELETE CASCADE
                )
            """)

            # 创建payment_schedules表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL,
                    installment_number INTEGER,
                    due_date TEXT,
                    amount REAL,
                    status TEXT DEFAULT 'pending',
                    remarks TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(contract_id) REFERENCES contracts(id) ON DELETE CASCADE
                )
            """)
            
            # 不再自动添加测试数据
                
        except sqlite3.Error as e:
            logger.error(f"Table creation failed: {e}")
        
    def _connect_to_db(self):
        """建立数据库连接"""
        try:
            conn = sqlite3.connect(self.db_name)
            conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
            conn.execute("PRAGMA synchronous = FULL")  # 确保数据安全写入
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            return None
            
    def encrypt_data(self, data):
        """数据加密方法"""
        # 这里实现实际的加密逻辑
        return data
        
    def decrypt_data(self, data):
        """数据解密方法"""
        # 这里实现实际的解密逻辑
        return data
        
    def close(self):
        """关闭数据库连接并确保数据持久化"""
        if self.conn:
            try:
                # 执行完整性检查
                self.conn.execute("PRAGMA integrity_check")
                # 确保所有更改写入磁盘
                self.conn.execute("PRAGMA wal_checkpoint(FULL)")
                # 关闭连接
                self.conn.close()
                logger.info("Database connection safely closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
                if self.conn:
                    self.conn.close()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_dashboard_stats(self, start_date=None, end_date=None):
        """获取仪表盘统计数据
        参数:
            start_date: 开始日期字符串(格式:YYYY-MM-DD)，不提供则使用当月1号
            end_date: 结束日期字符串(格式:YYYY-MM-DD)，不提供则使用当天
        返回:
            包含统计数据的字典
        """
        from datetime import datetime
        
        # 设置默认日期范围(当月1号到当天)
        if not start_date or not end_date:
            today = datetime.now().strftime('%Y-%m-%d')
            first_day_of_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            start_date = start_date or first_day_of_month
            end_date = end_date or today
        
        # 调试输出日期范围
        logger.debug(f"Stats date range: {start_date} to {end_date}")
        
        # 获取统计数据
        stats = {
            'total_customers': self.get_customer_count(start_date, end_date),
            'total_transactions': self.get_transaction_count(start_date, end_date),
            'monthly_income': self.get_monthly_income_total(start_date, end_date),
            'monthly_profit': self.get_monthly_profit(start_date, end_date)
        }
        
        # 调试输出统计结果
        logger.debug(f"Stats data: {stats}")
        
        return stats

    def get_todos(self):
        """获取待办事项列表"""
        import json
        
        todo_file = get_app_path('todo_list.json')
        if not os.path.exists(todo_file):
            return []
            
        try:
            with open(todo_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read todos: {e}")
            return []

    def add_todo(self, text):
        """添加待办事项"""
        todos = self.get_todos()
        new_id = max([t['id'] for t in todos], default=0) + 1
        todos.append({
            'id': new_id,
            'text': text,
            'completed': False
        })
        self._save_todos(todos)

    def update_todo_status(self, todo_id, completed):
        """更新待办事项状态"""
        todos = self.get_todos()
        for todo in todos:
            if todo['id'] == todo_id:
                todo['completed'] = completed
                break
        self._save_todos(todos)

    def delete_todo(self, todo_id):
        """删除指定ID的待办事项"""
        todos = self.get_todos()
        # 保留不匹配ID的待办事项
        updated_todos = [todo for todo in todos if todo['id'] != todo_id]
        if len(updated_todos) != len(todos):
            self._save_todos(updated_todos)
            return True
        return False

    def _save_todos(self, todos):
        """保存待办事项到文件"""
        import json
        
        todo_file = get_app_path('todo_list.json')
        try:
            with open(todo_file, 'w', encoding='utf-8') as f:
                json.dump(todos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save todos: {e}")

    def get_notes(self):
        """获取便签内容"""
        import json
        
        notes_file = get_app_path('notes.json')
        if not os.path.exists(notes_file):
            return ""
            
        try:
            with open(notes_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read notes: {e}")
            return ""

    def save_notes(self, notes):
        """保存便签内容"""
        
        notes_file = get_app_path('notes.json')
        try:
            with open(notes_file, 'w', encoding='utf-8') as f:
                f.write(notes)
        except Exception as e:
            logger.error(f"Failed to save notes: {e}")
        
    def execute_query(self, query, params=None, fetch=True):
        """执行SQL查询的通用方法
        参数:
            query: SQL查询字符串
            params: 查询参数(可选)
            fetch: 是否获取结果(默认为True)
        返回:
            查询结果(如果fetch=True)或None
        """
        try:
            if not self._check_connection():
                raise Exception("数据库连接不可用")
                
            with self.conn:
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                    
                if fetch:
                    return cursor.fetchall()
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}\nParams: {params}")
            raise
            
    def soft_delete_record(self, table, record_id):
        """软删除记录"""
        try:
            from datetime import datetime
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            query = f"UPDATE {table} SET is_deleted = 1, deleted_at = ? WHERE id = ?"
            self.execute_query(query, (now, record_id), fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Soft delete failed ({table}, {record_id}): {e}")
            return False

    def restore_record(self, table, record_id):
        """恢复已删除的记录"""
        try:
            query = f"UPDATE {table} SET is_deleted = 0, deleted_at = NULL WHERE id = ?"
            self.execute_query(query, (record_id,), fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Restore record failed ({table}, {record_id}): {e}")
            return False

    def get_deleted_records(self, table):
        """获取已删除的记录"""
        try:
            query = f"SELECT * FROM {table} WHERE is_deleted = 1 ORDER BY deleted_at DESC"
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to get deleted records ({table}): {e}")
            return []

    def permanent_delete_record(self, table, record_id):
        """永久删除记录"""
        try:
            query = f"DELETE FROM {table} WHERE id = ?"
            self.execute_query(query, (record_id,), fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Permanent delete failed ({table}, {record_id}): {e}")
            return False

    def get_monthly_income(self, year, start_date=None, end_date=None):
        """获取月度收入数据
        参数:
            year: 年份(整数)
            start_date: 开始日期字符串(格式:YYYY-MM-DD)
            end_date: 结束日期字符串(格式:YYYY-MM-DD)
        返回:
            有序字典: {月份: 金额} 月份格式为'01'-'12'，按月份顺序排列
        """
        try:
            query = """
                SELECT strftime('%m', due_date) as month, 
                       SUM(amount) as total
                FROM finance
                WHERE is_deleted = 0 
                AND strftime('%Y', due_date) = ?
                GROUP BY strftime('%m', due_date)
            """
            params = [str(year)]
            
            if start_date:
                query += " AND due_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND due_date <= ?"
                params.append(end_date)
                
            results = self.execute_query(query, params)
            
            # 初始化所有月份为0
            monthly_data = {f"{i:02d}": 0.0 for i in range(1, 13)}
            
            # 填充查询结果
            if results:
                for row in results:
                    monthly_data[row[0]] = row[1]
                    
            return monthly_data
            
        except Exception as e:
            logger.error(f"Failed to get monthly income: {e}")
            return {}

    def get_contracts(self, business_id=None, contract_type=None, status=None, search_text=None):
        """获取合同列表"""
        try:
            query = "SELECT * FROM contracts WHERE is_deleted = 0"
            params = []
            
            if business_id:
                query += " AND business_id = ?"
                params.append(business_id)
            
            if contract_type and contract_type != 'all':
                query += " AND contract_type = ?"
                params.append(contract_type)
                
            if status and status != 'all':
                query += " AND status = ?"
                params.append(status)

            if search_text:
                query += " AND (contract_number LIKE ? OR title LIKE ? OR party_a LIKE ? OR party_b LIKE ?)"
                like_text = f"%{search_text}%"
                params.extend([like_text, like_text, like_text, like_text])
                
            query += " ORDER BY created_at DESC"
            
            return self.execute_query(query, params)
        except Exception as e:
            logger.error(f"Failed to get contracts: {e}")
            return []

    def get_contract_categories(self):
        """获取合同分类"""
        try:
            query = "SELECT * FROM contract_categories ORDER BY name"
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to get contract categories: {e}")
            return []
            
    def add_contract(self, data):
        """添加合同"""
        try:
            keys = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO contracts ({keys}) VALUES ({placeholders})"
            self.execute_query(query, tuple(data.values()), fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add contract: {e}")
            return False

    def get_contract_attachments(self, contract_id):
        """获取合同附件"""
        try:
            query = "SELECT * FROM contract_attachments WHERE contract_id = ?"
            return self.execute_query(query, (contract_id,))
        except Exception as e:
            logger.error(f"Failed to get contract attachments: {e}")
            return []

    def add_contract_attachment(self, data):
        """添加合同附件"""
        try:
            keys = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO contract_attachments ({keys}) VALUES ({placeholders})"
            self.execute_query(query, tuple(data.values()), fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add contract attachment: {e}")
            return False

    def delete_contract_attachment(self, attachment_id):
        """删除合同附件"""
        try:
            query = "DELETE FROM contract_attachments WHERE id = ?"
            self.execute_query(query, (attachment_id,), fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete contract attachment: {e}")
            return False

    def get_payment_schedules(self, contract_id):
        """获取合同付款计划"""
        try:
            query = "SELECT * FROM payment_schedules WHERE contract_id = ? ORDER BY installment_number"
            return self.execute_query(query, (contract_id,))
        except Exception as e:
            logger.error(f"Failed to get payment schedules: {e}")
            return []

    def add_payment_schedule(self, data):
        """添加付款计划"""
        try:
            keys = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO payment_schedules ({keys}) VALUES ({placeholders})"
            self.execute_query(query, tuple(data.values()), fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add payment schedule: {e}")
            return False

    def update_payment_schedule(self, schedule_id, data):
        """更新付款计划"""
        try:
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            query = f"UPDATE payment_schedules SET {set_clause} WHERE id = ?"
            params = list(data.values()) + [schedule_id]
            self.execute_query(query, params, fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update payment schedule: {e}")
            return False

    def delete_payment_schedule(self, schedule_id):
        """删除付款计划"""
        try:
            query = "DELETE FROM payment_schedules WHERE id = ?"
            self.execute_query(query, (schedule_id,), fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete payment schedule: {e}")
            return False
            
    def update_contract(self, contract_id, data):
        """更新合同"""
        try:
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            set_clause += ", updated_at = CURRENT_TIMESTAMP"
            query = f"UPDATE contracts SET {set_clause} WHERE id = ?"
            params = list(data.values()) + [contract_id]
            self.execute_query(query, params, fetch=False)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update contract: {e}")
            return False

    def get_monthly_expense_by_year(self, year):
        """获取指定年份的月度支出数据"""
        try:
            query = """
                SELECT strftime('%m', due_date) as month, 
                       SUM(cost) as total
                FROM finance
                WHERE strftime('%Y', due_date) = ? AND is_deleted = 0
                GROUP BY month
            """
            results = self.execute_query(query, [str(year)])
            
            from collections import OrderedDict
            monthly_data = OrderedDict()
            for month in range(1, 13):
                monthly_data[f"{month:02d}"] = 0.0
            
            for row in results:
                monthly_data[row[0]] = float(row[1]) if row[1] else 0.0
                
            return monthly_data
        except Exception as e:
            logger.error(f"Error getting monthly expense: {e}")
            return {}

    def get_customer_count(self, start_date=None, end_date=None):
        """获取客户数
        参数:
            start_date: 开始日期(可选)
            end_date: 结束日期(可选)
        返回:
            客户数(整数)
        """
        try:
            query = "SELECT COUNT(*) FROM customers WHERE is_deleted = 0"
            params = []
            
            # 添加日期筛选条件
            if start_date and end_date:
                query += " AND created_at BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                query += " AND created_at >= ?"
                params.append(start_date)
            elif end_date:
                query += " AND created_at <= ?"
                params.append(end_date)
                
            result = self.execute_query(query, params)
            count = result[0][0] if result else 0
            logger.debug(f"Customer count result: {count}")  # 调试输出
            return count
        except Exception as e:
            logger.error(f"Error getting customer count: {e}")
            return 0

    def get_transaction_count(self, start_date=None, end_date=None):
        """获取业务记录总数"""
        try:
            if not hasattr(self, 'cursor'):
                self.cursor = self.conn.cursor()
                
            query = "SELECT COUNT(*) FROM business WHERE is_deleted = 0"
            self.cursor.execute(query)
            result = self.cursor.fetchone()[0]
            logger.debug(f"Total business records: {result}")
            logger.debug(f"Executed SQL: {query}")
            return int(result) if result else 0
        except sqlite3.Error as e:
            logger.error(f"Error getting business stats: {e}")
            return 0

    def get_monthly_income_total(self, start_date, end_date):
        """获取指定日期范围内的收入总额"""
        try:
            if not hasattr(self, 'cursor'):
                self.cursor = self.conn.cursor()
                
            self.cursor.execute("""
                SELECT SUM(amount) 
                FROM finance 
                WHERE due_date BETWEEN ? AND ?
            """, (start_date, end_date))
            return self.cursor.fetchone()[0] or 0
        except sqlite3.Error as e:
            logger.error(f"Error getting total income: {e}")
            return 0

    def get_monthly_profit(self, start_date, end_date):
        """获取指定日期范围内的利润(收入-成本)"""
        try:
            if not hasattr(self, 'cursor'):
                self.cursor = self.conn.cursor()
                
            # 获取总收入
            self.cursor.execute("""
                SELECT SUM(amount) 
                FROM finance 
                WHERE due_date BETWEEN ? AND ?
            """, (start_date, end_date))
            income = self.cursor.fetchone()[0] or 0
            
            # 获取总成本
            self.cursor.execute("""
                SELECT SUM(cost) 
                FROM finance 
                WHERE due_date BETWEEN ? AND ?
            """, (start_date, end_date))
            cost = self.cursor.fetchone()[0] or 0
            
            return income - cost
        except sqlite3.Error as e:
            logger.error(f"Error calculating profit: {e}")
            return 0
            
    def get_monthly_profit_by_year(self, year):
        """获取年度月度利润数据(格式与get_monthly_income一致)
        参数:
            year: 年份(整数)
        返回:
            有序字典: {月份: 利润} 月份格式为'01'-'12'，按月份顺序排列
        """
        try:
            from collections import OrderedDict
            
            # 基础查询
            query = """
                SELECT strftime('%m', due_date) as month, 
                       SUM(amount - cost) as profit
                FROM finance
                WHERE strftime('%Y', due_date) = ? AND is_deleted = 0
                GROUP BY month
            """
            params = [str(year)]
            
            results = self.execute_query(query, params)
            
            # 创建有序的月份字典
            monthly_data = OrderedDict()
            
            # 初始化所有月份为0
            for month in range(1, 13):
                month_str = f"{month:02d}"
                monthly_data[month_str] = 0.0
            
            # 填充查询结果
            for row in results:
                month_str = row[0]
                monthly_data[month_str] = float(row[1]) if row[1] else 0.0
                    
            return monthly_data
            
        except sqlite3.Error as e:
            logger.error(f"Error getting monthly profit data: {e}")
            # 返回空字典表示无数据
            return OrderedDict()
            
    def get_all_business(self):
        """获取所有业务数据
        返回:
            业务数据列表，包含表格需要的9个字段
        """
        try:
            if not hasattr(self, 'cursor'):
                self.cursor = self.conn.cursor()
                
            self.cursor.execute("""
                SELECT 
                    company_name,
                    business_name,
                    secondary_business,
                    company_password,
                    public_info,
                    remarks,
                    business_date,
                    proxy_accounting_date,
                    create_time
                FROM business
                ORDER BY create_time DESC
            """)
            
            return self.cursor.fetchall()
            
        except sqlite3.Error as e:
            logger.error(f"Error getting business data: {e}")
            return []
            
    def get_proxy_accounting_expiring(self, days):
        """获取即将到期的代理记账业务
        参数:
            days: 提前提醒的天数
        返回:
            即将到期的业务列表
        """
        try:
            if not hasattr(self, 'cursor'):
                self.cursor = self.conn.cursor()
                
            query = """
                SELECT id, company_name, proxy_end_date 
                FROM business 
                WHERE is_deleted = 0
                AND proxy_end_date IS NOT NULL 
                AND proxy_end_date != '' 
                AND date(proxy_end_date) <= date('now', '+' || ? || ' days')
                ORDER BY proxy_end_date ASC
            """
            self.cursor.execute(query, (str(days),))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting expiration reminders: {e}")
            return []

    def get_contracts_expiring(self, days):
        """获取即将到期的合同
        参数:
            days: 提前提醒的天数
        返回:
            即将到期的合同列表 (id, title, expiration_date)
        """
        try:
            if not hasattr(self, 'cursor'):
                self.cursor = self.conn.cursor()
                
            query = """
                SELECT id, title, expiration_date 
                FROM contracts 
                WHERE is_deleted = 0
                AND expiration_date IS NOT NULL 
                AND expiration_date != '' 
                AND date(expiration_date) <= date('now', '+' || ? || ' days')
                ORDER BY expiration_date ASC
            """
            self.cursor.execute(query, (str(days),))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting contract expiration reminders: {e}")
            return []

    def get_business_distribution(self):
        """获取业务分布数据 (用于饼图)
        返回:
            字典 {业务类型: 数量}
        """
        try:
            query = """
                SELECT deal_business, COUNT(*) 
                FROM business 
                WHERE is_deleted = 0 AND deal_business IS NOT NULL AND deal_business != ''
                GROUP BY deal_business
            """
            results = self.execute_query(query)
            
            distribution = {}
            for row in results:
                distribution[row[0]] = row[1]
                
            return distribution
        except Exception as e:
            logger.error(f"Error getting business distribution: {e}")
            return {}

    def get_all_customers(self):
        """获取所有客户数据
        返回:
            客户数据列表，每个客户是一个字典
        """
        try:
            if not hasattr(self, 'cursor'):
                self.cursor = self.conn.cursor()
                
            self.cursor.execute("""
                SELECT id, name, phone, email, address, created_at 
                FROM customers
                ORDER BY name
            """)
            
            columns = [desc[0] for desc in self.cursor.description]
            customers = []
            for row in self.cursor.fetchall():
                customers.append(dict(zip(columns, row)))
                
            return customers
        except sqlite3.Error as e:
            logger.error(f"Error getting customer list: {e}")
            return []
