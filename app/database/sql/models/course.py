from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.sql.db import Base


class Module(Base):
    __tablename__ = "modules"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    order = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chapters = relationship(
        "Chapter",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Chapter.order",
        lazy="selectin",
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(String(64), primary_key=True, index=True)
    module_id = Column(String(64), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    order = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    module = relationship("Module", back_populates="chapters")
    topics = relationship(
        "Topic",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="Topic.order",
        lazy="selectin",
    )


class Topic(Base):
    __tablename__ = "topics"

    id = Column(String(64), primary_key=True, index=True)
    chapter_id = Column(String(64), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    content = Column(Text, default="", nullable=False)
    content_path = Column(String(512), nullable=True)
    question_type = Column(String(50), default="code", nullable=True)
    order = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chapter = relationship("Chapter", back_populates="topics")
    progresses = relationship(
        "UserTopicProgress",
        back_populates="topic",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UserTopicProgress(Base):
    __tablename__ = "user_topic_progress"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(String(64), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    topic = relationship("Topic", back_populates="progresses")

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic_progress"),
    )
