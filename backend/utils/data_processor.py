import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process and validate uploaded Excel data"""
    
    def __init__(self):
        self.processed_data = {}
        
    def process_all_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process all uploaded data files"""
        try:
            logger.info("Starting data processing")
            
            processed = {}
            
            # Process each data type
            processed['locations'] = self._process_geo_locations(raw_data.get('geo_locations', {}))
            processed['capacity_data'] = self._process_capacity_data(raw_data.get('capacity', {}))
            processed['demand_data'] = self._process_demand_data(raw_data.get('demand', {}))
            processed['distance_matrix'] = self._process_distance_data(raw_data.get('distance', {}))
            processed['time_matrix'] = self._process_time_data(raw_data.get('time', {}))
            processed['cost_data'] = self._process_cost_data(raw_data.get('cost', {}))
            processed['costs_mwc'] = self._process_costs_mwc_data(raw_data.get('costs_mwc', {}))
            
            # Derive warehouses and stores from locations
            warehouses, stores = self._separate_warehouses_stores(processed['locations'])
            processed['warehouses'] = warehouses
            processed['stores'] = stores
            
            # Validate data consistency
            self._validate_data_consistency(processed)
            
            logger.info("Data processing completed successfully")
            return processed
            
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            raise
    
    def _process_geo_locations(self, geo_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Process geographical locations data"""
        try:
            locations = []

            # Process all sheets in geo locations file
            for sheet_name, df in geo_data.items():
                logger.info(f"Processing geo locations sheet: {sheet_name}")

                # We know from the Excel: columns like "Geo ID", "Latitude", "Longitude"
                cols_lower = {str(c).lower(): c for c in df.columns}

                lat_cols = [cols_lower[k] for k in cols_lower.keys() if k.startswith("latitude") or k == "lat"]
                lon_cols = [cols_lower[k] for k in cols_lower.keys() if k.startswith("longitude") or k in ("lon", "lng")]
                id_cols  = [cols_lower[k] for k in cols_lower.keys() if "geo id" in k or (k.endswith("id") and "grid" not in k)]

                for i, row in df.iterrows():
                    location = {
                        "sheet": sheet_name,
                        "index": i,
                    }

                    # ID
                    if id_cols:
                        location["id"] = str(row[id_cols[0]])
                    else:
                        location["id"] = f"{sheet_name}_{i}"

                    # Coordinates: skip rows without valid numeric lat/lon
                    if lat_cols and lon_cols:
                        lat_val = row[lat_cols[0]]
                        lon_val = row[lon_cols[0]]
                        try:
                            if pd.notna(lat_val) and pd.notna(lon_val):
                                location["lat"] = float(lat_val)
                                location["lon"] = float(lon_val)
                            else:
                                continue
                        except (TypeError, ValueError):
                            # Something like "GC0" etc. – not a coordinate row
                            continue
                    else:
                        # No coordinate columns at all
                        continue

                    # Name (optional – fall back to ID)
                    location["name"] = str(location.get("id"))

                    # Type – infer from sheet name
                    location["type"] = self._infer_location_type(sheet_name, row)

                    # Add all other columns as attributes
                    for col in df.columns:
                        key = str(col).lower()
                        if col not in (lat_cols + lon_cols + id_cols):
                            location[key] = row[col]

                    locations.append(location)

            logger.info(f"Processed {len(locations)} locations")
            return locations

        except Exception as e:
            logger.error(f"Error processing geo locations: {str(e)}")
            # Return whatever we have instead of nuking everything
            return locations

    
    def _process_capacity_data(self, capacity_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Process capacity data"""
        try:
            capacity_records = []
            
            for sheet_name, df in capacity_data.items():
                logger.info(f"Processing capacity sheet: {sheet_name}")
                
                for i, row in df.iterrows():
                    record = {'sheet': sheet_name, 'index': i}
                    
                    # Add all columns as attributes
                    for col in df.columns:
                        key = str(col).lower()
                        record[key] = row[col]
                    
                    capacity_records.append(record)
            
            logger.info(f"Processed {len(capacity_records)} capacity records")
            return capacity_records
            
        except Exception as e:
            logger.error(f"Error processing capacity data: {str(e)}")
            return []
    
    def _process_demand_data(self, demand_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Process demand data"""
        try:
            demand_records = []
            
            for sheet_name, df in demand_data.items():
                logger.info(f"Processing demand sheet: {sheet_name}")
                
                for i, row in df.iterrows():
                    record = {'sheet': sheet_name, 'index': i}
                    
                    # Add all columns as attributes
                    for col in df.columns:
                        key = str(col).lower()
                        record[key] = row[col]
                    
                    demand_records.append(record)
            
            logger.info(f"Processed {len(demand_records)} demand records")
            print("DEBUG demand_df columns:", df.columns.tolist())
            print("DEBUG demand_df head:")
            print(df.head())

            return demand_records
            
        except Exception as e:
            logger.error(f"Error processing demand data: {str(e)}")
            return []
    
    def _process_distance_data(self, distance_data: Dict[str, pd.DataFrame]) -> List[List[float]]:
        """Process distance matrix data"""
        try:
            distance_matrix = []
            
            for sheet_name, df in distance_data.items():
                logger.info(f"Processing distance sheet: {sheet_name}")
                
                # Try to extract matrix from dataframe
                numeric_df = df.select_dtypes(include=[np.number])
                
                if len(numeric_df.columns) > 0:
                    matrix = numeric_df.values.tolist()
                    if matrix:
                        distance_matrix = matrix
                        break
            
            logger.info(f"Processed distance matrix: {len(distance_matrix)}x{len(distance_matrix[0]) if distance_matrix else 0}")
            return distance_matrix
            
        except Exception as e:
            logger.error(f"Error processing distance data: {str(e)}")
            return []
    
    def _process_time_data(self, time_data: Dict[str, pd.DataFrame]) -> List[List[float]]:
        """Process time matrix data"""
        try:
            time_matrix = []
            
            for sheet_name, df in time_data.items():
                logger.info(f"Processing time sheet: {sheet_name}")
                
                # Try to extract matrix from dataframe
                numeric_df = df.select_dtypes(include=[np.number])
                
                if len(numeric_df.columns) > 0:
                    matrix = numeric_df.values.tolist()
                    if matrix:
                        time_matrix = matrix
                        break
            
            logger.info(f"Processed time matrix: {len(time_matrix)}x{len(time_matrix[0]) if time_matrix else 0}")
            return time_matrix
            
        except Exception as e:
            logger.error(f"Error processing time data: {str(e)}")
            return []
    
    def _process_cost_data(self, cost_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Process cost data"""
        try:
            cost_records = []
            
            for sheet_name, df in cost_data.items():
                logger.info(f"Processing cost sheet: {sheet_name}")
                
                for i, row in df.iterrows():
                    record = {'sheet': sheet_name, 'index': i}
                    
                    # Add all columns as attributes
                    for col in df.columns:
                        key = str(col).lower()
                        record[key] = row[col]
                    
                    cost_records.append(record)
            
            logger.info(f"Processed {len(cost_records)} cost records")
            return cost_records
            
        except Exception as e:
            logger.error(f"Error processing cost data: {str(e)}")
            return []
    
    def _process_costs_mwc_data(self, costs_mwc_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Process MWC costs data"""
        try:
            mwc_records = []
            
            for sheet_name, df in costs_mwc_data.items():
                logger.info(f"Processing MWC costs sheet: {sheet_name}")
                
                for i, row in df.iterrows():
                    record = {'sheet': sheet_name, 'index': i}
                    
                    # Add all columns as attributes
                    for col in df.columns:
                        key = str(col).lower()
                        record[key] = row[col]
                    
                    mwc_records.append(record)
            
            logger.info(f"Processed {len(mwc_records)} MWC cost records")
            return mwc_records
            
        except Exception as e:
            logger.error(f"Error processing MWC costs data: {str(e)}")
            return []
    
    def _infer_location_type(self, sheet_name: str, row: pd.Series) -> str:
        """Infer location type from sheet name or row data"""
        sheet_lower = sheet_name.lower()
        row_str = str(row).lower()
        
        if 'warehouse' in sheet_lower or 'warehouse' in row_str:
            return 'warehouse'
        elif 'store' in sheet_lower or 'store' in row_str or 'retail' in row_str:
            return 'store'
        elif 'depot' in sheet_lower or 'depot' in row_str:
            return 'warehouse'
        elif 'customer' in sheet_lower or 'customer' in row_str:
            return 'store'
        else:
            return 'location'
    
    def _separate_warehouses_stores(self, locations: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Separate locations into warehouses and stores"""
        warehouses = []
        stores = []
        
        for location in locations:
            location_type = location.get('type', 'location')
            
            if location_type == 'warehouse':
                warehouses.append(location)
            elif location_type == 'store':
                stores.append(location)
            else:
                # If type is unclear, use heuristics
                location_str = str(location).lower()
                if 'warehouse' in location_str or 'depot' in location_str:
                    location['type'] = 'warehouse'
                    warehouses.append(location)
                else:
                    location['type'] = 'store'
                    stores.append(location)
        
        # If we don't have clear separation, split roughly 20/80
        if not warehouses and stores:
            n_warehouses = max(1, len(locations) // 5)
            warehouses = locations[:n_warehouses]
            stores = locations[n_warehouses:]
            
            for w in warehouses:
                w['type'] = 'warehouse'
            for s in stores:
                s['type'] = 'store'
        
        logger.info(f"Separated into {len(warehouses)} warehouses and {len(stores)} stores")
        return warehouses, stores
    
    def _validate_data_consistency(self, processed_data: Dict[str, Any]) -> None:
        """Validate consistency across processed data"""
        try:
            logger.info("Validating data consistency")
            
            # Check if we have minimum required data
            if not processed_data.get('locations'):
                logger.warning("No location data found")
            
            if not processed_data.get('warehouses'):
                logger.warning("No warehouse data found")
            
            if not processed_data.get('stores'):
                logger.warning("No store data found")
            
            # Check matrix dimensions
            distance_matrix = processed_data.get('distance_matrix', [])
            time_matrix = processed_data.get('time_matrix', [])
            n_locations = len(processed_data.get('locations', []))
            
            if distance_matrix and len(distance_matrix) != n_locations:
                logger.warning(f"Distance matrix size ({len(distance_matrix)}) doesn't match number of locations ({n_locations})")
            
            if time_matrix and len(time_matrix) != n_locations:
                logger.warning(f"Time matrix size ({len(time_matrix)}) doesn't match number of locations ({n_locations})")
            
            logger.info("Data validation completed")
            
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
