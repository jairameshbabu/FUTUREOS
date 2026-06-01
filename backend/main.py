from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from scoring import calculate_emergence_scores

app = FastAPI(title="SaaS Investment Engine API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulationPayload(BaseModel):
    weight_mrr: float
    weight_growth: float
    weight_efficiency: float
    shocked_node_name: Optional[str] = None

@app.get("/api/baseline")
def get_baseline_rankings(db: Session = Depends(get_db)):
    try:
        # Pass None for the shock on initial load
        return calculate_emergence_scores(db, 33.3, 33.3, 33.3, None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate")
def run_simulation(payload: SimulationPayload, db: Session = Depends(get_db)):
    try:
        return calculate_emergence_scores(
            db, 
            payload.weight_mrr, 
            payload.weight_growth, 
            payload.weight_efficiency,
            payload.shocked_node_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))