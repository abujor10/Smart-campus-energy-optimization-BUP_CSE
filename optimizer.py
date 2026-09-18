import pulp
import logging

logger = logging.getLogger(__name__)

def optimize_schedule(hours_data, battery_params, directives):
    # Setup problem
    prob = pulp.LpProblem("EnergyCostMinimization", pulp.LpMinimize)
    
    # Defaults and Variables
    hours_range = range(24)
    grid = pulp.LpVariable.dicts("Grid", hours_range, lowBound=0)
    solar = pulp.LpVariable.dicts("SolarUsed", hours_range, lowBound=0)
    charge = pulp.LpVariable.dicts("Charge", hours_range, lowBound=0, upBound=battery_params.max_charge_kwh_per_hour)
    discharge = pulp.LpVariable.dicts("Discharge", hours_range, lowBound=0, upBound=battery_params.max_discharge_kwh_per_hour)
    energy = pulp.LpVariable.dicts("Energy", hours_range, lowBound=0, upBound=battery_params.capacity_kwh)
    
    # Applying base rules & direct directive overrides
    effective_solar_limit = [h.solar_kwh for h in hours_data]
    min_energy_limit = [battery_params.minimum_energy_kwh] * 24
    max_grid_limit = [None] * 24
    max_charge_limit = [battery_params.max_charge_kwh_per_hour] * 24
    max_discharge_limit = [battery_params.max_discharge_kwh_per_hour] * 24
    
    # Process Directives
    for d in directives:
        if not d["applies"] or d["directive_type"] == "no_op":
            continue
        
        adj = d["structured_adjustment"]
        target_hours = adj["hours"]
        dtype = d["directive_type"]
        
        for h in target_hours:
            if dtype == "solar_reduction":
                effective_solar_limit[h] *= adj["factor"]
            elif dtype == "minimum_battery_reserve":
                min_energy_limit[h] = max(min_energy_limit[h], adj["minimum_energy_kwh"])
            elif dtype == "no_charge_window":
                max_charge_limit[h] = 0
            elif dtype == "no_discharge_window":
                max_discharge_limit[h] = 0
            elif dtype == "max_grid_window":
                max_grid_limit[h] = adj["max_grid_kwh"]

    # Objective: Minimize total cost
    prob += pulp.lpSum(grid[i] * hours_data[i].tariff_bdt_per_kwh for i in hours_range), "Total_Cost"

    # Constraints per hour
    for i in hours_range:
        # Variable specific bounds updated from directives
        solar[i].upBound = effective_solar_limit[i]
        charge[i].upBound = max_charge_limit[i]
        discharge[i].upBound = max_discharge_limit[i]
        energy[i].lowBound = min_energy_limit[i]
        
        if max_grid_limit[i] is not None:
            grid[i].upBound = max_grid_limit[i]
            
        # Energy Balance Equation: Grid + Solar + Discharge == Demand + Charge
        prob += grid[i] + solar[i] + discharge[i] == hours_data[i].demand_kwh + charge[i], f"EnergyBalance_{i}"
        
        # Battery State Transition
        if i == 0:
            prob += energy[i] == battery_params.initial_energy_kwh + charge[i] - discharge[i], f"BatteryTransition_{i}"
        else:
            prob += energy[i] == energy[i-1] + charge[i] - discharge[i], f"BatteryTransition_{i}"

    # End-of-day Neutrality
    prob += energy[23] == battery_params.initial_energy_kwh, "EndOfDayNeutrality"
    
    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if pulp.LpStatus[prob.status] != 'Optimal':
        raise ValueError(f"Solver could not find an optimal solution. Status: {pulp.LpStatus[prob.status]}")

    # Process Output
    hourly_plan = []
    total_grid = 0.0
    total_cost = 0.0
    peak_grid = 0.0
    
    for i in hours_range:
        c_val = pulp.value(charge[i])
        d_val = pulp.value(discharge[i])
        g_val = pulp.value(grid[i])
        s_val = pulp.value(solar[i])
        e_val = pulp.value(energy[i])
        
        # Handle small floating point issues (epsilon)
        if c_val < 1e-5: c_val = 0.0
        if d_val < 1e-5: d_val = 0.0
        
        net = c_val - d_val
        if net > 1e-5:
            action = "charge"
            b_kwh = net
        elif net < -1e-5:
            action = "discharge"
            b_kwh = abs(net)
        else:
            action = "idle"
            b_kwh = 0.0

        total_grid += g_val
        total_cost += g_val * hours_data[i].tariff_bdt_per_kwh
        if g_val > peak_grid:
            peak_grid = g_val
            
        hourly_plan.append({
            "hour": i,
            "grid_kwh": round(g_val, 3),
            "solar_used_kwh": round(s_val, 3),
            "battery_action": action,
            "battery_kwh": round(b_kwh, 3),
            "battery_energy_after_kwh": round(e_val, 3)
        })

    totals = {
        "total_grid_kwh": round(total_grid, 3),
        "total_cost_bdt": round(total_cost, 3),
        "peak_grid_kwh": round(peak_grid, 3)
    }
    
    return hourly_plan, totals