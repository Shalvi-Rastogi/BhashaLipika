from app.database.database import engine, Base
from app.database.models import Document

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")