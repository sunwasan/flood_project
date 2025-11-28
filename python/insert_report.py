import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Load environment variables
load_dotenv()


DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST =  os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "report_db")


# create db if not exists
import psycopg2

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE {DB_NAME};")
    cursor.close()
    conn.close()
    print(f"Database '{DB_NAME}' created successfully.")
except psycopg2.Error as e:
    if e.pgcode == '42P04':  # DuplicateDatabase error code
        print(f"Database '{DB_NAME}' already exists.")
    else:
        print(f"Error creating database: {e}")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 3. Setup SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 4. Define a Model (Table Schema)
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True, nullable=True)
    reporter_line_id = Column(String, unique=False, index=False, nullable=True)
    reporter_email = Column(String, index=False, nullable=True)
    province = Column(String, index=True)
    district = Column(String, index=True)
    sub_district = Column(String, index=True)
    address = Column(String)
    content = Column(String)
    urgency = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
# 5. Create the table
Base.metadata.create_all(bind=engine)

# 6. Function to insert data
def insert_db(
    message_id: str,
    province: str,
    district: str,
    sub_district: str,
    address: str,
    content: str,
    urgency: str,
    timestamp: datetime = datetime.utcnow(),
    reporter_line_id: str = None,
    reporter_email: str = None,
):
    session = SessionLocal()
    try:
        new_report = Report(
            message_id=message_id,
            province=province,
            district=district,
            sub_district=sub_district,
            address=address,
            content=content,
            urgency=urgency,
            timestamp=timestamp,
            reporter_line_id=reporter_line_id,
            reporter_email=reporter_email
        )
        session.add(new_report)
        session.commit()
        session.refresh(new_report)
        print(f"✅ Data inserted successfully: ID {new_report.id} - {new_report.province}, {new_report.district}, {new_report.sub_district}")
        return new_report
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()

# Usage Example
if __name__ == "__main__":
    insert_report("Pathum Thani Market", 14.0208, 100.5204, 1.5, "Critical")