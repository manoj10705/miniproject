import React, { useState, useCallback, useEffect} from 'react';
import { Toaster } from 'sonner';
import FileUpload from './components/FileUpload';
import Dashboard from './components/Dashboard';
import ScenarioPanel from './components/ScenarioPanel';
import { SupplyChainData, OptimizationResults, ScenarioResult } from './types';

// ...rest of your App.tsx exactly as you posted...


export default function App() {
  const [loading, setLoading] = useState(false);
  const [scenarioResults, setScenarioResults] = useState<ScenarioResult[]>([]);
  const [dataSummary, setDataSummary] = useState<SupplyChainData | null>(null);
  const [optimizationResults, setOptimizationResults] = useState<OptimizationResults | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);

  // On first load, ask backend if anything is already loaded
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("http://localhost:8000/data-summary");
        if (!res.ok) {
          setInitialLoading(false);
          return;
        }
        const json = await res.json();

        if (json.status === "success") {
          const s = json.summary;
          setDataSummary({
            locations_count: s.locations_count ?? 0,
            warehouses_count: s.warehouses_count ?? 0,
            stores_count: s.stores_count ?? 0,
            time_periods: s.time_periods ?? 0,
            capacity_records: 0,
            demand_records: 0,
          });

          if (s.has_results) {
            const res2 = await fetch("http://localhost:8000/results");
            if (res2.ok) {
              const json2 = await res2.json();
              const r = json2.results;
              setOptimizationResults({
                demand_forecast: r.demand_forecast,
                allocation: r.allocation,
                routing: r.routing,
                metrics: r.metrics,
              });
            }
          }
        }
      } catch (e) {
        console.error("Initial data fetch failed", e);
      } finally {
        setInitialLoading(false);
      }
    })();
  }, []);

  const handleDataUpload = useCallback((uploadedData: SupplyChainData, uploadedResults: OptimizationResults) => {
    setDataSummary(uploadedData);
    setOptimizationResults(uploadedResults);
    setScenarioResults([]); // reset scenarios after new upload
  }, []);

  const handleScenarioRun = useCallback((scenarioResult: ScenarioResult) => {
    setScenarioResults(prev => [...prev, scenarioResult]);
  }, []);

  const allScenarioResults: ScenarioResult[] = [...scenarioResults];

  const showUpload = !dataSummary || dataSummary.locations_count === 0;

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#ECF0F1' }}>
      <header className="bg-white shadow-sm border-b" style={{ borderColor: '#2C3E50' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold" style={{ color: '#2C3E50' }}>
                Supply Chain Optimization Platform
              </h1>
              <p className="text-base mt-1" style={{ color: '#2C3E50' }}>
                Advanced Analytics for Warehouse Allocation & Vehicle Routing
              </p>
            </div>
            {dataSummary && (
              <div className="text-sm" style={{ color: '#2C3E50' }}>
                <div className="bg-white rounded-lg shadow-sm border px-3 py-2">
                  <span className="font-medium">{dataSummary.locations_count}</span> locations •{' '}
                  <span className="font-medium">{dataSummary.warehouses_count}</span> warehouses •{' '}
                  <span className="font-medium">{dataSummary.stores_count}</span> stores
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {showUpload ? (
          <div className="max-w-2xl mx-auto">
            <FileUpload onDataUpload={handleDataUpload} loading={loading} setLoading={setLoading} />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className="lg:col-span-3">
                <Dashboard 
                  data={dataSummary!} 
                  results={optimizationResults || null} 
                  scenarioResults={allScenarioResults}
                />
              </div>
              <div className="lg:col-span-1">
                <ScenarioPanel 
                  data={dataSummary!} 
                  onScenarioRun={handleScenarioRun}
                  loading={loading}
                  setLoading={setLoading}
                />
              </div>
            </div>
          </div>
        )}
      </main>

      <Toaster position="top-right" />
    </div>
  );
}
