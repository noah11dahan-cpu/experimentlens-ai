# app/models.py
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from .db import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    hypothesis = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # One-to-many: Experiment → Variants
    variants = relationship(
        "Variant",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )


class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)

    name = Column(String, nullable=False)  # e.g. "A", "B"
    users = Column(Integer, nullable=False)
    conversions = Column(Integer, nullable=False)
    conversion_rate = Column(Float, nullable=False)
    uplift = Column(Float, nullable=True)   # might be None for control variant
    p_value = Column(Float, nullable=True)  # might be None for control variant

    experiment = relationship("Experiment", back_populates="variants")
