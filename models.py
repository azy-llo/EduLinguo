import json
from typing import Any, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class Level(db.Model):
    """Уровень CEFR: A1 … C1."""

    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    lessons: Mapped[list["Lesson"]] = relationship(
        "Lesson", back_populates="level", order_by="Lesson.order_index"
    )


class Lesson(db.Model):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    aspect: Mapped[str] = mapped_column(String(32), nullable=False, default="grammar")
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    theory: Mapped[str] = mapped_column(Text, default="")
    reading_passage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_exam: Mapped[bool] = mapped_column(Boolean, default=False)

    level: Mapped["Level"] = relationship("Level", back_populates="lessons")
    exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise", back_populates="lesson", order_by="Exercise.order_index"
    )


class Exercise(db.Model):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")

    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="exercises")

    def payload(self) -> dict[str, Any]:
        try:
            return json.loads(self.payload_json or "{}")
        except json.JSONDecodeError:
            return {}


class UserExerciseCompletion(db.Model):
    __tablename__ = "user_exercise_completions"
    __table_args__ = (UniqueConstraint("user_id", "exercise_id", name="uq_user_exercise"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False, index=True)
    completed_at: Mapped[object] = mapped_column(DateTime(timezone=True))


class UserLevelProgress(db.Model):
    """Экзамен уровня сдан — можно открыть следующий уровень."""

    __tablename__ = "user_level_progress"
    __table_args__ = (UniqueConstraint("user_id", "level_id", name="uq_user_level_progress"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False, index=True)
    exam_passed_at: Mapped[object] = mapped_column(DateTime(timezone=True))
