import pulp
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class AllocationOptimizer:
    """Warehouse-to-store allocation optimization using PuLP"""
    
    def __init__(self):
        self.problem = None
        self.variables = {}
        self.constraints = {}
        
    def optimize(self, 
                 warehouses: List[Dict[str, Any]], 
                 stores: List[Dict[str, Any]], 
                 demand_forecast: Dict[str, Any],
                 capacity_data: List[Dict[str, Any]],
                 cost_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize warehouse-to-store allocation using PuLP"""
        try:
            logger.info("Starting allocation optimization")
            
            # Prepare data
            warehouse_df = pd.DataFrame(warehouses)
            store_df = pd.DataFrame(stores)
            capacity_df = pd.DataFrame(capacity_data)
            cost_df = pd.DataFrame(cost_data)
            
            # Extract warehouse and store IDs
            warehouse_ids = self._extract_ids(warehouse_df, ['warehouse_id', 'id', 'location_id'])
            store_ids = self._extract_ids(store_df, ['store_id', 'id', 'location_id'])
            
            if not warehouse_ids or not store_ids:
                raise ValueError("Could not identify warehouse or store IDs")
            
            logger.info(f"Optimizing for {len(warehouse_ids)} warehouses and {len(store_ids)} stores")
            
            # Extract capacities
            warehouse_capacities = self._extract_capacities(warehouse_df, capacity_df, warehouse_ids)
            
            # Extract demands
            store_demands = self._extract_demands(store_df, demand_forecast, store_ids)
            
            # Extract costs
            transportation_costs = self._extract_costs(cost_df, warehouse_ids, store_ids)
            
            # Create optimization problem
            self.problem = pulp.LpProblem("Warehouse_Store_Allocation", pulp.LpMinimize)
            
            # Decision variables: x[i,j] = amount shipped from warehouse i to store j
            self.variables = {}
            for w_id in warehouse_ids:
                for s_id in store_ids:
                    var_name = f"x_{w_id}_{s_id}"
                    self.variables[(w_id, s_id)] = pulp.LpVariable(
                        var_name, 
                        lowBound=0, 
                        cat='Continuous'
                    )
            
            # Objective function: minimize total transportation cost
            total_cost = 0
            for w_id in warehouse_ids:
                for s_id in store_ids:
                    cost = transportation_costs.get((w_id, s_id), 1.0)  # Default cost if not found
                    total_cost += cost * self.variables[(w_id, s_id)]
            
            self.problem += total_cost, "Total_Transportation_Cost"
            
            # Constraints
            self.constraints = {}
            
            # 1. Demand satisfaction constraints
            for s_id in store_ids:
                demand = store_demands.get(s_id, 0)
                constraint = pulp.lpSum([
                    self.variables[(w_id, s_id)] for w_id in warehouse_ids
                ]) >= demand
                
                constraint_name = f"demand_satisfaction_{s_id}"
                self.problem += constraint, constraint_name
                self.constraints[constraint_name] = constraint
            
            # 2. Capacity constraints
            for w_id in warehouse_ids:
                capacity = warehouse_capacities.get(w_id, float('inf'))
                if capacity != float('inf'):
                    constraint = pulp.lpSum([
                        self.variables[(w_id, s_id)] for s_id in store_ids
                    ]) <= capacity
                    
                    constraint_name = f"capacity_{w_id}"
                    self.problem += constraint, constraint_name
                    self.constraints[constraint_name] = constraint
            
            # Solve the problem
            logger.info("Solving allocation optimization problem")
            solver = pulp.PULP_CBC_CMD(msg=0)  # Silent solver
            self.problem.solve(solver)
            
            # Check solution status
            status = pulp.LpStatus[self.problem.status]
            logger.info(f"Optimization status: {status}")
            
            if status != 'Optimal':
                logger.warning(f"Optimization did not find optimal solution: {status}")
            
            # Extract results
            allocation_result = self._extract_solution(
                warehouse_ids, store_ids, warehouse_capacities, store_demands
            )
            
            logger.info("Allocation optimization completed")
            return allocation_result
            
        except Exception as e:
            logger.error(f"Error in allocation optimization: {str(e)}")
            raise
    
    def _extract_ids(self, df: pd.DataFrame, possible_columns: List[str]) -> List[str]:
        """Extract IDs from dataframe"""
        for col in possible_columns:
            if col in df.columns:
                return df[col].astype(str).tolist()
        
        # If no ID column found, use index
        return df.index.astype(str).tolist()
    
    def _extract_capacities(self, warehouse_df: pd.DataFrame, capacity_df: pd.DataFrame, warehouse_ids: List[str]) -> Dict[str, float]:
        """Extract warehouse capacities"""
        capacities = {}
        
        # Try to find capacity in warehouse dataframe
        capacity_columns = [col for col in warehouse_df.columns if 'capacity' in col.lower()]
        if capacity_columns:
            for i, w_id in enumerate(warehouse_ids):
                if i < len(warehouse_df):
                    capacity = warehouse_df.iloc[i][capacity_columns[0]]
                    capacities[w_id] = float(capacity) if pd.notna(capacity) else 1000.0
        
        # Try to find capacity in separate capacity dataframe
        elif len(capacity_df) > 0:
            # Look for warehouse ID column in capacity data
            id_columns = [col for col in capacity_df.columns if 'id' in col.lower() or 'warehouse' in col.lower()]
            capacity_columns = [col for col in capacity_df.columns if 'capacity' in col.lower()]
            
            if id_columns and capacity_columns:
                id_col = id_columns[0]
                cap_col = capacity_columns[0]
                
                for _, row in capacity_df.iterrows():
                    w_id = str(row[id_col])
                    if w_id in warehouse_ids:
                        capacity = row[cap_col]
                        capacities[w_id] = float(capacity) if pd.notna(capacity) else 1000.0
        
        # Default capacities if not found
        for w_id in warehouse_ids:
            if w_id not in capacities:
                capacities[w_id] = 1000.0  # Default capacity
        
        return capacities
    
    def _extract_demands(self, store_df: pd.DataFrame, demand_forecast: Dict[str, Any], store_ids: List[str]) -> Dict[str, float]:
        """Extract store demands"""
        demands = {}
        
        # Try to get demands from forecast
        if 'total_demand' in demand_forecast:
            total_demand_dict = demand_forecast['total_demand']
            for s_id in store_ids:
                if s_id in total_demand_dict:
                    demands[s_id] = float(total_demand_dict[s_id])
        
        # Try to find demand in store dataframe
        demand_columns = [col for col in store_df.columns if 'demand' in col.lower()]
        if demand_columns and len(demands) == 0:
            for i, s_id in enumerate(store_ids):
                if i < len(store_df):
                    demand = store_df.iloc[i][demand_columns[0]]
                    demands[s_id] = float(demand) if pd.notna(demand) else 100.0
        
        # Use ensemble forecast if available
                # Use ensemble forecast if available (treat it as total network demand per period)
        if 'ensemble_forecast' in demand_forecast and len(demands) == 0:
            ensemble = demand_forecast['ensemble_forecast']
            if ensemble:
                # Predicted total demand per period (from the target "total_demand")
                total_network_demand = float(np.mean(ensemble))
                if len(store_ids) > 0:
                    per_store = total_network_demand / len(store_ids)
                else:
                    per_store = total_network_demand

                for s_id in store_ids:
                    demands[s_id] = per_store

        
        # Default demands if not found
        for s_id in store_ids:
            if s_id not in demands:
                demands[s_id] = 100.0  # Default demand
        
        return demands
    
    def _extract_costs(self, cost_df: pd.DataFrame, warehouse_ids: List[str], store_ids: List[str]) -> Dict[Tuple[str, str], float]:
        """Extract transportation costs"""
        costs = {}
        
        # Try to find cost matrix in cost dataframe
        if len(cost_df) > 0:
            # Check if it's a matrix format
            if len(cost_df.columns) > 2:
                # Assume first column is warehouse ID, other columns are store costs
                for i, row in cost_df.iterrows():
                    w_id = str(row.iloc[0])
                    if w_id in warehouse_ids:
                        for j, s_id in enumerate(store_ids):
                            if j + 1 < len(row):
                                cost = row.iloc[j + 1]
                                costs[(w_id, s_id)] = float(cost) if pd.notna(cost) else 1.0
            else:
                # Look for from/to/cost format
                from_cols = [col for col in cost_df.columns if 'from' in col.lower() or 'warehouse' in col.lower()]
                to_cols = [col for col in cost_df.columns if 'to' in col.lower() or 'store' in col.lower()]
                cost_cols = [col for col in cost_df.columns if 'cost' in col.lower()]
                
                if from_cols and to_cols and cost_cols:
                    from_col, to_col, cost_col = from_cols[0], to_cols[0], cost_cols[0]
                    
                    for _, row in cost_df.iterrows():
                        w_id = str(row[from_col])
                        s_id = str(row[to_col])
                        cost = row[cost_col]
                        
                        if w_id in warehouse_ids and s_id in store_ids:
                            costs[(w_id, s_id)] = float(cost) if pd.notna(cost) else 1.0
        
        # Default costs if not found
        for w_id in warehouse_ids:
            for s_id in store_ids:
                if (w_id, s_id) not in costs:
                    costs[(w_id, s_id)] = 1.0  # Default cost
        
        return costs
    
    def _extract_solution(self, warehouse_ids: List[str], store_ids: List[str], 
                         warehouse_capacities: Dict[str, float], store_demands: Dict[str, float]) -> Dict[str, Any]:
        """Extract solution from solved problem"""
        try:
            solution = {
                'status': pulp.LpStatus[self.problem.status],
                'objective_value': pulp.value(self.problem.objective),
                'allocations': {},
                'warehouse_utilization': {},
                'store_fulfillment': {},
                'capacity_utilization': 0,
                'fulfilled_demand': {},
                'capacity_violations': [],
                'demand_violations': []
            }
            
            # Extract allocation decisions
            total_allocated = 0
            warehouse_usage = {w_id: 0 for w_id in warehouse_ids}
            store_received = {s_id: 0 for s_id in store_ids}
            
            for w_id in warehouse_ids:
                solution['allocations'][w_id] = {}
                for s_id in store_ids:
                    if (w_id, s_id) in self.variables:
                        allocation = pulp.value(self.variables[(w_id, s_id)])
                        if allocation and allocation > 0.001:  # Avoid tiny numerical values
                            solution['allocations'][w_id][s_id] = allocation
                            warehouse_usage[w_id] += allocation
                            store_received[s_id] += allocation
                            total_allocated += allocation
            
            # Calculate warehouse utilization
            total_capacity = sum(warehouse_capacities.values())
            for w_id in warehouse_ids:
                capacity = warehouse_capacities.get(w_id, 0)
                usage = warehouse_usage.get(w_id, 0)
                
                if capacity > 0:
                    utilization = (usage / capacity) * 100
                    solution['warehouse_utilization'][w_id] = utilization
                    
                    # Check for capacity violations
                    if usage > capacity * 1.01:  # 1% tolerance
                        solution['capacity_violations'].append({
                            'warehouse_id': w_id,
                            'capacity': capacity,
                            'usage': usage,
                            'violation': usage - capacity
                        })
            
            # Calculate store fulfillment
            total_demand = sum(store_demands.values())
            total_fulfilled = 0
            
            for s_id in store_ids:
                demand = store_demands.get(s_id, 0)
                received = store_received.get(s_id, 0)
                
                if demand > 0:
                    fulfillment = (received / demand) * 100
                    solution['store_fulfillment'][s_id] = fulfillment
                    solution['fulfilled_demand'][s_id] = received
                    total_fulfilled += received
                    
                    # Check for demand violations (under-fulfillment)
                    if received < demand * 0.99:  # 1% tolerance
                        solution['demand_violations'].append({
                            'store_id': s_id,
                            'demand': demand,
                            'received': received,
                            'shortfall': demand - received
                        })
            
            # Overall capacity utilization
            if total_capacity > 0:
                solution['capacity_utilization'] = (total_allocated / total_capacity) * 100
            
            return solution
            
        except Exception as e:
            logger.error(f"Error extracting solution: {str(e)}")
            return {
                'status': 'Error',
                'error': str(e),
                'allocations': {},
                'warehouse_utilization': {},
                'store_fulfillment': {},
                'capacity_utilization': 0,
                'fulfilled_demand': {},
                'capacity_violations': [],
                'demand_violations': []
            }
