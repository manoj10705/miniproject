import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import lightgbm as lgb
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class DemandForecaster:
    """Demand forecasting using RandomForest, LinearRegression, and LightGBM"""
    
    def __init__(self):
        self.models = {
            'random_forest': RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            ),
            'linear_regression': LinearRegression(),
            'lightgbm': lgb.LGBMRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                verbose=-1
            )
        }
        self.trained_models = {}
        self.feature_columns = []
        self.target_column = 'demand'
        self.scaler = None
        
    def prepare_features(self, demand_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare features from demand cluster data"""
        try:
            df = pd.DataFrame(demand_data)

            if df.empty:
                logger.warning("Empty demand data received in prepare_features")
                self.feature_columns = []
                return df

            # 1) Convert numeric-like strings to numbers where possible
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = pd.to_numeric(df[col], errors="ignore")

            # 2) Identify store-demand columns
            #    In your DemandCluster files, store columns are typically numeric IDs like 142452, 124075, etc.
            #    We'll treat ANY numeric-typed column that is not obviously an index as a demand contributor.
            numeric_cols_all = df.select_dtypes(include=[np.number]).columns.tolist()

            # Drop meta/index-like columns from demand contributors
            meta_like = {"index"}
            demand_contributors = [c for c in numeric_cols_all if str(c).lower() not in meta_like]
            logger.info(f"Demand contributor columns: {demand_contributors}")


            if demand_contributors:
                # Total demand per record (e.g., per period / store cluster)
                df["total_demand"] = df[demand_contributors].sum(axis=1)
                self.target_column = "total_demand"
            else:
                # Fallback: we won't crash here, just log and let train() complain later if needed
                logger.warning("No numeric demand contributors found; total_demand will not be created")

            # 3) Recompute numeric columns (now including total_demand)
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

            # Remove target column from feature candidates
            if self.target_column in numeric_columns:
                numeric_columns.remove(self.target_column)

            # 4) Optional: time features from 'period' if present
            if "period" in df.columns:
                try:
                    df["period"] = pd.to_datetime(df["period"], errors="coerce")
                    df["period_year"] = df["period"].dt.year
                    df["period_month"] = df["period"].dt.month
                    df["period_day"] = df["period"].dt.day
                    df["period_dayofweek"] = df["period"].dt.dayofweek
                    numeric_columns.extend(
                        ["period_year", "period_month", "period_day", "period_dayofweek"]
                    )
                except Exception as e:
                    logger.warning(f"Could not generate time features from 'period': {e}")

            # 5) Final feature list: only columns that actually exist
            self.feature_columns = [c for c in numeric_columns if c in df.columns]

            if self.feature_columns:
                df[self.feature_columns] = df[self.feature_columns].fillna(
                    df[self.feature_columns].mean()
                )

            logger.info(f"Prepared {len(self.feature_columns)} features: {self.feature_columns}")
            return df

        except Exception as e:
            logger.error(f"Error preparing features: {str(e)}")
            raise


    
    def train(self, demand_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train demand forecasting models"""
        try:
            logger.info("Starting demand forecasting model training")
            
            # Prepare data
            df = self.prepare_features(demand_data)
            
            # Decide target column more robustly

            # All numeric columns in the demand data
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

            if not numeric_cols:
                raise ValueError("No numeric columns available in demand data for forecasting")

            # If our current target_column exists AND is numeric, keep it
            if self.target_column in numeric_cols:
                target_col = self.target_column
            else:
                # Try to find a numeric column whose name looks like demand
                demand_like = [
                    c for c in numeric_cols
                    if isinstance(c, str) and ("demand" in c.lower() or "quantity" in c.lower())
                ]

                if demand_like:
                    target_col = demand_like[0]
                else:
                    # Fallback: use the first numeric column as target
                    target_col = numeric_cols[0]

            self.target_column = target_col
            print("USING DEMAND TARGET COLUMN:", self.target_column)
            if not self.feature_columns:
                raise ValueError("No feature columns available for training")

            
            # Prepare features and target
            X = df[self.feature_columns].values
            y = df[self.target_column].values
            
            # Remove rows with NaN in target
            valid_indices = ~np.isnan(y)
            X = X[valid_indices]
            y = y[valid_indices]
            
            if len(X) == 0:
                raise ValueError("No valid data points for training")
            
            # Split data
            if len(X) > 10:  # Only split if we have enough data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
            else:
                X_train, X_test, y_train, y_test = X, X, y, y
            
            # Train models
            training_results = {}
            
            for model_name, model in self.models.items():
                try:
                    logger.info(f"Training {model_name}")
                    
                    # Train model
                    model.fit(X_train, y_train)
                    
                    # Make predictions
                    y_pred_train = model.predict(X_train)
                    y_pred_test = model.predict(X_test)
                    
                    # Calculate metrics
                    train_mae = mean_absolute_error(y_train, y_pred_train)
                    test_mae = mean_absolute_error(y_test, y_pred_test)
                    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
                    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
                    
                    training_results[model_name] = {
                        'train_mae': train_mae,
                        'test_mae': test_mae,
                        'train_rmse': train_rmse,
                        'test_rmse': test_rmse
                    }
                    
                    # Store trained model
                    self.trained_models[model_name] = model
                    
                    logger.info(f"{model_name} - Test MAE: {test_mae:.2f}, Test RMSE: {test_rmse:.2f}")
                    
                except Exception as e:
                    logger.error(f"Error training {model_name}: {str(e)}")
                    training_results[model_name] = {'error': str(e)}
            
            logger.info("Demand forecasting training completed")
            return training_results
            
        except Exception as e:
            logger.error(f"Error in demand forecasting training: {str(e)}")
            raise
    
    def forecast(self, demand_data: List[Dict[str, Any]], periods_ahead: int = 12) -> Dict[str, Any]:
        """Generate demand forecasts"""
        try:
            logger.info(f"Generating demand forecasts for {periods_ahead} periods ahead")
            
            if not self.trained_models:
                raise ValueError("Models not trained. Call train() first.")
            
            # Prepare data
            df = self.prepare_features(demand_data)
            
            # Get the latest data point for forecasting
            if len(df) == 0:
                raise ValueError("No data available for forecasting")
            
            # Use the most recent data as base for forecasting
            latest_features = df[self.feature_columns].iloc[-1:].values
            
            forecasts = {}
            
            # Generate forecasts with each model
            for model_name, model in self.trained_models.items():
                try:
                    # Simple approach: use latest features to predict next periods
                    model_forecasts = []
                    current_features = latest_features.copy()
                    
                    for period in range(periods_ahead):
                        # Predict next period
                        pred = model.predict(current_features)[0]
                        model_forecasts.append(max(0, pred))  # Ensure non-negative demand
                        
                        # Update lag features if they exist
                        lag_indices = [i for i, col in enumerate(self.feature_columns) if 'lag' in col]
                        if lag_indices:
                            # Shift lag features
                            for i in range(len(lag_indices) - 1, 0, -1):
                                if lag_indices[i] < len(current_features[0]):
                                    current_features[0][lag_indices[i]] = current_features[0][lag_indices[i-1]]
                            # Set most recent lag to current prediction
                            if lag_indices and lag_indices[0] < len(current_features[0]):
                                current_features[0][lag_indices[0]] = pred
                    
                    forecasts[model_name] = model_forecasts
                    
                except Exception as e:
                    logger.error(f"Error forecasting with {model_name}: {str(e)}")
                    forecasts[model_name] = [0] * periods_ahead
            
            # Ensemble forecast (average of all models)
            if forecasts:
                ensemble_forecast = []
                for period in range(periods_ahead):
                    period_predictions = [forecasts[model][period] for model in forecasts.keys() if len(forecasts[model]) > period]
                    if period_predictions:
                        ensemble_forecast.append(np.mean(period_predictions))
                    else:
                        ensemble_forecast.append(0)
                
                forecasts['ensemble'] = ensemble_forecast
            
            # Calculate total demand by location/store if location data is available
            total_demand = {}
            if 'location_id' in df.columns or 'store_id' in df.columns:
                location_col = 'location_id' if 'location_id' in df.columns else 'store_id'
                unique_locations = df[location_col].unique()
                
                for location in unique_locations:
                    location_data = df[df[location_col] == location]
                    if len(location_data) > 0:
                        # Use average historical demand as baseline
                        avg_demand = location_data[self.target_column].mean() if self.target_column in location_data.columns else 0
                        total_demand[str(location)] = max(0, avg_demand)
            else:
                # Use overall average
                avg_demand = df[self.target_column].mean() if self.target_column in df.columns else 0
                total_demand['overall'] = max(0, avg_demand)
            
            result = {
                'forecasts_by_model': forecasts,
                'ensemble_forecast': forecasts.get('ensemble', []),
                'total_demand': total_demand,
                'forecast_periods': periods_ahead,
                'feature_importance': self._get_feature_importance()
            }
            
            logger.info("Demand forecasting completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in demand forecasting: {str(e)}")
            raise
    
    def _get_feature_importance(self) -> Dict[str, Any]:
        """Get feature importance from trained models"""
        try:
            importance = {}
            
            # Random Forest feature importance
            if 'random_forest' in self.trained_models:
                rf_model = self.trained_models['random_forest']
                if hasattr(rf_model, 'feature_importances_'):
                    importance['random_forest'] = dict(zip(
                        self.feature_columns, 
                        rf_model.feature_importances_
                    ))
            
            # LightGBM feature importance
            if 'lightgbm' in self.trained_models:
                lgb_model = self.trained_models['lightgbm']
                if hasattr(lgb_model, 'feature_importances_'):
                    importance['lightgbm'] = dict(zip(
                        self.feature_columns, 
                        lgb_model.feature_importances_
                    ))
            
            return importance
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {str(e)}")
            return {}
