# crop_service.py

import json
import pandas as pd
from typing import Dict

def _load_crop_rules(filepath: str = "crop_knowledgebase.json") -> Dict:
    """Helper to load and parse crop rules from the JSON knowledge base."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            kb = json.load(f)
        
        crop_rules = {c["name"].lower(): c["rules"] for c in kb["crops"]}
        for c in kb["crops"]:
            for alias in c.get("aliases", []):
                crop_rules[alias.lower()] = c["rules"]
        return crop_rules
    except FileNotFoundError:
        raise FileNotFoundError(f"Knowledge base file not found at '{filepath}'")
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Error parsing knowledge base file: {e}") from e

def _generate_recommendation_for_row(row: pd.Series, rules: list) -> str:
    """Generates a recommendation string for a single day based on crop-specific rules."""
    recs = []
    for rule in rules:
        try:
            if eval(rule["when"], {}, row.to_dict()):
                recs.append(f"[{rule['severity'].upper()}] {rule['advisory']}")
        except Exception:
            continue
    return " | ".join(recs) if recs else "Conditions are favorable. Monitor the crop."

def get_crop_recommendation(weather_df: pd.DataFrame, crop_name: str) -> pd.DataFrame:
    """
    Adds crop-specific recommendations to a pre-existing weather DataFrame.
    """
    CROP_RULES = _load_crop_rules()
    
    crop_ruleset = CROP_RULES.get(crop_name.lower())
    if not crop_ruleset:
        raise ValueError(f"No knowledge base found for crop '{crop_name}'.")
    
    df_with_recs = weather_df.copy()
    
    df_with_recs["recommendations"] = df_with_recs.apply(
        lambda row: _generate_recommendation_for_row(row, crop_ruleset), 
        axis=1
    )
    
    return df_with_recs
