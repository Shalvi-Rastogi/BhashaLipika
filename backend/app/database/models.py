from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.database import Base


class Document(Base):
	__tablename__ = "documents"

	id = Column(Integer, primary_key=True, index=True)
	original_filename = Column(String(255), nullable=False)
	file_type = Column(String(20), nullable=False)
	source_language = Column(String(20), nullable=False, default="en")
	target_language = Column(String(20), nullable=False)
	status = Column(String(30), nullable=False, default="uploaded")
	uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
	output_filename = Column(String(255), nullable=True)
