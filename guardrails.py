import logging

logger = logging.getLogger(__name__)

VALID_TYPES = {
    "solar_reduction", "minimum_battery_reserve", 
    "no_charge_window", "no_discharge_window", 
    "max_grid_window", "no_op"
}

def validate_directives(raw_directives: list[dict], notes: list[str]) -> list[dict]:
    validated = []
    
    # Ensure we process exactly the number of notes we have
    for i in range(len(notes)):
        # Find matching directive by note_index, or fallback
        d = next((item for item in raw_directives if item.get("note_index") == i), None)
        
        if d is None:
            validated.append(_make_noop(i, "Missing directive from LLM output."))
            continue
            
        try:
            d_type = d.get("directive_type")
            applies = d.get("applies")
            adj = d.get("structured_adjustment")
            
            if d_type not in VALID_TYPES:
                raise ValueError(f"Invalid directive type: {d_type}")
                
            if d_type == "no_op":
                validated.append(_make_noop(i, d.get("explanation", "Marked as no_op.")))
                continue
                
            if not applies:
                raise ValueError("applies is false but type is not no_op.")
                
            # Validate hours
            if "hours" not in adj or not isinstance(adj["hours"], list):
                raise ValueError("Missing or invalid 'hours' list.")
                
            hours = adj["hours"]
            if not all(isinstance(h, int) and 0 <= h <= 23 for h in hours):
                raise ValueError("Hours must be integers between 0 and 23.")
            if hours != sorted(list(set(hours))):
                raise ValueError("Hours must be unique and sorted ascending.")
                
            # Validate specific types
            if d_type == "solar_reduction" and not (0 <= adj.get("factor", -1) <= 1):
                raise ValueError("solar_reduction requires 'factor' between 0 and 1.")
            if d_type == "minimum_battery_reserve" and "minimum_energy_kwh" not in adj:
                raise ValueError("minimum_battery_reserve requires 'minimum_energy_kwh'.")
            if d_type == "max_grid_window" and "max_grid_kwh" not in adj:
                raise ValueError("max_grid_window requires 'max_grid_kwh'.")
                
            # Passed guardrails
            validated.append(d)
            
        except Exception as e:
            logger.warning(f"Guardrail check failed for note {i}: {e}. Overriding to no_op.")
            validated.append(_make_noop(i, f"Guardrail violation: {str(e)}"))
            
    return validated

def _make_noop(index: int, msg: str) -> dict:
    return {
        "note_index": index,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": msg
    }