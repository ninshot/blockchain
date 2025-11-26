from collections.abc import AsyncGenerator
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Integer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

DATABASE_URL = "sqlite+aiosqlite:///./blockchain.db"

class Base(DeclarativeBase):
    pass

class Block(Base):
    __tablename__ = "blocks"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    proof = Column(Integer, nullable=False)
    previous_hash = Column(String, nullable=False)
    transactions = relationship("Transaction", back_populates="block")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(Integer, ForeignKey("blocks.id"), nullable=True)
    sender = Column(Text, nullable=False)
    recipient = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    signature = Column(Text, nullable=True)

    block = relationship("Block", back_populates="transactions",)

class Wallet(Base):
    __tablename__ = "wallets"
    public_key = Column(Text, primary_key=True, index=True)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tableS():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session