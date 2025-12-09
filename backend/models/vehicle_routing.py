from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging
from haversine import haversine, Unit

logger = logging.getLogger(__name__)

class VehicleRouter:
    """Vehicle routing optimization using Google OR-Tools"""
    
    def __init__(self):
        self.distance_matrix = None
        self.time_matrix = None
        self.locations = []
        
    def optimize_routes(self, 
                       allocation_result: Dict[str, Any],
                       locations: List[Dict[str, Any]],
                       distance_matrix: List[List[float]] = None,
                       time_matrix: List[List[float]] = None) -> Dict[str, Any]:
        """Optimize vehicle routes using OR-Tools"""
        try:
            logger.info("Starting vehicle routing optimization")
            
            # Prepare location data
            location_df = pd.DataFrame(locations)
            self.locations = self._prepare_locations(location_df)
            
            if len(self.locations) < 2:
                logger.warning("Not enough locations for routing optimization")
                return self._create_simple_routing_result(allocation_result)
            
            # Prepare distance and time matrices
            self.distance_matrix = self._prepare_distance_matrix(distance_matrix, self.locations)
            self.time_matrix = self._prepare_time_matrix(time_matrix, self.locations)
            
            # Extract delivery requirements from allocation
            delivery_demands = self._extract_delivery_demands(allocation_result)
            
            # Create routing model
            routing_result = self._solve_vrp(delivery_demands)
            
            logger.info("Vehicle routing optimization completed")
            return routing_result
            
        except Exception as e:
            logger.error(f"Error in vehicle routing optimization: {str(e)}")
            return self._create_error_result(str(e))
    
    def _prepare_locations(self, location_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare location data for routing"""
        locations = []
        
        # Find coordinate columns
        lat_cols = [col for col in location_df.columns if 'lat' in col.lower()]
        lon_cols = [col for col in location_df.columns if 'lon' in col.lower() or 'lng' in col.lower()]
        id_cols = [col for col in location_df.columns if 'id' in col.lower()]
        
        if not lat_cols or not lon_cols:
            logger.warning("No coordinate columns found, using dummy coordinates")
            # Create dummy coordinates
            for i, row in location_df.iterrows():
                locations.append({
                    'id': str(row[id_cols[0]]) if id_cols else str(i),
                    'lat': 40.7128 + (i * 0.01),  # Dummy coordinates around NYC
                    'lon': -74.0060 + (i * 0.01),
                    'type': 'location'
                })
        else:
            lat_col, lon_col = lat_cols[0], lon_cols[0]
            id_col = id_cols[0] if id_cols else None
            
            for i, row in location_df.iterrows():
                lat = row[lat_col]
                lon = row[lon_col]
                
                if pd.notna(lat) and pd.notna(lon):
                    locations.append({
                        'id': str(row[id_col]) if id_col else str(i),
                        'lat': float(lat),
                        'lon': float(lon),
                        'type': self._determine_location_type(row)
                    })
        
        return locations
    
    def _determine_location_type(self, row: pd.Series) -> str:
        """Determine if location is warehouse or store"""
        row_str = str(row).lower()
        if 'warehouse' in row_str:
            return 'warehouse'
        elif 'store' in row_str:
            return 'store'
        else:
            return 'location'
    
    def _prepare_distance_matrix(self, distance_matrix: List[List[float]], locations: List[Dict[str, Any]]) -> List[List[float]]:
        """Prepare distance matrix for routing"""
        n_locations = len(locations)
        
        if distance_matrix and len(distance_matrix) == n_locations:
            # Use provided distance matrix
            return distance_matrix
        
        # Calculate distance matrix using Haversine formula
        matrix = []
        for i in range(n_locations):
            row = []
            for j in range(n_locations):
                if i == j:
                    row.append(0.0)
                else:
                    loc1 = (locations[i]['lat'], locations[i]['lon'])
                    loc2 = (locations[j]['lat'], locations[j]['lon'])
                    distance = haversine(loc1, loc2, unit=Unit.KILOMETERS)
                    row.append(distance)
            matrix.append(row)
        
        return matrix
    
    def _prepare_time_matrix(self, time_matrix: List[List[float]], locations: List[Dict[str, Any]]) -> List[List[float]]:
        """Prepare time matrix for routing"""
        n_locations = len(locations)
        
        if time_matrix and len(time_matrix) == n_locations:
            # Use provided time matrix
            return time_matrix
        
        # Estimate time matrix from distance (assuming 50 km/h average speed)
        matrix = []
        for i in range(n_locations):
            row = []
            for j in range(n_locations):
                if i == j:
                    row.append(0.0)
                else:
                    distance = self.distance_matrix[i][j]
                    time = (distance / 50.0) * 60  # Convert to minutes
                    row.append(time)
            matrix.append(row)
        
        return matrix
    
    def _extract_delivery_demands(self, allocation_result: Dict[str, Any]) -> Dict[str, float]:
        """Extract delivery demands from allocation result"""
        demands = {}
        
        if 'allocations' in allocation_result:
            allocations = allocation_result['allocations']
            
            # Sum up demands for each store
            for warehouse_id, warehouse_allocations in allocations.items():
                for store_id, amount in warehouse_allocations.items():
                    if store_id not in demands:
                        demands[store_id] = 0
                    demands[store_id] += amount
        
        return demands
    
    def _solve_vrp(self, delivery_demands: Dict[str, float]) -> Dict[str, Any]:
        """Solve Vehicle Routing Problem using OR-Tools"""
        try:
            n_locations = len(self.locations)
            n_vehicles = min(5, max(1, len(delivery_demands) // 3))  # Heuristic for number of vehicles
            
            # Create routing index manager
            manager = pywrapcp.RoutingIndexManager(n_locations, n_vehicles, 0)  # Depot at index 0
            
            # Create routing model
            routing = pywrapcp.RoutingModel(manager)
            
            # Create distance callback
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(self.distance_matrix[from_node][to_node] * 100)  # Scale for integer
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Add capacity constraint if we have demands
            if delivery_demands:
                # Create demand callback
                def demand_callback(from_index):
                    from_node = manager.IndexToNode(from_index)
                    if from_node < len(self.locations):
                        location_id = self.locations[from_node]['id']
                        return int(delivery_demands.get(location_id, 0))
                    return 0
                
                demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
                
                # Add capacity dimension
                vehicle_capacity = max(100, int(sum(delivery_demands.values()) / n_vehicles * 1.5))
                routing.AddDimensionWithVehicleCapacity(
                    demand_callback_index,
                    0,  # null capacity slack
                    [vehicle_capacity] * n_vehicles,  # vehicle maximum capacities
                    True,  # start cumul to zero
                    'Capacity'
                )
            
            # Add time constraint
            def time_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(self.time_matrix[from_node][to_node])
            
            time_callback_index = routing.RegisterTransitCallback(time_callback)
            
            # Add time dimension
            max_time = 480  # 8 hours in minutes
            routing.AddDimension(
                time_callback_index,
                30,  # allow waiting time
                max_time,  # maximum time per vehicle
                False,  # don't force start cumul to zero
                'Time'
            )
            
            time_dimension = routing.GetDimensionOrDie('Time')
            time_dimension.SetGlobalSpanCostCoefficient(100)
            
            # Setting first solution heuristic
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.FromSeconds(30)  # 30 second time limit
            
            # Solve the problem
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                return self._extract_vrp_solution(manager, routing, solution, delivery_demands)
            else:
                logger.warning("No solution found for VRP")
                return self._create_simple_routing_result({'allocations': {}})
                
        except Exception as e:
            logger.error(f"Error solving VRP: {str(e)}")
            return self._create_error_result(str(e))
    
    def _extract_vrp_solution(self, manager, routing, solution, delivery_demands: Dict[str, float]) -> Dict[str, Any]:
        """Extract solution from OR-Tools VRP solver"""
        try:
            routes = []
            total_distance = 0
            total_time = 0
            total_cost = 0
            
            for vehicle_id in range(routing.vehicles()):
                index = routing.Start(vehicle_id)
                route = {
                    'vehicle_id': vehicle_id,
                    'stops': [],
                    'distance': 0,
                    'time': 0,
                    'load': 0
                }
                
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    
                    if node_index < len(self.locations):
                        location = self.locations[node_index]
                        demand = delivery_demands.get(location['id'], 0)
                        
                        route['stops'].append({
                            'location_id': location['id'],
                            'lat': location['lat'],
                            'lon': location['lon'],
                            'demand': demand,
                            'arrival_time': solution.Value(routing.GetDimensionOrDie('Time').CumulVar(index))
                        })
                        
                        route['load'] += demand
                    
                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    
                    if previous_index != index:
                        from_node = manager.IndexToNode(previous_index)
                        to_node = manager.IndexToNode(index)
                        if from_node < len(self.distance_matrix) and to_node < len(self.distance_matrix[0]):
                            route['distance'] += self.distance_matrix[from_node][to_node]
                            route['time'] += self.time_matrix[from_node][to_node]
                
                # Add return to depot
                if route['stops']:
                    last_node = len(route['stops']) - 1
                    if last_node >= 0:
                        route['distance'] += self.distance_matrix[manager.IndexToNode(index)][0]
                        route['time'] += self.time_matrix[manager.IndexToNode(index)][0]
                
                if route['stops']:  # Only add routes with stops
                    routes.append(route)
                    total_distance += route['distance']
                    total_time += route['time']
                    total_cost += route['distance'] * 0.5  # Assume $0.5 per km
            
            return {
                'status': 'Optimal',
                'routes': routes,
                'total_distance': total_distance,
                'total_time': total_time,
                'total_cost': total_cost,
                'n_vehicles_used': len(routes),
                'summary': {
                    'total_stops': sum(len(route['stops']) for route in routes),
                    'avg_route_distance': total_distance / len(routes) if routes else 0,
                    'avg_route_time': total_time / len(routes) if routes else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting VRP solution: {str(e)}")
            return self._create_error_result(str(e))
    
    def _create_simple_routing_result(self, allocation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create simple routing result when VRP cannot be solved"""
        routes = []
        total_cost = 0
        
        if 'allocations' in allocation_result:
            vehicle_id = 0
            for warehouse_id, warehouse_allocations in allocation_result['allocations'].items():
                if warehouse_allocations:
                    route = {
                        'vehicle_id': vehicle_id,
                        'stops': [],
                        'distance': 0,
                        'time': 0,
                        'load': 0
                    }
                    
                    for store_id, amount in warehouse_allocations.items():
                        # Find location coordinates
                        location = next((loc for loc in self.locations if loc['id'] == store_id), None)
                        if location:
                            route['stops'].append({
                                'location_id': store_id,
                                'lat': location['lat'],
                                'lon': location['lon'],
                                'demand': amount,
                                'arrival_time': 0
                            })
                            route['load'] += amount
                    
                    if route['stops']:
                        # Estimate distance and time
                        route['distance'] = len(route['stops']) * 10  # 10 km per stop
                        route['time'] = len(route['stops']) * 30  # 30 minutes per stop
                        routes.append(route)
                        total_cost += route['distance'] * 0.5
                        vehicle_id += 1
        
        return {
            'status': 'Simplified',
            'reason': 'Fallback heuristic used instead of full VRP',
            'routes': routes,
            'total_distance': sum(route['distance'] for route in routes),
            'total_time': sum(route['time'] for route in routes),
            'total_cost': total_cost,
            'n_vehicles_used': len(routes),
            'summary': {
                'total_stops': sum(len(route['stops']) for route in routes),
                'avg_route_distance': sum(route['distance'] for route in routes) / len(routes) if routes else 0,
                'avg_route_time': sum(route['time'] for route in routes) / len(routes) if routes else 0
            }
        }

    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            'status': 'Error',
            'error': error_message,
            'routes': [],
            'total_distance': 0,
            'total_time': 0,
            'total_cost': 0,
            'n_vehicles_used': 0,
            'summary': {
                'total_stops': 0,
                'avg_route_distance': 0,
                'avg_route_time': 0
            }
        }
