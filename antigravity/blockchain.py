"""
Blockchain implementation for DocuTrace.
Provides an immutable, tamper-evident cryptographic ledger
for storing document hashes, ownership metadata, and verification proofs.
"""

import hashlib
import json
import time
from datetime import datetime
from database import save_block_to_db, get_all_blocks_from_db


class Block:
    """Represents a single block in the DocuTrace blockchain."""

    def __init__(self, index, timestamp, doc_id, doc_hash, title, uploader, previous_hash, nonce=0, current_hash=None):
        self.index = index
        self.timestamp = timestamp
        self.doc_id = doc_id
        self.doc_hash = doc_hash
        self.title = title
        self.uploader = uploader
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = current_hash if current_hash else self.compute_hash()

    def compute_hash(self):
        """
        Calculates SHA-256 hash of the block contents.
        Any change to document metadata, hash, or previous block hash
        changes this block hash entirely.
        """
        block_content = {
            "index": self.index,
            "timestamp": self.timestamp,
            "doc_id": self.doc_id,
            "doc_hash": self.doc_hash,
            "title": self.title,
            "uploader": self.uploader,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        encoded_content = json.dumps(block_content, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded_content).hexdigest()

    def to_dict(self):
        """Return dictionary representation of the block."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "doc_id": self.doc_id,
            "doc_hash": self.doc_hash,
            "title": self.title,
            "uploader": self.uploader,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }


class Blockchain:
    """Manages the chain of blocks, proof-of-work, and authenticity verification."""

    def __init__(self, difficulty=2):
        self.chain = []
        # Proof-of-work difficulty: number of leading zeros (e.g. 2 for instant responsive demo)
        self.difficulty = difficulty
        self.load_or_initialize()

    def load_or_initialize(self):
        """Load blockchain from SQLite database or create genesis block."""
        db_blocks = get_all_blocks_from_db()
        if db_blocks:
            self.chain = []
            for b in db_blocks:
                block = Block(
                    index=b["block_index"],
                    timestamp=b["timestamp"],
                    doc_id=b["doc_id"],
                    doc_hash=b["doc_hash"],
                    title=b["title"],
                    uploader=b["uploader"],
                    previous_hash=b["previous_hash"],
                    nonce=b["nonce"],
                    current_hash=b["hash"]
                )
                self.chain.append(block)
        else:
            self.create_genesis_block()

    def create_genesis_block(self):
        """Generate the first block in the blockchain."""
        genesis_block = Block(
            index=0,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            doc_id="GENESIS",
            doc_hash="0000000000000000000000000000000000000000000000000000000000000000",
            title="DocuTrace Genesis Root Block",
            uploader="System Root Authority",
            previous_hash="0" * 64,
            nonce=0
        )
        mined_block = self.proof_of_work(genesis_block)
        self.chain.append(mined_block)
        self._persist_block(mined_block)
        return mined_block

    @property
    def last_block(self):
        """Returns the most recent block in the chain."""
        return self.chain[-1]

    def proof_of_work(self, block):
        """
        Proof of Work consensus mechanism:
        Increments nonce until hash satisfies difficulty criteria (e.g., starts with '00').
        """
        prefix = "0" * self.difficulty
        while not block.compute_hash().startswith(prefix):
            block.nonce += 1
        block.hash = block.compute_hash()
        return block

    def add_document_block(self, doc_id, doc_hash, title, uploader):
        """
        Mines and registers a new document record onto the blockchain.
        Returns the created block.
        """
        previous_block = self.last_block
        new_block = Block(
            index=len(self.chain),
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            doc_id=doc_id,
            doc_hash=doc_hash,
            title=title,
            uploader=uploader,
            previous_hash=previous_block.hash,
            nonce=0
        )

        mined_block = self.proof_of_work(new_block)
        self.chain.append(mined_block)
        self._persist_block(mined_block)
        return mined_block

    def _persist_block(self, block):
        """Saves a block to the SQLite database."""
        save_block_to_db(
            block_index=block.index,
            timestamp=block.timestamp,
            doc_id=block.doc_id,
            doc_hash=block.doc_hash,
            title=block.title,
            uploader=block.uploader,
            previous_hash=block.previous_hash,
            nonce=block.nonce,
            current_hash=block.hash
        )

    def is_chain_valid(self):
        """
        Validates cryptographic integrity of the entire blockchain:
        1. Current block's recomputed hash must match its stored hash.
        2. Current block's previous_hash must match the hash of the preceding block.
        3. Block hash must satisfy proof-of-work difficulty.
        """
        prefix = "0" * self.difficulty

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Verify current block's hash integrity
            if current.hash != current.compute_hash():
                return False, f"Block #{current.index} has been altered! Hash mismatch."

            # Verify chain link
            if current.previous_hash != previous.hash:
                return False, f"Broken link between Block #{previous.index} and Block #{current.index}."

            # Verify proof of work
            if not current.hash.startswith(prefix):
                return False, f"Block #{current.index} fails proof-of-work difficulty requirement."

        return True, "Blockchain integrity verified. All blocks are cryptographically valid and linked."

    def find_block_by_doc_id(self, doc_id):
        """Find the block corresponding to a specific document ID."""
        for block in self.chain:
            if block.doc_id == doc_id:
                return block
        return None

    def find_block_by_doc_hash(self, doc_hash):
        """Find the block matching an exact document SHA-256 hash."""
        for block in self.chain:
            if block.doc_hash.lower() == doc_hash.lower():
                return block
        return None

    def get_chain_data(self):
        """Returns all blocks as list of dictionaries."""
        return [b.to_dict() for b in self.chain]
