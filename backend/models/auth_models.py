"""
SQLAlchemy models for User and Document tables.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Boolean
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
