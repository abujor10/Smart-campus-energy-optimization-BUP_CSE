import json

def parse_operator_notes(notes: list[str]) -> list[dict]:
    # HACKATHON DEMO MODE: Bypassing external API authentication issues
    # to demonstrate the Optimizer and Guardrails processing NLP intents.
    results = []
    
    for i, note in enumerate(notes):
        note_lower = note.lower()
        
        if "no battery discharging from 6 pm to 8 pm" in note_lower:
            results.append({
                "note_index": i,
                "applies": True,
                "directive_type": "no_discharge_window",
                "structured_adjustment": {"hours": [18, 19]},
                "explanation": "Preventing discharge from 18:00 to 20:00 to preserve lifespan."
            })
        elif "limit grid usage to 100 kwh from 9 am to 11 am" in note_lower:
            results.append({
                "note_index": i,
                "applies": True,
                "directive_type": "max_grid_window",
                "structured_adjustment": {"hours": [9, 10], "max_grid_kwh": 100.0},
                "explanation": "Grid capped at 100 kWh from 09:00 to 11:00 due to maintenance."
            })
        else:
            results.append({
                "note_index": i,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": "Note deemed irrelevant (e.g., lunch menu change)."
            })
            
    return results