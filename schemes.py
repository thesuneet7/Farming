#schemes.py
import json
from typing import List, Dict, Any, Optional

# Load schemes.json once
with open("schemes.json", "r", encoding="utf-8") as f:
    SCHEMES = json.load(f)


def get_personalised_schemes(
    age: int,
    gender: Optional[str] = None,
    land: Optional[float] = None,
    income: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Filters schemes.json based on farmer profile.
    Returns a list of eligible schemes.
    """
    eligible_schemes = []

    for scheme in SCHEMES:
        crit = scheme.get("criteria", {})
        is_eligible = True

        # --- Age check ---
        if "min_age" in crit and age < crit["min_age"]:
            is_eligible = False
        if "max_age" in crit and age > crit["max_age"]:
            is_eligible = False

        # --- Gender check ---
        if "gender" in crit:
            allowed = [g.lower() for g in crit["gender"]]
            if gender and gender.lower() not in allowed:
                is_eligible = False

        # --- Land check ---
        if "max_land" in crit and land is not None and land > crit["max_land"]:
            is_eligible = False
        if "min_land" in crit and land is not None and land < crit["min_land"]:
            is_eligible = False

        # --- Income check ---
        if "max_income" in crit and income is not None and income > crit["max_income"]:
            is_eligible = False
        if "min_income" in crit and income is not None and income < crit["min_income"]:
            is_eligible = False

        if is_eligible:
            eligible_schemes.append({
                "name": scheme["name"],
                "benefit": scheme.get("benefit", "Not specified"),
                "link": scheme.get("link", "")
            })

    return eligible_schemes

