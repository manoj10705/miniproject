// src/components/Dashboard.tsx
import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
} from 'recharts';
import type { PieLabelRenderProps } from 'recharts/types/polar/Pie';
import { TrendingUp, Package, Truck, AlertTriangle, DollarSign, Target } from 'lucide-react';
import { SupplyChainData, OptimizationResults, ScenarioResult } from '../types';

interface DashboardProps {
  data: SupplyChainData;
  results: OptimizationResults | null;
  scenarioResults: ScenarioResult[];
}

export default function Dashboard({ data, results, scenarioResults }: DashboardProps) {
  if (!results) {
    return (
      <div
        className="bg-white rounded-lg shadow-lg border-2 p-12 text-center"
        style={{ borderColor: '#2C3E50' }}
      >
        <Package className="mx-auto h-16 w-16 mb-6" style={{ color: '#2C3E50' }} />
        <h3 className="text-2xl font-bold mb-4" style={{ color: '#2C3E50' }}>
          No Optimization Results Available
        </h3>
        <p className="text-lg" style={{ color: '#2C3E50' }}>
          Upload IEEE DataPort files to generate ML-powered optimization results
        </p>
      </div>
    );
  }

  // Process data for visualizations
  const demandForecastData = (results.demand_forecast?.ensemble_forecast || []).map(
    (value: any, index: number) => ({
      period: `Period ${index + 1}`,
      demand: value,
      forecast_lower: value * 0.9,
      forecast_upper: value * 1.1,
    })
  );

  const allocationData = Object.entries(results.allocation?.allocations || {}).map(
    ([warehouse, stores]: [string, any]) => {
      const total = Object.values(stores || {}).reduce(
        (sum: number, amount: any) => sum + (amount || 0),
        0
      );
      return {
        warehouse,
        total,
        utilization: ((total / 2000) * 100).toFixed(1),
      };
    }
  );

  const routingData = (results.routing?.routes || []).map((route: any) => {
    const distance = route.total_distance ?? route.distance ?? 0;
    const time = route.total_time ?? route.time ?? 0;
    const stops = route.stops?.length || 0;

    return {
      vehicle: `Vehicle ${route.vehicle_id + 1}`,
      distance,
      time,
      stops,
      efficiency: time > 0 ? ((stops / time) * 60).toFixed(2) : '0.00',
    };
  });

  const metricsData = [
    {
      title: 'Total Cost',
      value: `$${(results.metrics?.total_cost || 0).toLocaleString()}`,
      icon: DollarSign,
      color: '#27AE60',
      bgColor: '#D5DBDB',
      change: '+2.3%',
    },
    {
      title: 'Capacity Utilization',
      value: `${(results.metrics?.capacity_utilization || 0).toFixed(1)}%`,
      icon: Package,
      color: '#E67E22',
      bgColor: '#D5DBDB',
      change: '+5.1%',
    },
    {
      title: 'Demand Fulfillment',
      value: `${(results.metrics?.demand_fulfillment || 0).toFixed(1)}%`,
      icon: Target,
      color: '#16A085',
      bgColor: '#D5DBDB',
      change: '+1.8%',
    },
    {
      title: 'Active Vehicles',
      value: (results.routing?.routes?.length || 0).toString(),
      icon: Truck,
      color: '#F39C12',
      bgColor: '#D5DBDB',
      change: '-3 vehicles',
    },
  ];

  const pieData = Object.entries(results.demand_forecast?.total_demand || {}).map(
    ([store, demand]: [string, any]) => ({
      name: store,
      value: demand,
    })
  );

  const COLORS = ['#2C3E50', '#E67E22', '#16A085', '#F39C12', '#C0392B', '#27AE60'];

  return (
    <div className="space-y-8">
      {/* Key Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metricsData.map((metric, index) => (
          <div
            key={index}
            className="bg-white rounded-lg shadow-lg border-2 p-6"
            style={{ borderColor: '#2C3E50' }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="p-3 rounded-lg" style={{ backgroundColor: metric.bgColor }}>
                  <metric.icon className="h-8 w-8" style={{ color: metric.color }} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium" style={{ color: '#2C3E50' }}>
                    {metric.title}
                  </p>
                  <p className="text-2xl font-bold" style={{ color: '#2C3E50' }}>
                    {metric.value}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <span className="text-sm font-medium" style={{ color: '#27AE60' }}>
                  {metric.change}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Constraint Violations Alert */}
      {(results.metrics?.constraint_violations?.length || 0) > 0 && (
        <div
          className="rounded-lg p-6 border-2"
          style={{ backgroundColor: '#FADBD8', borderColor: '#C0392B' }}
        >
          <div className="flex items-center">
            <AlertTriangle className="h-6 w-6 mr-4" style={{ color: '#C0392B' }} />
            <div>
              <h4 className="text-lg font-bold" style={{ color: '#C0392B' }}>
                Constraint Violations Detected
              </h4>
              <p className="text-base mt-1" style={{ color: '#C0392B' }}>
                {results.metrics?.constraint_violations?.length || 0} constraint violation(s) found
                in optimization results. Review capacity and demand constraints.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Advanced Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* ML Demand Forecasting */}
        <div
          className="bg-white rounded-lg shadow-lg border-2 p-6"
          style={{ borderColor: '#2C3E50' }}
        >
          <div className="flex items-center mb-6">
            <TrendingUp className="h-6 w-6 mr-3" style={{ color: '#16A085' }} />
            <h3 className="text-xl font-bold" style={{ color: '#2C3E50' }}>
              ML Demand Forecasting (RandomForest + LightGBM)
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={demandForecastData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ECF0F1" />
              <XAxis dataKey="period" stroke="#2C3E50" />
              <YAxis stroke="#2C3E50" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: `2px solid #2C3E50`,
                  borderRadius: '8px',
                }}
              />
              <Line
                type="monotone"
                dataKey="demand"
                stroke="#16A085"
                strokeWidth={3}
                name="Forecast"
              />
              <Line
                type="monotone"
                dataKey="forecast_lower"
                stroke="#E67E22"
                strokeWidth={2}
                strokeDasharray="5 5"
                name="Lower Bound"
              />
              <Line
                type="monotone"
                dataKey="forecast_upper"
                stroke="#E67E22"
                strokeWidth={2}
                strokeDasharray="5 5"
                name="Upper Bound"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* PuLP Allocation Optimization */}
        <div
          className="bg-white rounded-lg shadow-lg border-2 p-6"
          style={{ borderColor: '#2C3E50' }}
        >
          <div className="flex items-center mb-6">
            <Package className="h-6 w-6 mr-3" style={{ color: '#E67E22' }} />
            <h3 className="text-xl font-bold" style={{ color: '#2C3E50' }}>
              PuLP Warehouse Allocation Optimization
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={allocationData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ECF0F1" />
              <XAxis dataKey="warehouse" stroke="#2C3E50" />
              <YAxis stroke="#2C3E50" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: `2px solid #2C3E50`,
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="total" fill="#E67E22" name="Allocated Volume" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* OR-Tools Vehicle Routing */}
        <div
          className="bg-white rounded-lg shadow-lg border-2 p-6"
          style={{ borderColor: '#2C3E50' }}
        >
          <div className="flex items-center mb-6">
            <Truck className="h-6 w-6 mr-3" style={{ color: '#F39C12' }} />
            <h3 className="text-xl font-bold" style={{ color: '#2C3E50' }}>
              OR-Tools Vehicle Routing Optimization
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <ScatterChart data={routingData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ECF0F1" />
              <XAxis dataKey="distance" stroke="#2C3E50" name="Distance (km)" />
              <YAxis dataKey="time" stroke="#2C3E50" name="Time (min)" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: `2px solid #2C3E50`,
                  borderRadius: '8px',
                }}
              />
              <Scatter dataKey="stops" fill="#F39C12" name="Route Efficiency" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Demand Distribution Analysis */}
        <div
          className="bg-white rounded-lg shadow-lg border-2 p-6"
          style={{ borderColor: '#2C3E50' }}
        >
          <div className="flex items-center mb-6">
            <Target className="h-6 w-6 mr-3" style={{ color: '#16A085' }} />
            <h3 className="text-xl font-bold" style={{ color: '#2C3E50' }}>
              Geographic Demand Distribution
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(props: PieLabelRenderProps) => {
                  const name = props.name ?? 'Unknown';
                  const percent = props.percent ?? 0;
                  return `${name} ${(percent * 100).toFixed(0)}%`;
                }}
                outerRadius={120}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: `2px solid #2C3E50`,
                  borderRadius: '8px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Scenario Comparison Table */}
      {scenarioResults.length > 0 && (
        <div
          className="bg-white rounded-lg shadow-lg border-2 p-6"
          style={{ borderColor: '#2C3E50' }}
        >
          <h3 className="text-xl font-bold mb-6" style={{ color: '#2C3E50' }}>
            What-If Scenario Analysis Results
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead style={{ backgroundColor: '#ECF0F1' }}>
                <tr>
                  <th
                    className="px-6 py-4 text-left text-sm font-bold uppercase tracking-wider"
                    style={{ color: '#2C3E50' }}
                  >
                    Scenario
                  </th>
                  <th
                    className="px-6 py-4 text-left text-sm font-bold uppercase tracking-wider"
                    style={{ color: '#2C3E50' }}
                  >
                    Total Cost
                  </th>
                  <th
                    className="px-6 py-4 text-left text-sm font-bold uppercase tracking-wider"
                    style={{ color: '#2C3E50' }}
                  >
                    Capacity Utilization
                  </th>
                  <th
                    className="px-6 py-4 text-left text-sm font-bold uppercase tracking-wider"
                    style={{ color: '#2C3E50' }}
                  >
                    Demand Fulfillment
                  </th>
                  <th
                    className="px-6 py-4 text-left text-sm font-bold uppercase tracking-wider"
                    style={{ color: '#2C3E50' }}
                  >
                    Performance Impact
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y-2" style={{ borderColor: '#ECF0F1' }}>
                <tr style={{ backgroundColor: '#F8F9FA' }}>
                  <td
                    className="px-6 py-4 whitespace-nowrap font-bold"
                    style={{ color: '#2C3E50' }}
                  >
                    Baseline (Current)
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap" style={{ color: '#2C3E50' }}>
                    ${(results.metrics?.total_cost || 0).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap" style={{ color: '#2C3E50' }}>
                    {(results.metrics?.capacity_utilization || 0).toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap" style={{ color: '#2C3E50' }}>
                    {(results.metrics?.demand_fulfillment || 0).toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className="px-3 py-1 rounded-full text-sm font-medium"
                      style={{ backgroundColor: '#27AE60', color: 'white' }}
                    >
                      Reference
                    </span>
                  </td>
                </tr>

                {scenarioResults.map((scenario, index) => {
                  // Be defensive about shapes coming back from the backend
                  const raw: any = scenario as any;

                  // Step 1: get something like { scenario_name, results, comparison, ... }
                  const scenarioResultsRoot =
                    raw.results?.scenario_results ??
                    raw.scenario_results ??
                    raw.results ??
                    raw;

                  // Step 2: get the optimization triple { demand_forecast, allocation, routing }
                  const optimization =
                    scenarioResultsRoot.results ?? scenarioResultsRoot.optimization ?? scenarioResultsRoot;

                  const routing = optimization.routing || {};
                  const allocation = optimization.allocation || {};

                  const scenarioCost: number = Number(
                    routing.total_cost ?? routing.totalDistance ?? 0
                  );
                  const scenarioCapacity: number = Number(
                    allocation.capacity_utilization ?? 0
                  );

                  // No per-scenario demand fulfillment in backend yet
                  const scenarioDemandFulfillment: number | undefined = undefined;

                  const baselineCost = results.metrics?.total_cost || 0;
                  const costDiff = scenarioCost - baselineCost;
                  const isImprovement = costDiff < 0;

                  return (
                    <tr key={index}>
                      <td
                        className="px-6 py-4 whitespace-nowrap font-medium"
                        style={{ color: '#2C3E50' }}
                      >
                        {raw.scenarioName ?? scenarioResultsRoot.scenario_name ?? `Scenario ${index + 1}`}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap" style={{ color: '#2C3E50' }}>
                        ${scenarioCost.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap" style={{ color: '#2C3E50' }}>
                        {`${scenarioCapacity.toFixed(1)}%`}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap" style={{ color: '#2C3E50' }}>
                        {typeof scenarioDemandFulfillment === 'number'
                          ? `${scenarioDemandFulfillment.toFixed(1)}%`
                          : 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className="px-3 py-1 rounded-full text-sm font-medium"
                          style={{
                            backgroundColor: isImprovement ? '#27AE60' : '#C0392B',
                            color: 'white',
                          }}
                        >
                          {isImprovement ? '↓' : '↑'} ${Math.abs(costDiff).toLocaleString()}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
