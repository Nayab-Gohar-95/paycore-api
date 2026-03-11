from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    full_name  = Column(String(255), nullable=False)
    hashed_pw  = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    accounts   = relationship("Account", back_populates="owner")
