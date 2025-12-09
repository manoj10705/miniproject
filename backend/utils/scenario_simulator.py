import copy
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ScenarioSimulator:
    """Simulate what-if scenarios for supply chain optimization"""
    
    def __init__(self, processed_data: Dict[str, Any], models: Dict[str, Any]):
        self.base_data = copy.deepcopy(processed_data)
        self.models = models
        
    def run_scenario(self, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a what-if scenario simulation"""
        try:
            logger.info(f"Running scenario: {scenario_config.get('name', 'Unnamed')}")
            
            # Create modified data based on scenario
            modified_data = self._apply_scenario_changes(scenario_config)
            
            # Re-run optimization with modified data
            scenario_results = self._run_optimization(modified_data)
            
            # Compare with baseline
            comparison = self._compare_with_baseline(scenario_results)
            
            return {
                'scenario_name': scenario_config.get('name', 'Unnamed Scenario'),
                'scenario_config': scenario_config,
                'results': scenario_results,
                'comparison': comparison,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error running scenario: {str(e)}")
            return {
                'scenario_name': scenario_config.get('name', 'Failed Scenario'),
                'error': str(e),
                'status': 'error'
            }
    
    def _apply_scenario_changes(self, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply scenario changes to base data"""
        modified_data = copy.deepcopy(self.base_data)
        
        # Apply demand surge
        if 'demand_surge' in scenario_config:
            surge_config = scenario_config['demand_surge']
            modified_data = self._apply_demand_surge(modified_data, surge_config)
        
        # Apply node removal
        if 'remove_nodes' in scenario_config:
            remove_config = scenario_config['remove_nodes']
            modified_data = self._apply_node_removal(modified_data, remove_config)
        
        # Apply route blockages
        if 'route_blockages' in scenario_config:
            blockage_config = scenario_config['route_blockages']
            modified_data = self._apply_route_blockages(modified_data, blockage_config)
        
        # Apply capacity changes
        if 'capacity_changes' in scenario_config:
            capacity_config = scenario_config['capacity_changes']
            modified_data = self._apply_capacity_changes(modified_data, capacity_config)
        
        return modified_data
    
    def _apply_demand_surge(self, data: Dict[str, Any], surge_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply demand surge to specific locations or overall"""
        try:
            surge_factor = surge_config.get('factor', 1.5)  # Default 50% increase
            affected_locations = surge_config.get('locations', [])  # Empty means all locations
            
            # Modify demand data
            demand_data = data.get('demand_data', [])
            
            for record in demand_data:
                # Check if this record should be affected
                should_apply = True
                if affected_locations:
                    location_id = str(record.get('id', record.get('location_id', record.get('store_id', ''))))
                    should_apply = location_id in affected_locations
                
                if should_apply:
                    # Apply surge to numeric demand columns
                    for key, value in record.items():
                        if 'demand' in key.lower() and isinstance(value, (int, float)):
                            record[key] = value * surge_factor
            
            logger.info(f"Applied demand surge factor {surge_factor} to {len(affected_locations) if affected_locations else 'all'} locations")
            return data
            
        except Exception as e:
            logger.error(f"Error applying demand surge: {str(e)}")
            return data
    
    def _apply_node_removal(self, data: Dict[str, Any], remove_config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove specified nodes from the network"""
        try:
            nodes_to_remove = remove_config.get('node_ids', [])
            node_type = remove_config.get('type', 'any')  # 'warehouse', 'store', or 'any'
            
            if not nodes_to_remove:
                return data
            
            # Remove from locations
            original_locations = data.get('locations', [])
            filtered_locations = []
            
            for location in original_locations:
                location_id = str(location.get('id', ''))
                location_type = location.get('type', 'location')
                
                should_remove = (
                    location_id in nodes_to_remove and 
                    (node_type == 'any' or location_type == node_type)
                )
                
                if not should_remove:
                    filtered_locations.append(location)
            
            data['locations'] = filtered_locations
            
            # Update warehouses and stores
            warehouses, stores = self._separate_warehouses_stores(filtered_locations)
            data['warehouses'] = warehouses
            data['stores'] = stores
            
            # Update matrices (remove corresponding rows/columns)
            removed_indices = []
            for i, location in enumerate(original_locations):
                location_id = str(location.get('id', ''))
                if location_id in nodes_to_remove:
                    removed_indices.append(i)
            
            if removed_indices:
                data['distance_matrix'] = self._remove_matrix_indices(
                    data.get('distance_matrix', []), removed_indices
                )
                data['time_matrix'] = self._remove_matrix_indices(
                    data.get('time_matrix', []), removed_indices
                )
            
            logger.info(f"Removed {len(nodes_to_remove)} nodes of type {node_type}")
            return data
            
        except Exception as e:
            logger.error(f"Error removing nodes: {str(e)}")
            return data
    
    def _apply_route_blockages(self, data: Dict[str, Any], blockage_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply route blockages by increasing travel times/distances"""
        try:
            blocked_routes = blockage_config.get('routes', [])  # List of (from_id, to_id) tuples
            blockage_factor = blockage_config.get('factor', float('inf'))  # Default: complete blockage
            
            if not blocked_routes:
                return data
            
            locations = data.get('locations', [])
            location_id_to_index = {str(loc.get('id', '')): i for i, loc in enumerate(locations)}
            
            distance_matrix = data.get('distance_matrix', [])
            time_matrix = data.get('time_matrix', [])
            
            for from_id, to_id in blocked_routes:
                from_idx = location_id_to_index.get(str(from_id))
                to_idx = location_id_to_index.get(str(to_id))
                
                if from_idx is not None and to_idx is not None:
                    # Apply blockage to distance matrix
                    if (from_idx < len(distance_matrix) and 
                        to_idx < len(distance_matrix[from_idx])):
                        if blockage_factor == float('inf'):
                            distance_matrix[from_idx][to_idx] = 999999  # Very large number
                            distance_matrix[to_idx][from_idx] = 999999  # Bidirectional
                        else:
                            distance_matrix[from_idx][to_idx] *= blockage_factor
                            distance_matrix[to_idx][from_idx] *= blockage_factor
                    
                    # Apply blockage to time matrix
                    if (from_idx < len(time_matrix) and 
                        to_idx < len(time_matrix[from_idx])):
                        if blockage_factor == float('inf'):
                            time_matrix[from_idx][to_idx] = 999999  # Very large number
                            time_matrix[to_idx][from_idx] = 999999  # Bidirectional
                        else:
                            time_matrix[from_idx][to_idx] *= blockage_factor
                            time_matrix[to_idx][from_idx] *= blockage_factor
            
            logger.info(f"Applied blockages to {len(blocked_routes)} routes")
            return data
            
        except Exception as e:
            logger.error(f"Error applying route blockages: {str(e)}")
            return data
    
    def _apply_capacity_changes(self, data: Dict[str, Any], capacity_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply capacity changes to warehouses"""
        try:
            capacity_changes = capacity_config.get('changes', {})  # {warehouse_id: new_capacity}
            
            # Update capacity data
            capacity_data = data.get('capacity_data', [])
            
            for record in capacity_data:
                warehouse_id = str(record.get('id', record.get('warehouse_id', '')))
                if warehouse_id in capacity_changes:
                    new_capacity = capacity_changes[warehouse_id]
                    
                    # Update capacity columns
                    for key in record.keys():
                        if 'capacity' in key.lower():
                            record[key] = new_capacity
            
            # Also update warehouse records
            warehouses = data.get('warehouses', [])
            for warehouse in warehouses:
                warehouse_id = str(warehouse.get('id', ''))
                if warehouse_id in capacity_changes:
                    new_capacity = capacity_changes[warehouse_id]
                    
                    # Update capacity columns
                    for key in warehouse.keys():
                        if 'capacity' in key.lower():
                            warehouse[key] = new_capacity
            
            logger.info(f"Applied capacity changes to {len(capacity_changes)} warehouses")
            return data
            
        except Exception as e:
            logger.error(f"Error applying capacity changes: {str(e)}")
            return data
    
    def _run_optimization(self, modified_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run optimization with modified data"""
        try:
            # Re-run demand forecasting
            demand_forecast = self.models['demand_forecaster'].forecast(
                modified_data['demand_data']
            )
            
            # Re-run allocation optimization
            allocation_result = self.models['allocation_optimizer'].optimize(
                warehouses=modified_data['warehouses'],
                stores=modified_data['stores'],
                demand_forecast=demand_forecast,
                capacity_data=modified_data['capacity_data'],
                cost_data=modified_data['cost_data']
            )
            
            # Re-run vehicle routing
            routing_result = self.models['vehicle_router'].optimize_routes(
                allocation_result=allocation_result,
                locations=modified_data['locations'],
                distance_matrix=modified_data['distance_matrix'],
                time_matrix=modified_data['time_matrix']
            )
            
            return {
                'demand_forecast': demand_forecast,
                'allocation': allocation_result,
                'routing': routing_result
            }
            
        except Exception as e:
            logger.error(f"Error running optimization: {str(e)}")
            return {'error': str(e)}
    
    def _compare_with_baseline(self, scenario_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare scenario results with baseline"""
        try:
            # This would compare with stored baseline results
            # For now, return basic comparison structure
            
            comparison = {
                'cost_change': 0,
                'capacity_utilization_change': 0,
                'demand_fulfillment_change': 0,
                'route_efficiency_change': 0,
                'constraint_violations_change': 0
            }
            
            # Extract key metrics from scenario results
            if 'routing' in scenario_results and 'total_cost' in scenario_results['routing']:
                scenario_cost = scenario_results['routing']['total_cost']
                # comparison['cost_change'] = scenario_cost - baseline_cost (if we had baseline)
            
            if 'allocation' in scenario_results and 'capacity_utilization' in scenario_results['allocation']:
                scenario_utilization = scenario_results['allocation']['capacity_utilization']
                # comparison['capacity_utilization_change'] = scenario_utilization - baseline_utilization
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing with baseline: {str(e)}")
            return {'error': str(e)}
    
    def _separate_warehouses_stores(self, locations: List[Dict[str, Any]]) -> tuple:
        """Separate locations into warehouses and stores"""
        warehouses = [loc for loc in locations if loc.get('type') == 'warehouse']
        stores = [loc for loc in locations if loc.get('type') == 'store']
        return warehouses, stores
    
    def _remove_matrix_indices(self, matrix: List[List[float]], indices_to_remove: List[int]) -> List[List[float]]:
        """Remove specified indices from a matrix"""
        if not matrix or not indices_to_remove:
            return matrix
        
        # Sort indices in descending order to remove from end first
        sorted_indices = sorted(indices_to_remove, reverse=True)
        
        # Remove rows
        for idx in sorted_indices:
            if 0 <= idx < len(matrix):
                matrix.pop(idx)
        
        # Remove columns
        for row in matrix:
            for idx in sorted_indices:
                if 0 <= idx < len(row):
                    row.pop(idx)
        
        return matrix
