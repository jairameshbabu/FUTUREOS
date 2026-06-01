from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    type = Column(String, index=True)  
    description = Column(String)

    sources = relationship("SignalSource", back_populates="entity", cascade="all, delete-orphan")
    signals = relationship("SignalData", back_populates="entity", cascade="all, delete-orphan")
    # New Stage 2 Relationship
    dependencies = relationship("DependencyEdge", back_populates="entity", cascade="all, delete-orphan")

class SignalSource(Base):
    __tablename__ = "signal_sources"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    source_type = Column(String)  
    source_url = Column(String)

    entity = relationship("Entity", back_populates="sources")

class SignalData(Base):
    __tablename__ = "signal_data"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    metric_type = Column(String)  
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    entity = relationship("Entity", back_populates="signals")

# --- NEW STAGE 2 MODELS (Systemic Risk Graph) ---

class TechNode(Base):
    __tablename__ = "tech_nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String) # e.g., 'infrastructure', 'payment_gateway', 'regulation'
    description = Column(String)
    base_fragility = Column(Float, default=0.0) # 0.0 to 1.0 (Inherent vulnerability)

    dependent_entities = relationship("DependencyEdge", back_populates="tech_node", cascade="all, delete-orphan")

class DependencyEdge(Base):
    __tablename__ = "dependency_edges"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    tech_node_id = Column(Integer, ForeignKey("tech_nodes.id"))
    dependency_weight = Column(Float, default=1.0) # 0.1 (low reliance) to 1.0 (critical failure point)

    entity = relationship("Entity", back_populates="dependencies")
    tech_node = relationship("TechNode", back_populates="dependent_entities")