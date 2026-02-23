import sqlite3
from core.logger import logger

class MigrationManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def run_migrations(self):
        """Execute all migrations"""
        conn = self.db_manager.conn
        cursor = conn.cursor()
        
        migrations = [
            self._add_soft_delete_columns,
            self._add_customer_fields,
            self._add_business_fields,
            self._add_finance_fields,
            self._add_contract_fields
        ]
        
        for migration in migrations:
            try:
                migration(cursor)
            except Exception as e:
                logger.error(f"Migration failed {migration.__name__}: {e}")
        
        conn.commit()

    def _add_soft_delete_columns(self, cursor):
        tables = ['finance', 'customers', 'business']
        for table in tables:
            self._ensure_column(cursor, table, 'is_deleted', 'INTEGER DEFAULT 0')
            self._ensure_column(cursor, table, 'deleted_at', 'TEXT')

    def _add_customer_fields(self, cursor):
        self._ensure_column(cursor, 'customers', 'position', 'TEXT')
        self._ensure_column(cursor, 'customers', 'mobile', 'TEXT')
        self._ensure_column(cursor, 'customers', 'email', 'TEXT')

    def _add_business_fields(self, cursor):
        self._ensure_column(cursor, 'business', 'business_type', 'TEXT')

    def _add_finance_fields(self, cursor):
        self._ensure_column(cursor, 'finance', 'pending_amount', 'REAL DEFAULT 0')
        self._ensure_column(cursor, 'finance', 'pending_date', 'TEXT')

    def _add_contract_fields(self, cursor):
        self._ensure_column(cursor, 'contracts', 'category_ids', 'TEXT')

    def _ensure_column(self, cursor, table, column, definition):
        """Helper to add column if it doesn't exist"""
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = {row[1] for row in cursor.fetchall()}
            if column not in columns:
                logger.info(f"Adding column {column} to {table}")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except Exception as e:
            logger.error(f"Error checking/adding column {column} to {table}: {e}")
