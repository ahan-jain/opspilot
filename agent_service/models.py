from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class RunStatus(enum.Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    NEEDS_APPROVAL = "needs_approval"

class Run(Base):
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    goal = Column(Text, nullable=False)
    status = Column(SQLEnum(RunStatus), default=RunStatus.RUNNING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    steps = relationship("Step", back_populates="run", cascade="all, delete-orphan")

class StepState(enum.Enum):
    PLAN = "plan"
    EXECUTE_TOOL = "execute_tool"
    EVALUATE = "evaluate"
    NEEDS_APPROVAL = "needs_approval"
    DONE = "done"
    FAILED = "failed"

class Step(Base):
    __tablename__ = "steps"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    state = Column(SQLEnum(StepState), nullable=False)
    step_number = Column(Integer, nullable=False)
    reasoning = Column(Text)  # LLM's reasoning for this step
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    run = relationship("Run", back_populates="steps")
    tool_calls = relationship("ToolCall", back_populates="step", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_run_id_step_number', 'run_id', 'step_number'),
        Index('idx_state', 'state'),
    )

class ToolCallStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_APPROVAL = "needs_approval"

class ToolCall(Base):
    __tablename__ = "tool_calls"
    
    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("steps.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    inputs = Column(Text)  # JSON string
    outputs = Column(Text)  # JSON string
    status = Column(SQLEnum(ToolCallStatus), default=ToolCallStatus.PENDING)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)
    
    # Relationships
    step = relationship("Step", back_populates="tool_calls")

    __table_args__ = (
        Index('idx_step_id_status', 'step_id', 'status'),
        Index('idx_tool_name', 'tool_name'),
    )