from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL connection URL
# 把下面的密码换成你自己安装 PostgreSQL 时设置的那个
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:你的密码@localhost:5432/healthcare"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
