from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import io
import json
from datetime import datetime
import logging

from models.demand_forecasting import DemandForecaster
from models.allocation_optimizer import AllocationOptimizer
from models.vehicle_routing import VehicleRouter
from utils.data_processor import DataProcessor
from utils.scenario_simulator import ScenarioSimulator


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def clean_json(obj):
    """Recursively convert numpy types to native Python types so JSONResponse can handle them."""
    import numpy as np

    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [clean_json(v) for v in obj]

    # numpy scalar types
    if isinstance(obj, (np.integer,)):
        return int(obj)

    if isinstance(obj, (np.floating,)):
        return float(obj)

    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    # numpy arrays
    if isinstance(obj, np.ndarray):
        return [clean_json(v) for v in obj.tolist()]

    return obj


app = FastAPI(title="Supply Chain Optimization API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data storage (in production, use Redis or database)
app_data = {
    "raw_data": {},
    "processed_data": {},
    "models": {},
    "results": {}
}

@app.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload and process all Excel files"""
    try:
        logger.info(f"Received {len(files)} files for upload")
        
        # Expected file names
        expected_files = {
            'GeoLocations.xlsx': 'geo_locations',
            'CapacityClustered.xlsx': 'capacity',
            'DemandCluster.xlsx': 'demand',
            'DistanceCluster.xlsx': 'distance',
            'Time.xlsx': 'time',
            'CostCluster.xlsx': 'cost',
            'CostsMWC-Clustered.xlsx': 'costs_mwc'
        }
        
        raw_data = {}
        
        # Process each uploaded file
        for file in files:
            if file.filename in expected_files:
                content = await file.read()
                
                # Read Excel file with all sheets
                excel_data = pd.read_excel(io.BytesIO(content), sheet_name=None)
                raw_data[expected_files[file.filename]] = excel_data
                logger.info(f"Processed {file.filename} with {len(excel_data)} sheets")
        
        # Validate required files
        missing_files = set(expected_files.values()) - set(raw_data.keys())
        if missing_files:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required files: {missing_files}"
            )
        
        # Store raw data
        app_data["raw_data"] = raw_data
        
        # Process data
        processor = DataProcessor()
        processed_data = processor.process_all_data(raw_data)
        app_data["processed_data"] = processed_data
        
        # Initialize and train models
        await initialize_models(processed_data)
        
        # Generate initial results
        results = await generate_optimization_results(processed_data)
        app_data["results"] = results
        
        return JSONResponse(clean_json({
            "status": "success",
            "message": "Files uploaded and processed successfully",
            "data_summary": {
                "locations": len(processed_data.get("locations", [])),
                "warehouses": len(processed_data.get("warehouses", [])),
                "stores": len(processed_data.get("stores", [])),
                "time_periods": len(processed_data.get("demand_data", [])),
            },
            "results": results
        }))
        
    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def initialize_models(processed_data: Dict[str, Any]):
    """Initialize and train ML models"""
    try:
        # Demand Forecasting Model
        demand_forecaster = DemandForecaster()
        demand_forecaster.train(processed_data["demand_data"])
        
        # Allocation Optimizer
        allocation_optimizer = AllocationOptimizer()
        
        # Vehicle Router
        vehicle_router = VehicleRouter()
        
        app_data["models"] = {
            "demand_forecaster": demand_forecaster,
            "allocation_optimizer": allocation_optimizer,
            "vehicle_router": vehicle_router
        }
        
        logger.info("Models initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing models: {str(e)}")
        raise

async def generate_optimization_results(processed_data: Dict[str, Any]):
    """Generate optimization results"""
    try:
        models = app_data["models"]
        
        # 1. Demand Forecasting
        demand_forecast = models["demand_forecaster"].forecast(
            processed_data["demand_data"]
        )
        
        # 2. Allocation Optimization
        allocation_result = models["allocation_optimizer"].optimize(
            warehouses=processed_data["warehouses"],
            stores=processed_data["stores"],
            demand_forecast=demand_forecast,
            capacity_data=processed_data["capacity_data"],
            cost_data=processed_data["cost_data"]
        )
        
        # 3. Vehicle Routing
        routing_result = models["vehicle_router"].optimize_routes(
            allocation_result=allocation_result,
            locations=processed_data["locations"],
            distance_matrix=processed_data["distance_matrix"],
            time_matrix=processed_data["time_matrix"]
        )
        
        # 4. Calculate metrics and violations
        metrics = calculate_performance_metrics(
            demand_forecast, allocation_result, routing_result, processed_data
        )
        
        return {
            "demand_forecast": demand_forecast,
            "allocation": allocation_result,
            "routing": routing_result,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating results: {str(e)}")
        raise

def calculate_performance_metrics(demand_forecast, allocation_result, routing_result, processed_data):
    """Calculate performance metrics and constraint violations"""
    try:
        metrics = {
            "total_cost": 0,
            "capacity_utilization": 0,
            "demand_fulfillment": 0,
            "constraint_violations": [],
            "cost_breakdown": {
                "transportation": 0,
                "warehousing": 0,
                "handling": 0
            }
        }
        
        # Calculate total costs from routing and allocation
        if routing_result and "total_cost" in routing_result:
            metrics["total_cost"] = routing_result["total_cost"]
            metrics["cost_breakdown"]["transportation"] = routing_result["total_cost"]
        
        # Calculate capacity utilization
        if allocation_result and "capacity_utilization" in allocation_result:
            metrics["capacity_utilization"] = allocation_result["capacity_utilization"]
        
        # Calculate demand fulfillment rate
        if demand_forecast and allocation_result:
            total_demand_dict = demand_forecast.get("total_demand", {})
            fulfilled_demand_dict = allocation_result.get("fulfilled_demand", {})

            fulfilled_demand_value = float(sum(fulfilled_demand_dict.values())) if fulfilled_demand_dict else 0.0
            total_demand_value = 0.0

            # If total_demand is a dict like {"overall": avg_demand_per_store}
            if isinstance(total_demand_dict, dict):
                if "overall" in total_demand_dict and fulfilled_demand_dict:
                    # Interpret "overall" as average demand per store
                    avg_per_store = float(total_demand_dict["overall"])
                    n_stores = len(fulfilled_demand_dict)
                    total_demand_value = avg_per_store * n_stores
                else:
                    # Otherwise sum all values in the dict
                    total_demand_value = float(sum(total_demand_dict.values())) if total_demand_dict else 0.0
            else:
                # If total_demand is just a scalar
                try:
                    total_demand_value = float(total_demand_dict)
                except Exception:
                    total_demand_value = 0.0

            if total_demand_value > 0:
                fulfillment = (fulfilled_demand_value / total_demand_value) * 100.0
                # Clamp to [0, 100] to avoid nonsense percentages
                fulfillment = max(0.0, min(100.0, fulfillment))
                metrics["demand_fulfillment"] = fulfillment
        
        # Check for constraint violations
        violations = []
        
        # Capacity violations
        if allocation_result and "capacity_violations" in allocation_result:
            violations.extend(allocation_result["capacity_violations"])
        
        # Demand violations
        if allocation_result and "demand_violations" in allocation_result:
            violations.extend(allocation_result["demand_violations"])
        
        metrics["constraint_violations"] = violations
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating metrics: {str(e)}")
        return {"error": str(e)}


@app.post("/run-scenario")
async def run_scenario(scenario_data: Dict[str, Any]):
    """Run what-if scenario simulation"""
    try:
        if not app_data.get("processed_data") or not app_data.get("models"):
            raise HTTPException(
                status_code=400, 
                detail="No data loaded. Please upload files first."
            )
        
        simulator = ScenarioSimulator(
            processed_data=app_data["processed_data"],
            models=app_data["models"]
        )
        
        scenario_results = simulator.run_scenario(scenario_data)
        
        return JSONResponse(clean_json({
            "status": "success",
            "scenario_results": scenario_results,
            "timestamp": datetime.now().isoformat()
        }))

        
    except Exception as e:
        logger.error(f"Error running scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results")
async def get_results():
    """Get current optimization results"""
    try:
        if not app_data.get("results"):
            raise HTTPException(
                status_code=404, 
                detail="No results available. Please upload files first."
            )
        
        return JSONResponse(clean_json({
            "status": "success",
            "results": app_data["results"]
        }))
        
    except Exception as e:
        logger.error(f"Error getting results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data-summary")
async def get_data_summary():
    """Get summary of loaded data"""
    try:
        if not app_data.get("processed_data"):
            return JSONResponse({
                "status": "no_data",
                "message": "No data loaded"
            })
        
        processed_data = app_data["processed_data"]
        
        summary = {
            "locations_count": len(processed_data.get("locations", [])),
            "warehouses_count": len(processed_data.get("warehouses", [])),
            "stores_count": len(processed_data.get("stores", [])),
            "time_periods": len(processed_data.get("demand_data", [])),
            "has_results": bool(app_data.get("results"))
        }
        
        return JSONResponse(clean_json({
            "status": "success",
            "summary": summary
        }))

        
    except Exception as e:
        logger.error(f"Error getting data summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
