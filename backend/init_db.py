import datetime
import random
from database import engine, Base, SessionLocal
from models import Entity, SignalSource, SignalData, TechNode, DependencyEdge

def seed_database():
    # Drops existing tables to cleanly apply the new Stage 2 schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # 1. Seed SaaS Entities
    entities_data = [
        {"name": "Ramp", "type": "startup", "description": "Spend management, corporate cards, and automated finance operations.", "metrics": {"mrr": 83300000.0, "yoy_growth": 133.0, "ltv_cac_ratio": 3.8}},
        {"name": "Deel", "type": "startup", "description": "Global HR, payroll, and Employer of Record (EOR) platform.", "metrics": {"mrr": 85000000.0, "yoy_growth": 57.0, "ltv_cac_ratio": 4.5}},
        {"name": "Wiz", "type": "startup", "description": "Agentless cloud security posture management (CNAPP).", "metrics": {"mrr": 50000000.0, "yoy_growth": 80.0, "ltv_cac_ratio": 5.2}},
        {"name": "Retool", "type": "startup", "description": "Low-code platform for building internal business tools and dashboards.", "metrics": {"mrr": 12500000.0, "yoy_growth": 65.0, "ltv_cac_ratio": 4.0}},
        {"name": "Navan", "type": "startup", "description": "Corporate travel management and expense automation.", "metrics": {"mrr": 29100000.0, "yoy_growth": 40.0, "ltv_cac_ratio": 3.2}}
    ]

    entity_records = {}
    for item in entities_data:
        entity = Entity(name=item["name"], type=item["type"], description=item["description"])
        db.add(entity)
        db.commit()
        db.refresh(entity)
        entity_records[item["name"]] = entity.id

        db.add(SignalSource(entity_id=entity.id, source_type="pitch_deck_data", source_url=f"https://crunchbase.com/organization/{entity.name.lower()}"))

        # --> THE MISSING BLOCK: INJECTING THE ACTUAL METRICS <--
        for metric_type, val in item["metrics"].items():
            for months_ago in range(3, 0, -1):
                historical_val = val * (1.0 - (months_ago * random.uniform(0.03, 0.08)))
                db.add(SignalData(
                    entity_id=entity.id,
                    metric_type=metric_type,
                    value=historical_val,
                    timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=months_ago * 30)
                ))
            
            # Current value
            db.add(SignalData(
                entity_id=entity.id,
                metric_type=metric_type,
                value=val,
                timestamp=datetime.datetime.utcnow()
            ))

    # 2. Seed Infrastructure Tech Nodes
    tech_nodes_data = [
        {"name": "Stripe API", "category": "payment_gateway", "desc": "Core payment processing and issuing infrastructure.", "fragility": 0.1},
        {"name": "AWS us-east-1", "category": "cloud_infrastructure", "desc": "Primary Amazon Web Services data center cluster.", "fragility": 0.2},
        {"name": "OpenAI GPT-4", "category": "llm_provider", "desc": "Foundational AI model for text generation and routing.", "fragility": 0.4},
        {"name": "Global EOR Regulations", "category": "regulation", "desc": "Cross-border compliance and tax localization laws.", "fragility": 0.6}
    ]

    node_records = {}
    for item in tech_nodes_data:
        node = TechNode(name=item["name"], category=item["category"], description=item["desc"], base_fragility=item["fragility"])
        db.add(node)
        db.commit()
        db.refresh(node)
        node_records[item["name"]] = node.id

    # 3. Map the Dependency Edges (The Fragility Web)
    edges = [
        {"entity": "Ramp", "node": "Stripe API", "weight": 0.9},
        {"entity": "Ramp", "node": "AWS us-east-1", "weight": 0.5},
        {"entity": "Deel", "node": "Global EOR Regulations", "weight": 0.95},
        {"entity": "Deel", "node": "AWS us-east-1", "weight": 0.6},
        {"entity": "Wiz", "node": "AWS us-east-1", "weight": 0.8},
        {"entity": "Retool", "node": "OpenAI GPT-4", "weight": 0.7},
        {"entity": "Retool", "node": "AWS us-east-1", "weight": 0.4},
        {"entity": "Navan", "node": "Stripe API", "weight": 0.6},
        {"entity": "Navan", "node": "OpenAI GPT-4", "weight": 0.5}
    ]

    for edge in edges:
        db.add(DependencyEdge(
            entity_id=entity_records[edge["entity"]],
            tech_node_id=node_records[edge["node"]],
            dependency_weight=edge["weight"]
        ))

    db.commit()
    db.close()
    print("Stage 2 Complete: Database re-initialized with Entities, Tech Nodes, and Dependency Edges.")

if __name__ == "__main__":
    seed_database()