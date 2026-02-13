from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from server.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    queries_remaining = Column(Integer, nullable=False, default=50)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, onupdate=func.now())

    query_logs = relationship("QueryLog", back_populates="user")


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_hash = Column(String, nullable=False)
    tokens_used = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="query_logs")
