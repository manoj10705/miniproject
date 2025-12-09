export interface SupplyChainData {
  locations_count: number;
  warehouses_count: number;
  stores_count: number;
  time_periods?: number;
  capacity_records?: number;
  demand_records?: number;
}

export interface OptimizationResults {
  demand_forecast: any;
  allocation: any;
  routing: any;
  metrics: any;
}

export interface ScenarioResult {
  scenarioName: string;
  // For now keep this generic – we’ll just read what we need in Dashboard.
  results: any;
  timestamp: number;
}
