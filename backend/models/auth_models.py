"""
SQLAlchemy models for User and Document tables.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Boolean, Date
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to documents
    documents = relationship("Document", back_populates="owner")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doc_type = Column(String, nullable=False)  # "aadhaar" or "pan"
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_data = Column(LargeBinary, nullable=False)  # Stored as encrypted BLOB
    encryption_nonce = Column(String, nullable=True)   # AES-GCM nonce (base64)
    is_encrypted = Column(Boolean, default=True)       # Encryption flag
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to user
    owner = relationship("User", back_populates="documents")


class BlockchainRecord(Base):
    """
    Simulated blockchain ledger for document integrity.
    Stores cryptographic hashes of documents, not the documents themselves.
    """
    __tablename__ = "blockchain_ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    doc_type = Column(String, nullable=False)
    doc_hash = Column(String, nullable=False) # SHA-256 hash
    timestamp = Column(DateTime, default=datetime.utcnow)

class CitizenProfile(Base):
    __tablename__ = "citizen_profiles"

    user_id = Column(Integer, primary_key=True)
    employment_type = Column(String)  # salaried | business | freelancer | unemployed
    salary_range = Column(String)     # 0-5L | 5-10L | 10-20L | 20L+
    senior_citizen = Column(Boolean)
    itr_filed_last_year = Column(Boolean)
    past_notice_types = Column(String)  # Storing as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PassportTracking(Base):
    __tablename__ = "passport_tracking"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    application_date = Column(Date)
    application_type = Column(String)  # Normal / Tatkaal
    police_verification = Column(String, default="Pending")  # Pending / Completed
    passport_received = Column(Boolean, default=False)
    notified_delay = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
