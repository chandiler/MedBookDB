# transaction_manager.py

import psycopg
from contextlib import contextmanager
from config import DB_CONFIG


# 创建数据库连接
# Create database connection
def get_connection():
    # 连接PostgreSQL数据库
    # Connect to PostgreSQL database
    conn = psycopg.connect(
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
    )
    return conn


# 写入审计日志的辅助函数
# Helper function to write audit log
def log_action(result, user_id, action, target_table, target_id, details):
    # result 可以是 'COMMIT' 或 'ROLLBACK'
    # result can be 'COMMIT' or 'ROLLBACK'
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log (user_id, action, target_table, target_id, details)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    f"{action}_{result}",
                    target_table,
                    target_id,
                    details,
                ),
            )
        conn.commit()
    except Exception as log_err:
        # 如果日志写入失败，仅打印错误，不影响主逻辑
        # If logging fails, print the error but do not raise
        print("Audit log write failed:", log_err)
    finally:
        conn.close()


# 统一事务控制上下文
# Unified transaction control context
@contextmanager
def transaction(user_id=None, action=None, target_table=None, target_id=None):
    # 上下文管理事务，进入时BEGIN，正常结束时COMMIT，异常时ROLLBACK
    # Manage transaction context: BEGIN on enter, COMMIT on success, ROLLBACK on error
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
        # 成功时写入日志
        # Write audit log when transaction commits
        if user_id:
            log_action(
                "COMMIT",
                user_id,
                action or "UNKNOWN_ACTION",
                target_table or "UNKNOWN_TABLE",
                target_id or 0,
                "Transaction committed successfully",
            )
    except Exception as e:
        conn.rollback()
        print("Transaction rolled back due to error:", e)
        # 回滚后写入日志（使用新连接）
        # After rollback, write audit log with a new connection
        if user_id:
            log_action(
                "ROLLBACK",
                user_id,
                action or "UNKNOWN_ACTION",
                target_table or "UNKNOWN_TABLE",
                target_id or 0,
                str(e),
            )
        raise e
    finally:
        conn.close()
