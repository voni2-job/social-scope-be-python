from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PageComment(Base):
    __tablename__ = "page_comments"

    id = Column(String, primary_key=True, index=True)
    created_time = Column(DateTime, nullable=False)
    message = Column(Text, nullable=True)
