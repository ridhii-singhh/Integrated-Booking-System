"""
State Manager for tracking transactions and system state
"""
import asyncio
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from models import TransactionStatus, TransactionState, ActionType
from config import settings

logger = logging.getLogger(__name__)

class StateManager:
    """Manages transaction state and system state"""
    
    def __init__(self):
        self.storage_type = settings.STATE_STORAGE_TYPE
        self.transactions: Dict[str, TransactionStatus] = {}
        self.db_connection = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the state manager"""
        if self._initialized:
            return
        
        try:
            if self.storage_type == "memory":
                await self._init_memory_storage()
            elif self.storage_type == "sqlite":
                await self._init_sqlite_storage()
            elif self.storage_type == "postgres":
                await self._init_postgres_storage()
            else:
                logger.warning(f"Unknown storage type: {self.storage_type}, using memory")
                await self._init_memory_storage()
            
            self._initialized = True
            logger.info(f"✅ State Manager initialized with {self.storage_type} storage")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize State Manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.db_connection:
                await self.db_connection.close()
            logger.info("✅ State Manager cleanup completed")
        except Exception as e:
            logger.error(f"❌ State Manager cleanup failed: {e}")
    
    # =============================================================================
    # STORAGE INITIALIZATION
    # =============================================================================
    
    async def _init_memory_storage(self):
        """Initialize in-memory storage"""
        self.transactions = {}
        logger.info("📝 Using in-memory storage for state management")
    
    async def _init_sqlite_storage(self):
        """Initialize SQLite storage"""
        try:
            import aiosqlite
            
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            self.db_connection = await aiosqlite.connect(db_path)
            
            # Create tables
            await self._create_sqlite_tables()
            
            logger.info(f"📝 Using SQLite storage: {db_path}")
            
        except ImportError:
            logger.error("❌ aiosqlite not installed, falling back to memory storage")
            await self._init_memory_storage()
        except Exception as e:
            logger.error(f"❌ SQLite initialization failed: {e}")
            await self._init_memory_storage()
    
    async def _init_postgres_storage(self):
        """Initialize PostgreSQL storage"""
        try:
            import asyncpg
            
            self.db_connection = await asyncpg.connect(settings.DATABASE_URL)
            
            # Create tables
            await self._create_postgres_tables()
            
            logger.info("📝 Using PostgreSQL storage")
            
        except ImportError:
            logger.error("❌ asyncpg not installed, falling back to memory storage")
            await self._init_memory_storage()
        except Exception as e:
            logger.error(f"❌ PostgreSQL initialization failed: {e}")
            await self._init_memory_storage()
    
    async def _create_sqlite_tables(self):
        """Create SQLite tables"""
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_id TEXT,
                original_request TEXT NOT NULL,
                state_history TEXT NOT NULL,
                call_details TEXT,
                final_result TEXT
            )
        """)
        await self.db_connection.commit()
    
    async def _create_postgres_tables(self):
        """Create PostgreSQL tables"""
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                user_id TEXT,
                original_request JSONB NOT NULL,
                state_history JSONB NOT NULL,
                call_details JSONB,
                final_result JSONB
            )
        """)
    
    # =============================================================================
    # TRANSACTION MANAGEMENT
    # =============================================================================
    
    async def create_transaction(self, action_type: str, user_request: Dict[str, Any], user_id: Optional[str] = None) -> str:
        """Create a new transaction"""
        try:
            transaction_id = str(uuid.uuid4())
            now = datetime.now()
            
            transaction = TransactionStatus(
                transaction_id=transaction_id,
                action_type=ActionType(action_type),
                state=TransactionState.CREATED,
                created_at=now,
                updated_at=now,
                user_id=user_id,
                original_request=user_request,
                state_history=[{
                    "state": TransactionState.CREATED.value,
                    "timestamp": now.isoformat(),
                    "details": {"action": "transaction_created"}
                }]
            )
            
            await self._store_transaction(transaction)
            
            logger.info(f"✅ Created transaction: {transaction_id} ({action_type})")
            return transaction_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create transaction: {e}")
            raise
    
    async def update_transaction(self, transaction_id: str, new_state: str, details: Optional[Dict[str, Any]] = None):
        """Update transaction state"""
        try:
            transaction = await self.get_transaction_status(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction not found: {transaction_id}")
            
            now = datetime.now()
            
            # Update state
            transaction.state = TransactionState(new_state)
            transaction.updated_at = now
            
            # Add to state history
            history_entry = {
                "state": new_state,
                "timestamp": now.isoformat(),
                "details": details or {}
            }
            transaction.state_history.append(history_entry)
            
            # Store specific details
            if new_state == "call_triggered" and details:
                transaction.call_details = details.get("call_result", {})
            elif new_state in ["completed", "failed"] and details:
                transaction.final_result = details
            
            await self._store_transaction(transaction)
            
            logger.info(f"✅ Updated transaction {transaction_id}: {new_state}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update transaction {transaction_id}: {e}")
            raise
    
    async def get_transaction_status(self, transaction_id: str) -> Optional[TransactionStatus]:
        """Get transaction status"""
        try:
            if self.storage_type == "memory":
                return self.transactions.get(transaction_id)
            elif self.storage_type == "sqlite":
                return await self._get_sqlite_transaction(transaction_id)
            elif self.storage_type == "postgres":
                return await self._get_postgres_transaction(transaction_id)
            else:
                return self.transactions.get(transaction_id)
                
        except Exception as e:
            logger.error(f"❌ Failed to get transaction {transaction_id}: {e}")
            return None
    
    async def list_transactions(self, limit: int = 50, offset: int = 0, user_id: Optional[str] = None) -> List[TransactionStatus]:
        """List transactions with pagination"""
        try:
            if self.storage_type == "memory":
                return await self._list_memory_transactions(limit, offset, user_id)
            elif self.storage_type == "sqlite":
                return await self._list_sqlite_transactions(limit, offset, user_id)
            elif self.storage_type == "postgres":
                return await self._list_postgres_transactions(limit, offset, user_id)
            else:
                return await self._list_memory_transactions(limit, offset, user_id)
                
        except Exception as e:
            logger.error(f"❌ Failed to list transactions: {e}")
            return []
    
    async def cleanup_old_transactions(self, days: int = 30):
        """Clean up transactions older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            if self.storage_type == "memory":
                to_remove = [
                    tid for tid, tx in self.transactions.items() 
                    if tx.created_at < cutoff_date
                ]
                for tid in to_remove:
                    del self.transactions[tid]
                    
            elif self.storage_type == "sqlite":
                await self.db_connection.execute(
                    "DELETE FROM transactions WHERE created_at < ?",
                    (cutoff_date.isoformat(),)
                )
                await self.db_connection.commit()
                
            elif self.storage_type == "postgres":
                await self.db_connection.execute(
                    "DELETE FROM transactions WHERE created_at < $1",
                    cutoff_date
                )
            
            logger.info(f"✅ Cleaned up transactions older than {days} days")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old transactions: {e}")
    
    # =============================================================================
    # STORAGE IMPLEMENTATIONS
    # =============================================================================
    
    async def _store_transaction(self, transaction: TransactionStatus):
        """Store transaction based on storage type"""
        if self.storage_type == "memory":
            self.transactions[transaction.transaction_id] = transaction
        elif self.storage_type == "sqlite":
            await self._store_sqlite_transaction(transaction)
        elif self.storage_type == "postgres":
            await self._store_postgres_transaction(transaction)
        else:
            self.transactions[transaction.transaction_id] = transaction
    
    async def _store_sqlite_transaction(self, transaction: TransactionStatus):
        """Store transaction in SQLite"""
        await self.db_connection.execute("""
            INSERT OR REPLACE INTO transactions 
            (transaction_id, action_type, state, created_at, updated_at, user_id, 
             original_request, state_history, call_details, final_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction.transaction_id,
            transaction.action_type.value,
            transaction.state.value,
            transaction.created_at.isoformat(),
            transaction.updated_at.isoformat(),
            transaction.user_id,
            json.dumps(transaction.original_request),
            json.dumps(transaction.state_history),
            json.dumps(transaction.call_details) if transaction.call_details else None,
            json.dumps(transaction.final_result) if transaction.final_result else None
        ))
        await self.db_connection.commit()
    
    async def _store_postgres_transaction(self, transaction: TransactionStatus):
        """Store transaction in PostgreSQL"""
        await self.db_connection.execute("""
            INSERT INTO transactions 
            (transaction_id, action_type, state, created_at, updated_at, user_id, 
             original_request, state_history, call_details, final_result)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (transaction_id) DO UPDATE SET
                action_type = EXCLUDED.action_type,
                state = EXCLUDED.state,
                updated_at = EXCLUDED.updated_at,
                user_id = EXCLUDED.user_id,
                original_request = EXCLUDED.original_request,
                state_history = EXCLUDED.state_history,
                call_details = EXCLUDED.call_details,
                final_result = EXCLUDED.final_result
        """, 
            transaction.transaction_id,
            transaction.action_type.value,
            transaction.state.value,
            transaction.created_at,
            transaction.updated_at,
            transaction.user_id,
            transaction.original_request,
            transaction.state_history,
            transaction.call_details,
            transaction.final_result
        )
    
    async def _get_sqlite_transaction(self, transaction_id: str) -> Optional[TransactionStatus]:
        """Get transaction from SQLite"""
        cursor = await self.db_connection.execute(
            "SELECT * FROM transactions WHERE transaction_id = ?",
            (transaction_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        
        return TransactionStatus(
            transaction_id=row[0],
            action_type=ActionType(row[1]),
            state=TransactionState(row[2]),
            created_at=datetime.fromisoformat(row[3]),
            updated_at=datetime.fromisoformat(row[4]),
            user_id=row[5],
            original_request=json.loads(row[6]),
            state_history=json.loads(row[7]),
            call_details=json.loads(row[8]) if row[8] else None,
            final_result=json.loads(row[9]) if row[9] else None
        )
    
    async def _get_postgres_transaction(self, transaction_id: str) -> Optional[TransactionStatus]:
        """Get transaction from PostgreSQL"""
        row = await self.db_connection.fetchrow(
            "SELECT * FROM transactions WHERE transaction_id = $1",
            transaction_id
        )
        if not row:
            return None
        
        return TransactionStatus(
            transaction_id=row['transaction_id'],
            action_type=ActionType(row['action_type']),
            state=TransactionState(row['state']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            user_id=row['user_id'],
            original_request=row['original_request'],
            state_history=row['state_history'],
            call_details=row['call_details'],
            final_result=row['final_result']
        )
    
    async def _list_memory_transactions(self, limit: int, offset: int, user_id: Optional[str]) -> List[TransactionStatus]:
        """List transactions from memory"""
        transactions = list(self.transactions.values())
        
        # Filter by user_id if provided
        if user_id:
            transactions = [tx for tx in transactions if tx.user_id == user_id]
        
        # Sort by created_at descending
        transactions.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        return transactions[offset:offset + limit]
    
    async def _list_sqlite_transactions(self, limit: int, offset: int, user_id: Optional[str]) -> List[TransactionStatus]:
        """List transactions from SQLite"""
        query = "SELECT * FROM transactions"
        params = []
        
        if user_id:
            query += " WHERE user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = await self.db_connection.execute(query, params)
        rows = await cursor.fetchall()
        
        transactions = []
        for row in rows:
            transaction = TransactionStatus(
                transaction_id=row[0],
                action_type=ActionType(row[1]),
                state=TransactionState(row[2]),
                created_at=datetime.fromisoformat(row[3]),
                updated_at=datetime.fromisoformat(row[4]),
                user_id=row[5],
                original_request=json.loads(row[6]),
                state_history=json.loads(row[7]),
                call_details=json.loads(row[8]) if row[8] else None,
                final_result=json.loads(row[9]) if row[9] else None
            )
            transactions.append(transaction)
        
        return transactions
    
    async def _list_postgres_transactions(self, limit: int, offset: int, user_id: Optional[str]) -> List[TransactionStatus]:
        """List transactions from PostgreSQL"""
        query = "SELECT * FROM transactions"
        params = []
        
        if user_id:
            query += " WHERE user_id = $1"
            params.append(user_id)
            query += " ORDER BY created_at DESC LIMIT $2 OFFSET $3"
            params.extend([limit, offset])
        else:
            query += " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
            params.extend([limit, offset])
        
        rows = await self.db_connection.fetch(query, *params)
        
        transactions = []
        for row in rows:
            transaction = TransactionStatus(
                transaction_id=row['transaction_id'],
                action_type=ActionType(row['action_type']),
                state=TransactionState(row['state']),
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                user_id=row['user_id'],
                original_request=row['original_request'],
                state_history=row['state_history'],
                call_details=row['call_details'],
                final_result=row['final_result']
            )
            transactions.append(transaction)
        
        return transactions
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for state manager"""
        try:
            if not self._initialized:
                return {"status": "unhealthy", "reason": "not_initialized"}
            
            # Test basic operations
            test_id = str(uuid.uuid4())
            test_transaction = TransactionStatus(
                transaction_id=test_id,
                action_type=ActionType.BOOKING,
                state=TransactionState.CREATED,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                original_request={"test": True},
                state_history=[]
            )
            
            # Store and retrieve test transaction
            await self._store_transaction(test_transaction)
            retrieved = await self.get_transaction_status(test_id)
            
            if retrieved and retrieved.transaction_id == test_id:
                # Clean up test transaction
                if self.storage_type == "memory":
                    del self.transactions[test_id]
                
                return {
                    "status": "healthy",
                    "storage_type": self.storage_type,
                    "transaction_count": len(self.transactions) if self.storage_type == "memory" else "N/A"
                }
            else:
                return {"status": "unhealthy", "reason": "storage_test_failed"}
                
        except Exception as e:
            logger.error(f"❌ State Manager health check failed: {e}")
            return {"status": "unhealthy", "reason": str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the state manager"""
        try:
            if self.storage_type == "memory":
                total_transactions = len(self.transactions)
                states = {}
                for tx in self.transactions.values():
                    state = tx.state.value
                    states[state] = states.get(state, 0) + 1
            else:
                # For database storage, we'd need to run queries
                total_transactions = 0
                states = {}
            
            return {
                "storage_type": self.storage_type,
                "total_transactions": total_transactions,
                "states_breakdown": states,
                "initialized": self._initialized
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get state manager stats: {e}")
            return {"error": str(e)}