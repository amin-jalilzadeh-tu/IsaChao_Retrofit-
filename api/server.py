"""
Isabella2 Retrofit API Server

FastAPI server for exposing Isabella2 ML inference and optimization
to the dt-generic-cesium frontend.

Run with: uvicorn api.server:app --reload --port 8000
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import Isabella2 modules
try:
    from src.inference_pipeline import select_model
    from src.training_functions import get_model_path, get_scaler_path
    import torch
    import joblib
    MODELS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Isabella2 modules: {e}")
    MODELS_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="Isabella2 Retrofit API",
    description="ML inference and Pareto optimization for building retrofits",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Pydantic Models
# ============================================

class DesignVariables(BaseModel):
    """Input design variables for retrofit prediction"""
    time_horizon: int = Field(2020, ge=2020, le=2100, description="Climate scenario year")
    windows_U_Factor: float = Field(2.9, ge=0.5, le=3.0, description="Window U-Factor (W/m2K)")
    groundfloor_thermal_resistance: float = Field(0.41, ge=0.3, le=6.0, description="Ground floor R-value (m2K/W)")
    ext_walls_thermal_resistance: float = Field(0.45, ge=0.3, le=7.0, description="External walls R-value (m2K/W)")
    roof_thermal_resistance: float = Field(0.48, ge=0.3, le=9.0, description="Roof R-value (m2K/W)")


class RetrofitOutputs(BaseModel):
    """Predicted outputs for a retrofit scenario"""
    annual_energy_GJ: float = Field(..., description="Annual energy consumption (GJ)")
    total_cost_EUR: float = Field(..., description="Total retrofit cost (EUR)")
    total_co2_kg: float = Field(..., description="Total CO2 emissions (kg)")
    comfort_days: float = Field(..., description="Comfort days (17.5-24C)")


class InferenceRequest(BaseModel):
    """Request body for inference endpoint"""
    method: str = Field("uncertainty", description="Training method")
    model_type: str = Field("Data_Based_Isa", description="Model architecture")
    design_variables: List[DesignVariables]


class InferenceResponse(BaseModel):
    """Response body for inference endpoint"""
    predictions: List[RetrofitOutputs]
    execution_time_ms: float
    confidence: Optional[List[float]] = None


class OptimizationRequest(BaseModel):
    """Request body for optimization endpoint"""
    n_generations: int = Field(100, ge=10, le=1000)
    pop_size: int = Field(50, ge=20, le=500)
    method: str = Field("uncertainty")
    model_type: str = Field("Data_Based_Isa")
    time_horizon: Optional[int] = Field(None)


class ParetoSolution(BaseModel):
    """A single Pareto-optimal solution"""
    id: str
    time_horizon: int
    windows_U_Factor: float
    groundfloor_thermal_resistance: float
    ext_walls_thermal_resistance: float
    roof_thermal_resistance: float
    annual_energy_GJ: float
    total_cost_EUR: float
    total_co2_kg: float
    comfort_days: float


class OptimizationResponse(BaseModel):
    """Response body for optimization endpoint"""
    pareto_solutions: List[ParetoSolution]
    total_evaluated: int
    run_time_seconds: float


class MCDMRequest(BaseModel):
    """Request body for MCDM ranking"""
    solutions: List[dict]
    weights: dict
    bounds: dict


# ============================================
# Model Loading & Inference
# ============================================

# Cache for loaded models
_model_cache = {}
_scaler_cache = {}

def load_model_and_scalers(method: str, model_type: str):
    """Load model and scalers, with caching"""
    cache_key = f"{method}_{model_type}"

    if cache_key not in _model_cache:
        if not MODELS_AVAILABLE:
            raise HTTPException(500, "ML modules not available")

        try:
            # Load model
            model = select_model(method, model_type, input_size=5)
            model_path = get_model_path(method, model_type)
            model.load_state_dict(torch.load(model_path, map_location='cpu'))
            model.eval()
            _model_cache[cache_key] = model

            # Load scalers
            scaler_X_path = get_scaler_path(method, model_type, 'X')
            scaler_X = joblib.load(scaler_X_path)

            scalers_Y = []
            for i in range(4):  # 4 targets
                scaler_Y_path = get_scaler_path(method, model_type, f'Y_{i}')
                scalers_Y.append(joblib.load(scaler_Y_path))

            _scaler_cache[cache_key] = {'X': scaler_X, 'Y': scalers_Y}

        except Exception as e:
            raise HTTPException(500, f"Failed to load model: {str(e)}")

    return _model_cache[cache_key], _scaler_cache[cache_key]


def run_inference(design_vars: List[DesignVariables], method: str, model_type: str) -> List[RetrofitOutputs]:
    """Run ML inference on design variables"""
    model, scalers = load_model_and_scalers(method, model_type)

    # Convert to numpy array
    X = np.array([[
        dv.time_horizon,
        dv.windows_U_Factor,
        dv.groundfloor_thermal_resistance,
        dv.ext_walls_thermal_resistance,
        dv.roof_thermal_resistance
    ] for dv in design_vars])

    # Normalize inputs
    X_scaled = scalers['X'].transform(X)

    # Run inference
    with torch.no_grad():
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        outputs = model(X_tensor)

        # Handle different model output formats
        if isinstance(outputs, tuple):
            predictions = outputs[0]  # First element is predictions
        else:
            predictions = outputs

    # Denormalize outputs
    predictions_np = predictions.numpy()
    results = []

    for i in range(len(design_vars)):
        pred_denorm = []
        for j, scaler_Y in enumerate(scalers['Y']):
            val = scaler_Y.inverse_transform([[predictions_np[i, j]]])[0, 0]
            pred_denorm.append(float(val))

        results.append(RetrofitOutputs(
            annual_energy_GJ=pred_denorm[0],
            total_cost_EUR=pred_denorm[1],
            total_co2_kg=pred_denorm[2],
            comfort_days=pred_denorm[3]
        ))

    return results


# ============================================
# Cost & CO2 Calculation (from Isabella2 utils)
# ============================================

def calculate_cost(dv: DesignVariables) -> float:
    """Calculate retrofit cost from design variables"""
    cost = 0

    # Window cost
    if dv.windows_U_Factor <= 0.85:
        cost += 622
    elif dv.windows_U_Factor <= 1.25:
        cost += 350

    # Floor cost
    floor_r = dv.groundfloor_thermal_resistance
    if floor_r > 0.5:
        cost += min(108, (floor_r - 0.41) / (5.6 - 0.41) * 108)

    # Walls cost
    walls_r = dv.ext_walls_thermal_resistance
    if walls_r > 0.5:
        cost += min(222, (walls_r - 0.45) / (6.7 - 0.45) * 222)

    # Roof cost
    roof_r = dv.roof_thermal_resistance
    if roof_r > 0.5:
        cost += min(139, (roof_r - 0.48) / (8.7 - 0.48) * 139)

    return cost


def calculate_co2(dv: DesignVariables) -> float:
    """Calculate CO2 emissions from design variables"""
    co2 = 0

    # Window CO2
    if dv.windows_U_Factor <= 0.85:
        co2 += 150
    elif dv.windows_U_Factor <= 1.25:
        co2 += 75

    # Floor CO2
    floor_r = dv.groundfloor_thermal_resistance
    if floor_r > 0.5:
        co2 += min(11, (floor_r - 0.41) / (5.6 - 0.41) * 11)

    # Walls CO2
    walls_r = dv.ext_walls_thermal_resistance
    if walls_r > 0.5:
        co2 += min(17, (walls_r - 0.45) / (6.7 - 0.45) * 17)

    # Roof CO2
    roof_r = dv.roof_thermal_resistance
    if roof_r > 0.5:
        co2 += min(23, (roof_r - 0.48) / (8.7 - 0.48) * 23)

    return co2


# ============================================
# API Endpoints
# ============================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "models_available": MODELS_AVAILABLE,
        "project_root": str(PROJECT_ROOT)
    }


@app.get("/api/models")
async def get_available_models():
    """Get available models and methods"""
    return {
        "methods": ["weighted_sum", "mgda", "uncertainty"],
        "architectures": [
            "shared", "separate", "Ref_Based_Isa", "Data_Based_Isa",
            "More_Shared_Layer", "Few_Shared_Layers", "Deep_Balanced_Layer"
        ]
    }


@app.post("/api/inference", response_model=InferenceResponse)
async def inference_endpoint(request: InferenceRequest):
    """Run ML inference on design variables"""
    start_time = time.time()

    if not MODELS_AVAILABLE:
        # Fallback: use simple calculations without ML
        predictions = []
        for dv in request.design_variables:
            # Estimate energy based on thermal properties
            base_energy = 50  # GJ baseline
            energy_reduction = (
                (2.9 - dv.windows_U_Factor) / 2.1 * 10 +
                (dv.groundfloor_thermal_resistance - 0.41) / 5.19 * 5 +
                (dv.ext_walls_thermal_resistance - 0.45) / 6.25 * 8 +
                (dv.roof_thermal_resistance - 0.48) / 8.22 * 7
            )
            annual_energy = max(10, base_energy - energy_reduction)

            predictions.append(RetrofitOutputs(
                annual_energy_GJ=annual_energy,
                total_cost_EUR=calculate_cost(dv),
                total_co2_kg=calculate_co2(dv),
                comfort_days=200 + energy_reduction * 2  # Rough estimate
            ))
    else:
        predictions = run_inference(
            request.design_variables,
            request.method,
            request.model_type
        )

    execution_time = (time.time() - start_time) * 1000

    return InferenceResponse(
        predictions=predictions,
        execution_time_ms=execution_time
    )


@app.post("/api/optimize", response_model=OptimizationResponse)
async def optimization_endpoint(request: OptimizationRequest):
    """Run NSGA2 Pareto optimization"""
    start_time = time.time()

    try:
        # Try to use pymoo for optimization
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import Problem
        from pymoo.optimize import minimize

        class RetrofitProblem(Problem):
            def __init__(self, method, model_type, time_horizon):
                super().__init__(
                    n_var=4,  # 4 design variables (excluding time_horizon)
                    n_obj=4,  # 4 objectives
                    n_constr=0,
                    xl=np.array([0.8, 0.41, 0.45, 0.48]),
                    xu=np.array([2.9, 5.6, 6.7, 8.7])
                )
                self.method = method
                self.model_type = model_type
                self.time_horizon = time_horizon or 2020

            def _evaluate(self, X, out, *args, **kwargs):
                # Convert to design variables
                design_vars = [
                    DesignVariables(
                        time_horizon=self.time_horizon,
                        windows_U_Factor=x[0],
                        groundfloor_thermal_resistance=x[1],
                        ext_walls_thermal_resistance=x[2],
                        roof_thermal_resistance=x[3]
                    )
                    for x in X
                ]

                if MODELS_AVAILABLE:
                    predictions = run_inference(design_vars, self.method, self.model_type)
                else:
                    # Fallback
                    predictions = []
                    for dv in design_vars:
                        base_energy = 50
                        energy_reduction = (
                            (2.9 - dv.windows_U_Factor) / 2.1 * 10 +
                            (dv.groundfloor_thermal_resistance - 0.41) / 5.19 * 5 +
                            (dv.ext_walls_thermal_resistance - 0.45) / 6.25 * 8 +
                            (dv.roof_thermal_resistance - 0.48) / 8.22 * 7
                        )
                        predictions.append(RetrofitOutputs(
                            annual_energy_GJ=max(10, base_energy - energy_reduction),
                            total_cost_EUR=calculate_cost(dv),
                            total_co2_kg=calculate_co2(dv),
                            comfort_days=200 + energy_reduction * 2
                        ))

                # Objectives: minimize energy, cost, co2; maximize comfort (so negate)
                out["F"] = np.array([
                    [p.annual_energy_GJ, p.total_cost_EUR, p.total_co2_kg, -p.comfort_days]
                    for p in predictions
                ])

        problem = RetrofitProblem(request.method, request.model_type, request.time_horizon)
        algorithm = NSGA2(pop_size=request.pop_size)

        result = minimize(
            problem,
            algorithm,
            ('n_gen', request.n_generations),
            seed=42,
            verbose=False
        )

        # Extract Pareto solutions
        pareto_solutions = []
        for i, (x, f) in enumerate(zip(result.X, result.F)):
            pareto_solutions.append(ParetoSolution(
                id=f"opt_{i}",
                time_horizon=request.time_horizon or 2020,
                windows_U_Factor=float(x[0]),
                groundfloor_thermal_resistance=float(x[1]),
                ext_walls_thermal_resistance=float(x[2]),
                roof_thermal_resistance=float(x[3]),
                annual_energy_GJ=float(f[0]),
                total_cost_EUR=float(f[1]),
                total_co2_kg=float(f[2]),
                comfort_days=float(-f[3])  # Negate back
            ))

        return OptimizationResponse(
            pareto_solutions=pareto_solutions,
            total_evaluated=request.n_generations * request.pop_size,
            run_time_seconds=time.time() - start_time
        )

    except ImportError:
        # Fallback: generate random Pareto-like solutions
        pareto_solutions = []
        for i in range(min(50, request.pop_size)):
            # Random design variables
            dv = DesignVariables(
                time_horizon=request.time_horizon or 2020,
                windows_U_Factor=np.random.uniform(0.8, 2.9),
                groundfloor_thermal_resistance=np.random.uniform(0.41, 5.6),
                ext_walls_thermal_resistance=np.random.uniform(0.45, 6.7),
                roof_thermal_resistance=np.random.uniform(0.48, 8.7)
            )

            # Estimate outputs
            base_energy = 50
            energy_reduction = (
                (2.9 - dv.windows_U_Factor) / 2.1 * 10 +
                (dv.groundfloor_thermal_resistance - 0.41) / 5.19 * 5 +
                (dv.ext_walls_thermal_resistance - 0.45) / 6.25 * 8 +
                (dv.roof_thermal_resistance - 0.48) / 8.22 * 7
            )

            pareto_solutions.append(ParetoSolution(
                id=f"fallback_{i}",
                time_horizon=dv.time_horizon,
                windows_U_Factor=dv.windows_U_Factor,
                groundfloor_thermal_resistance=dv.groundfloor_thermal_resistance,
                ext_walls_thermal_resistance=dv.ext_walls_thermal_resistance,
                roof_thermal_resistance=dv.roof_thermal_resistance,
                annual_energy_GJ=max(10, base_energy - energy_reduction),
                total_cost_EUR=calculate_cost(dv),
                total_co2_kg=calculate_co2(dv),
                comfort_days=200 + energy_reduction * 2
            ))

        return OptimizationResponse(
            pareto_solutions=pareto_solutions,
            total_evaluated=len(pareto_solutions),
            run_time_seconds=time.time() - start_time
        )


@app.post("/api/mcdm")
async def mcdm_endpoint(request: MCDMRequest):
    """Run MCDM ranking on Pareto solutions"""
    solutions = request.solutions
    weights = request.weights
    bounds = request.bounds

    # Normalize and score each solution
    rankings = []
    for sol in solutions:
        # Normalize objectives (0-1)
        energy_norm = 1 - (sol['energy'] - bounds['energy']['min']) / max(1, bounds['energy']['max'] - bounds['energy']['min'])
        cost_norm = 1 - (sol['cost'] - bounds['cost']['min']) / max(1, bounds['cost']['max'] - bounds['cost']['min'])
        co2_norm = 1 - (sol['co2'] - bounds['co2']['min']) / max(1, bounds['co2']['max'] - bounds['co2']['min'])
        comfort_norm = (sol['comfort'] - bounds['comfort']['min']) / max(1, bounds['comfort']['max'] - bounds['comfort']['min'])

        # Weighted score
        weighted_score = (
            weights['energy'] * energy_norm +
            weights['cost'] * cost_norm +
            weights['co2'] * co2_norm +
            weights['comfort'] * comfort_norm
        )

        rankings.append({
            'id': sol['id'],
            'weighted_score': weighted_score,
            'asf_score': weighted_score,  # Simplified
            'is_high_tradeoff': weighted_score > 0.7
        })

    # Sort by score and assign ranks
    rankings.sort(key=lambda x: x['weighted_score'], reverse=True)
    for i, r in enumerate(rankings):
        r['rank'] = i + 1

    return {'rankings': rankings}


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
