import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

const applicationTables = {
  // Store uploaded files metadata (no auth required)
  uploadedFiles: defineTable({
    fileName: v.string(),
    fileType: v.string(),
    storageId: v.id("_storage"),
    uploadedAt: v.number(),
  }),

  // Store processed location data from GeoLocations.xlsx
  locations: defineTable({
    locationId: v.string(),
    name: v.string(),
    lat: v.optional(v.number()),
    lon: v.optional(v.number()),
    type: v.string(), // 'warehouse' or 'store'
    sheet: v.string(),
    attributes: v.any(), // Store additional IEEE DataPort attributes
  }).index("by_type", ["type"])
    .index("by_location_id", ["locationId"]),

  // Store capacity data from CapacityClustered.xlsx
  capacityData: defineTable({
    locationId: v.string(),
    capacity: v.number(),
    sheet: v.string(),
    attributes: v.any(), // ML features and constraints
  }).index("by_location", ["locationId"]),

  // Store demand data from DemandCluster.xlsx
  demandData: defineTable({
    locationId: v.optional(v.string()),
    demand: v.number(),
    period: v.optional(v.string()),
    sheet: v.string(),
    attributes: v.any(), // ML features for forecasting
  }).index("by_location", ["locationId"]),

  // Store cost data from CostCluster.xlsx and CostsMWC-Clustered.xlsx
  costData: defineTable({
    fromLocationId: v.string(),
    toLocationId: v.string(),
    cost: v.number(),
    sheet: v.string(),
    attributes: v.any(), // Cost breakdown and factors
  }).index("by_from_to", ["fromLocationId", "toLocationId"]),

  // Store ML optimization results
  optimizationResults: defineTable({
    demandForecast: v.any(), // RandomForest + LightGBM results
    allocation: v.any(), // PuLP optimization results
    routing: v.any(), // OR-Tools VRP results
    metrics: v.any(), // Performance metrics and violations
    timestamp: v.number(),
    status: v.string(),
  }).index("by_timestamp", ["timestamp"]),

  // Store scenario results (no auth required)
  scenarioResults: defineTable({
    scenarioName: v.string(),
    scenarioData: v.any(),
    results: v.any(),
    timestamp: v.number(),
  }).index("by_timestamp", ["timestamp"]),

  // Store distance and time matrices from DistanceCluster.xlsx and Time.xlsx
  matrices: defineTable({
    matrixType: v.string(), // 'distance' or 'time'
    data: v.array(v.array(v.number())),
    locationIds: v.array(v.string()),
  }).index("by_type", ["matrixType"]),
};

export default defineSchema({
  ...applicationTables,
});
