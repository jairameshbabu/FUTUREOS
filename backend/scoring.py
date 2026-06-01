import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy.orm import Session
from sqlalchemy import text 
import networkx as nx

def calculate_emergence_scores(db: Session, w_mrr: float, w_growth: float, w_efficiency: float, shocked_node_name: str = None):
    query = """
        SELECT sd.entity_id, sd.metric_type, sd.value, e.name, e.type, e.description
        FROM signal_data sd
        JOIN entities e ON sd.entity_id = e.id
        WHERE sd.id IN (
            SELECT MAX(id)
            FROM signal_data
            GROUP BY entity_id, metric_type
        )
    """
    result = db.execute(text(query)).fetchall()
    if not result:
        return {"rankings": [], "graph": {"nodes": [], "links": []}}

    data = [{"entity_id": r[0], "metric_type": r[1], "value": r[2], "name": r[3], "type": r[4], "description": r[5]} for r in result]
    df = pd.DataFrame(data)

    df_pivoted = df.pivot(index=["entity_id", "name", "type", "description"], 
                          columns="metric_type", 
                          values="value").reset_index()

    metrics_to_scale = ["mrr", "yoy_growth", "ltv_cac_ratio"]
    for col in metrics_to_scale:
        if col not in df_pivoted.columns:
            df_pivoted[col] = 0.0

    scaler = MinMaxScaler()
    for metric in metrics_to_scale:
        min_val = df_pivoted[metric].min()
        max_val = df_pivoted[metric].max()
        if max_val == min_val:
            df_pivoted[f"norm_{metric}"] = 1.0
        else:
            df_pivoted[f"norm_{metric}"] = scaler.fit_transform(df_pivoted[[metric]])

    total_weight = w_mrr + w_growth + w_efficiency
    if total_weight == 0:
        w_m, w_g, w_e = 0.333, 0.333, 0.333
    else:
        w_m = w_mrr / total_weight
        w_g = w_growth / total_weight
        w_e = w_efficiency / total_weight

    df_pivoted["base_score"] = (
        df_pivoted["norm_mrr"] * w_m +
        df_pivoted["norm_yoy_growth"] * w_g +
        df_pivoted["norm_ltv_cac_ratio"] * w_e
    ) * 100.0

    tech_nodes_query = "SELECT id, name, category, base_fragility FROM tech_nodes"
    tech_nodes_data = db.execute(text(tech_nodes_query)).fetchall()
    
    edges_query = """
        SELECT de.entity_id, e.name AS entity_name, de.tech_node_id, tn.name AS node_name, de.dependency_weight 
        FROM dependency_edges de
        JOIN entities e ON de.entity_id = e.id
        JOIN tech_nodes tn ON de.tech_node_id = tn.id
    """
    edges_data = db.execute(text(edges_query)).fetchall()

    G = nx.DiGraph()
    graph_payload = {"nodes": [], "links": []}

    for t_id, t_name, cat, frag in tech_nodes_data:
        node_key = f"Tech_{t_id}"
        G.add_node(node_key, type="tech", name=t_name, fragility=frag)
        is_shocked = True if shocked_node_name == t_name else False
        graph_payload["nodes"].append({
            "id": node_key, "name": t_name, "group": "tech", "is_shocked": is_shocked
        })

    penalties = {}
    for e_id, e_name, t_id, t_name, weight in edges_data:
        entity_key = f"Entity_{e_id}"
        tech_key = f"Tech_{t_id}"
        
        G.add_edge(entity_key, tech_key, weight=weight)
        graph_payload["links"].append({
            "source": entity_key, "target": tech_key, "value": weight
        })

        if shocked_node_name and shocked_node_name == t_name:
            penalty_impact = weight * 45.0
            if e_id in penalties:
                penalties[e_id] += penalty_impact
            else:
                penalties[e_id] = penalty_impact

    def apply_penalty(row):
        e_id = row["entity_id"]
        penalty = penalties.get(e_id, 0.0)
        final_score = row["base_score"] - penalty
        return max(0.0, final_score)

    df_pivoted["emergence_score"] = df_pivoted.apply(apply_penalty, axis=1)
    df_ranked = df_pivoted.sort_values(by="emergence_score", ascending=False)

    ranked_output = []
    for idx, row in enumerate(df_ranked.to_dict(orient="records"), start=1):
        entity_key = f"Entity_{row['entity_id']}"
        graph_payload["nodes"].append({"id": entity_key, "name": row["name"], "group": "startup"})
        penalty_taken = round(penalties.get(row['entity_id'], 0.0), 1)

        ranked_output.append({
            "rank": idx, "entity_id": row["entity_id"], "name": row["name"], "description": row["description"],
            "emergence_score": round(row["emergence_score"], 1), "penalty_taken": penalty_taken,
            "raw_metrics": {"mrr": round(row["mrr"], 1), "yoy_growth": round(row["yoy_growth"], 1), "ltv_cac_ratio": round(row["ltv_cac_ratio"], 1)}
        })

    return {
        "rankings": ranked_output,
        "graph": graph_payload
    }