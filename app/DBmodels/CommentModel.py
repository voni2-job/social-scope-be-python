from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from core.database import Base

class PageComment(Base):
    __tablename__ = "page_comments"
    comment_id = Column(String, primary_key=True, index=True)
    created_time = Column(DateTime(timezone=True), nullable=False)
    message = Column(Text, nullable=False)
 
