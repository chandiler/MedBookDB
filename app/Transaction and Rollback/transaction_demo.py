# transaction_demo.py

from transaction_manager import transaction


# 成功示例：插入两条用户记录都会提交
# Success example: both user insertions will be committed
def demo_success():
    # 演示正常事务，两条插入都成功
    # Demonstrate normal transaction: both inserts succeed
    with transaction() as cur:
        # 插入第一个用户
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, email)
            VALUES (%s, %s, %s, %s)
            """,
            ("user_success1", "hash123", "patient", "user1@example.com"),
        )

        # 插入第二个用户
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, email)
            VALUES (%s, %s, %s, %s)
            """,
            ("user_success2", "hash456", "doctor", "user2@example.com"),
        )

    # 执行到这里表示事务提交成功
    # If code reaches here, transaction was committed
    return "success committed"


# 失败示例：第二个插入故意违反唯一约束，触发回滚
# Failure example: second insert violates constraint, triggers rollback
def demo_fail():
    # 演示异常事务：第一条成功，第二条重复username导致失败
    # Demonstrate failing transaction: duplicate username causes rollback
    with transaction() as cur:
        # 插入第一个用户（暂存事务中）
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, email)
            VALUES (%s, %s, %s, %s)
            """,
            ("user_fail", "hash000", "patient", "fail1@example.com"),
        )

        # 第二个插入重复 username，触发唯一约束异常
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, email)
            VALUES (%s, %s, %s, %s)
            """,
            ("user_fail", "hash999", "doctor", "fail2@example.com"),
        )

    # 不会执行到这里
    # This line will not be reached
    return "should not reach"


if __name__ == "__main__":
    # 成功测试：两条用户记录都应写入
    # Success test: both records will be committed
    try:
        print(demo_success())
    except Exception as e:
        print("demo_success failed:", e)

    # 失败测试：没有任何记录应写入（事务被回滚）
    # Failure test: rollback removes both inserts
    try:
        print(demo_fail())
    except Exception as e:
        print("demo_fail rolled back:", e)
