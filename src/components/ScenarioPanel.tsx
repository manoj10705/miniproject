import React, { useState } from 'react';
import { Play, Settings, TrendingUp, Package, Truck, MapPin, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { SupplyChainData, ScenarioResult } from '../types';

interface ScenarioPanelProps {
  data: SupplyChainData;
  onScenarioRun: (result: ScenarioResult) => void;
  loading: boolean;
  setLoading: (loading: boolean) => void;
}

export default function ScenarioPanel({ data, onScenarioRun, loading, setLoading }: ScenarioPanelProps) {
  const [scenarioName, setScenarioName] = useState('');
  const [demandChange, setDemandChange] = useState(0);
  const [capacityChange, setCapacityChange] = useState(0);
  const [costChange, setCostChange] = useState(0);
  const [routeBlockage, setRouteBlockage] = useState(false);
  

  const handleRunScenario = async () => {
  if (!scenarioName.trim()) {
    toast.error('Please enter a scenario name');
    return;
  }

  setLoading(true);

  try {
    // Map the sliders into a scenario configuration the backend can use.
    const body = {
      name: scenarioName.trim(),
      // Treat demand slider as an overall demand surge
      demand_surge: {
        factor: 1 + demandChange / 100,
        locations: []  // empty = all locations
      },
      // TODO: map capacityChange, costChange, routeBlockage if you extend backend
    };

    const res = await fetch("http://localhost:8000/run-scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Scenario request failed");
    }

    const json = await res.json();

    const scenarioResult: ScenarioResult = {
      scenarioName: scenarioName.trim(),
      results: json,       // store full backend response
      timestamp: Date.now()
    };

    onScenarioRun(scenarioResult);
    toast.success(`Scenario "${scenarioName}" completed!`);

    // Reset form
    setScenarioName('');
    setDemandChange(0);
    setCapacityChange(0);
    setCostChange(0);
    setRouteBlockage(false);

  } catch (error) {
    console.error('Scenario error:', error);
    toast.error(error instanceof Error ? error.message : 'Failed to run scenario');
  } finally {
    setLoading(false);
  }
};


  const predefinedScenarios = [
    {
      name: 'Peak Season Surge',
      description: 'Black Friday demand spike (+40%)',
      demand: 40,
      capacity: 0,
      cost: 15,
      blockage: false,
    },
    {
      name: 'Capacity Expansion',
      description: 'New warehouse capacity (+50%)',
      demand: 0,
      capacity: 50,
      cost: 0,
      blockage: false,
    },
    {
      name: 'Fuel Crisis',
      description: 'Transportation cost surge (+30%)',
      demand: 0,
      capacity: 0,
      cost: 30,
      blockage: false,
    },
    {
      name: 'Route Disruption',
      description: 'Major highway closure',
      demand: 10,
      capacity: 0,
      cost: 20,
      blockage: true,
    },
    {
      name: 'Economic Downturn',
      description: 'Reduced demand (-25%)',
      demand: -25,
      capacity: 0,
      cost: -10,
      blockage: false,
    },
    {
      name: 'Supply Chain Crisis',
      description: 'Capacity constraints (-30%)',
      demand: 0,
      capacity: -30,
      cost: 25,
      blockage: true,
    },
  ];

  const loadPredefinedScenario = (scenario: typeof predefinedScenarios[0]) => {
    setScenarioName(scenario.name);
    setDemandChange(scenario.demand);
    setCapacityChange(scenario.capacity);
    setCostChange(scenario.cost);
    setRouteBlockage(scenario.blockage);
  };

  return (
    <div className="bg-white rounded-lg shadow-lg border-2 p-6" style={{ borderColor: '#2C3E50' }}>
      <div className="flex items-center mb-6">
        <Settings className="h-6 w-6 mr-3" style={{ color: '#E67E22' }} />
        <h2 className="text-xl font-bold" style={{ color: '#2C3E50' }}>
          What-If Scenario Simulator
        </h2>
      </div>

      <div className="space-y-6">
        {/* Scenario Name */}
        <div>
          <label className="block text-sm font-bold mb-2" style={{ color: '#2C3E50' }}>
            Scenario Name
          </label>
          <input
            type="text"
            value={scenarioName}
            onChange={(e) => setScenarioName(e.target.value)}
            placeholder="Enter scenario name..."
            className="w-full px-4 py-3 border-2 rounded-lg focus:outline-none focus:ring-2 transition-all"
            style={{ 
              borderColor: '#2C3E50'
            }}
          />
        </div>

        {/* Advanced Parameter Controls */}
        <div className="space-y-5">
          <h3 className="text-lg font-bold" style={{ color: '#2C3E50' }}>
            ML-Driven Parameter Adjustments
          </h3>
          
          {/* Demand Change */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center">
                <TrendingUp className="h-5 w-5 mr-2" style={{ color: '#16A085' }} />
                <label className="font-medium" style={{ color: '#2C3E50' }}>
                  Demand Forecast Adjustment
                </label>
              </div>
              <span className="font-bold text-lg" style={{ color: demandChange >= 0 ? '#27AE60' : '#C0392B' }}>
                {demandChange > 0 ? '+' : ''}{demandChange}%
              </span>
            </div>
            <input
              type="range"
              min="-50"
              max="100"
              value={demandChange}
              onChange={(e) => setDemandChange(Number(e.target.value))}
              className="w-full h-3 rounded-lg appearance-none cursor-pointer"
              style={{ backgroundColor: '#ECF0F1' }}
            />
            <div className="flex justify-between text-sm mt-2" style={{ color: '#2C3E50' }}>
              <span>-50% (Recession)</span>
              <span>+100% (Boom)</span>
            </div>
          </div>

          {/* Capacity Change */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center">
                <Package className="h-5 w-5 mr-2" style={{ color: '#E67E22' }} />
                <label className="font-medium" style={{ color: '#2C3E50' }}>
                  Warehouse Capacity Adjustment
                </label>
              </div>
              <span className="font-bold text-lg" style={{ color: capacityChange >= 0 ? '#27AE60' : '#C0392B' }}>
                {capacityChange > 0 ? '+' : ''}{capacityChange}%
              </span>
            </div>
            <input
              type="range"
              min="-40"
              max="100"
              value={capacityChange}
              onChange={(e) => setCapacityChange(Number(e.target.value))}
              className="w-full h-3 rounded-lg appearance-none cursor-pointer"
              style={{ backgroundColor: '#ECF0F1' }}
            />
            <div className="flex justify-between text-sm mt-2" style={{ color: '#2C3E50' }}>
              <span>-40% (Closures)</span>
              <span>+100% (Expansion)</span>
            </div>
          </div>

          {/* Cost Change */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center">
                <Truck className="h-5 w-5 mr-2" style={{ color: '#F39C12' }} />
                <label className="font-medium" style={{ color: '#2C3E50' }}>
                  Transportation Cost Change
                </label>
              </div>
              <span className="font-bold text-lg" style={{ color: costChange <= 0 ? '#27AE60' : '#C0392B' }}>
                {costChange > 0 ? '+' : ''}{costChange}%
              </span>
            </div>
            <input
              type="range"
              min="-30"
              max="50"
              value={costChange}
              onChange={(e) => setCostChange(Number(e.target.value))}
              className="w-full h-3 rounded-lg appearance-none cursor-pointer"
              style={{ backgroundColor: '#ECF0F1' }}
            />
            <div className="flex justify-between text-sm mt-2" style={{ color: '#2C3E50' }}>
              <span>-30% (Efficiency)</span>
              <span>+50% (Crisis)</span>
            </div>
          </div>

          {/* Route Disruption Toggle */}
          <div className="flex items-center justify-between p-4 rounded-lg border-2" style={{ borderColor: '#2C3E50', backgroundColor: '#ECF0F1' }}>
            <div className="flex items-center">
              <AlertTriangle className="h-5 w-5 mr-3" style={{ color: '#C0392B' }} />
              <div>
                <label className="font-medium" style={{ color: '#2C3E50' }}>
                  Route Disruption Simulation
                </label>
                <p className="text-sm" style={{ color: '#2C3E50' }}>
                  Simulate highway closures or traffic disruptions
                </p>
              </div>
            </div>
            <button
              onClick={() => setRouteBlockage(!routeBlockage)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                routeBlockage ? 'text-white' : 'text-white'
              }`}
              style={{ 
                backgroundColor: routeBlockage ? '#C0392B' : '#27AE60'
              }}
            >
              {routeBlockage ? 'ON' : 'OFF'}
            </button>
          </div>
        </div>

        {/* Run Scenario Button */}
        <button
          onClick={handleRunScenario}
          disabled={loading || !scenarioName.trim()}
          className="w-full py-4 px-6 rounded-lg text-lg font-bold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          style={{ 
            backgroundColor: loading || !scenarioName.trim() ? '#95A5A6' : '#E67E22',
            color: 'white'
          }}
        >
          {loading ? (
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-3"></div>
              Running ML Optimization...
            </div>
          ) : (
            <>
              <Play className="h-5 w-5 mr-3" />
              Execute Scenario Analysis
            </>
          )}
        </button>

        {/* Predefined Scenarios */}
        <div>
          <h3 className="text-lg font-bold mb-4" style={{ color: '#2C3E50' }}>
            Industry Standard Scenarios
          </h3>
          <div className="space-y-3">
            {predefinedScenarios.map((scenario, index) => (
              <button
                key={index}
                onClick={() => loadPredefinedScenario(scenario)}
                disabled={loading}
                className="w-full text-left p-4 border-2 rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-md"
                style={{ 
                  borderColor: '#2C3E50',
                  backgroundColor: 'white'
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-bold text-base" style={{ color: '#2C3E50' }}>
                      {scenario.name}
                    </div>
                    <div className="text-sm mt-1" style={{ color: '#2C3E50' }}>
                      {scenario.description}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs" style={{ color: '#2C3E50' }}>
                      D: {scenario.demand > 0 ? '+' : ''}{scenario.demand}%
                    </div>
                    <div className="text-xs" style={{ color: '#2C3E50' }}>
                      C: {scenario.cost > 0 ? '+' : ''}{scenario.cost}%
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Current Data Summary */}
        <div className="rounded-lg p-4 border-2" style={{ backgroundColor: '#ECF0F1', borderColor: '#16A085' }}>
          <h3 className="text-lg font-bold mb-3" style={{ color: '#2C3E50' }}>
            Current Dataset Overview
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex items-center">
              <MapPin className="h-4 w-4 mr-2" style={{ color: '#16A085' }} />
              <span style={{ color: '#2C3E50' }}>
                <strong>{data.locations_count}</strong> Locations
              </span>
            </div>
            <div className="flex items-center">
              <Package className="h-4 w-4 mr-2" style={{ color: '#E67E22' }} />
              <span style={{ color: '#2C3E50' }}>
                <strong>{data.warehouses_count}</strong> Warehouses
              </span>
            </div>
            <div className="flex items-center">
              <Truck className="h-4 w-4 mr-2" style={{ color: '#F39C12' }} />
              <span style={{ color: '#2C3E50' }}>
                <strong>{data.stores_count}</strong> Stores
              </span>
            </div>
            <div className="flex items-center">
              <TrendingUp className="h-4 w-4 mr-2" style={{ color: '#16A085' }} />
              <span style={{ color: '#2C3E50' }}>
                <strong>{(data.capacity_records || 0) + (data.demand_records || 0)}</strong> Records
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
