import uuid
import json
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    recommended_route = Column(String(30), nullable=False) # 'Repair', 'Resell', 'Donate', 'Refurbish', 'Recycle'
    overall_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    weights_used = Column(Text, default="{}") # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="recommendations")
    device = relationship("Device", back_populates="recommendations")
    scores = relationship("RecommendationScore", back_populates="recommendation", cascade="all, delete-orphan")

class RecommendationScore(Base):
    __tablename__ = "recommendation_scores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recommendation_id = Column(String(36), ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True)
    route = Column(String(30), nullable=False) # 'Repair', 'Resell', 'Donate', 'Refurbish', 'Recycle'
    is_eligible = Column(Boolean, nullable=False)
    final_score = Column(Float, nullable=False)
    financial_score = Column(Float, nullable=False)
    useful_life_score = Column(Float, nullable=False)
    convenience_score = Column(Float, nullable=False)
    reuse_score = Column(Float, nullable=False)
    ineligible_reason = Column(Text, nullable=True)
    score_breakdown = Column(Text, default="{}") # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    recommendation = relationship("Recommendation", back_populates="scores")

    def get_breakdown(self):
        try:
            return json.loads(self.score_breakdown) if self.score_breakdown else {}
        except Exception:
            return {}
