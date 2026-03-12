import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.auth_models import BlockchainRecord

def generate_hash(file_bytes: bytes) -> str:
    """
    Generate a SHA-256 hash for the given file bytes.
    """
    return hashlib.sha256(file_bytes).hexdigest()

def record_on_blockchain(db: Session, user_id: int, doc_type: str, doc_hash: str):
    """
    Store the document hash in the simulated blockchain ledger.
    If a record already exists for this user and doc_type, update it.
    """
    existing = db.query(BlockchainRecord).filter(
        BlockchainRecord.user_id == user_id,
        BlockchainRecord.doc_type == doc_type
    ).first()

    if existing:
        existing.doc_hash = doc_hash
        existing.timestamp = datetime.utcnow()
    else:
        record = BlockchainRecord(
            user_id=user_id,
            doc_type=doc_type,
            doc_hash=doc_hash
        )
        db.add(record)
    
    db.commit()

def verify_integrity(db: Session, user_id: int, doc_type: str, current_file_bytes: bytes) -> dict:
    """
    Verify the integrity of a document by comparing its current hash
    with the hash stored on the blockchain.
    """
    current_hash = generate_hash(current_file_bytes)
    
    record = db.query(BlockchainRecord).filter(
        BlockchainRecord.user_id == user_id,
        BlockchainRecord.doc_type == doc_type
    ).first()

    if not record:
        return {
            "authentic": False,
            "error": "No blockchain record found for this document.",
            "current_hash": current_hash,
            "stored_hash": None
        }

    is_authentic = (current_hash == record.doc_hash)
    
    return {
        "authentic": is_authentic,
        "current_hash": current_hash,
        "stored_hash": record.doc_hash,
        "timestamp": record.timestamp.isoformat() if record.timestamp else None
    }
