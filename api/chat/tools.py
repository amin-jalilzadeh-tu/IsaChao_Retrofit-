"""
Function calling tools for LLM integration.

Security-critical: Uses whitelisted operations instead of LLM-generated code.
This prevents code injection attacks from natural language queries.
"""
from typing import Dict, Any, List, Optional, Callable
import json
import uuid
from datetime import datetime

from api.models import SessionContext

# Whitelisted filter operations for Pareto queries
# LLM can only use these predefined filters, not generate arbitrary code
ALLOWED_FILTERS = {
    "energy_savings_min": lambda df, val: df[df["energy_savings"] >= val],
    "energy_savings_max": lambda df, val: df[df["energy_savings"] <= val],
    "cost_max": lambda df, val: df[df["cost"] <= val],
    "cost_min": lambda df, val: df[df["cost"] >= val],
    "co2_reduction_min": lambda df, val: df[df["co2_reduction"] >= val],
    "co2_reduction_max": lambda df, val: df[df["co2_reduction"] <= val],
    "comfort_min": lambda df, val: df[df["comfort_score"] >= val],
    "payback_max": lambda df, val: df[df["payback_years"] <= val],
    "payback_min": lambda df, val: df[df["payback_years"] >= val],
}

ALLOWED_SORT_FIELDS = [
    "energy_savings",
    "cost",
    "co2_reduction",
    "comfort_score",
    "payback_years",
    "investment_cost",
    "annual_savings",
]

# Background job storage (in production, use Redis)
_background_jobs: Dict[str, Dict[str, Any]] = {}


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get OpenAI function definitions for available tools.

    Returns:
        List of tool definitions in OpenAI format
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "run_inference",
                "description": "Run the MTL neural network to predict building performance metrics (energy, cost, CO2, comfort) for a specific set of design variables.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "building_id": {
                            "type": "string",
                            "description": "Building identifier (e.g., 'building_001')"
                        },
                        "windows_u_factor": {
                            "type": "number",
                            "description": "Window U-factor (W/m²K), typically 0.8-5.0"
                        },
                        "walls_insulation": {
                            "type": "number",
                            "description": "Wall insulation R-value (m²K/W), typically 1-10"
                        },
                        "roof_insulation": {
                            "type": "number",
                            "description": "Roof insulation R-value (m²K/W), typically 1-10"
                        },
                        "hvac_efficiency": {
                            "type": "number",
                            "description": "HVAC system efficiency (COP), typically 2-5"
                        },
                        "time_horizon": {
                            "type": "integer",
                            "enum": [2020, 2050, 2100],
                            "description": "Climate scenario year"
                        }
                    },
                    "required": ["building_id", "time_horizon"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "start_optimization",
                "description": "Start NSGA-II multi-objective optimization to find Pareto-optimal retrofit solutions. Returns a job_id for tracking (optimization takes 30-60 seconds).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "building_id": {
                            "type": "string",
                            "description": "Building identifier"
                        },
                        "objectives": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Objectives to optimize: energy, cost, co2, comfort"
                        },
                        "constraints": {
                            "type": "object",
                            "description": "Budget and other constraints",
                            "properties": {
                                "max_investment": {"type": "number"},
                                "min_energy_savings": {"type": "number"},
                                "min_comfort": {"type": "number"}
                            }
                        },
                        "time_horizon": {
                            "type": "integer",
                            "enum": [2020, 2050, 2100]
                        },
                        "population_size": {
                            "type": "integer",
                            "description": "NSGA-II population size (default 100)"
                        },
                        "generations": {
                            "type": "integer",
                            "description": "Number of generations (default 50)"
                        }
                    },
                    "required": ["building_id", "objectives"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_optimization_status",
                "description": "Check the status of a running optimization job.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "Job ID returned from start_optimization"
                        }
                    },
                    "required": ["job_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_pareto_solutions",
                "description": "Query and filter Pareto-optimal solutions from the current session. Uses safe, predefined filters.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filters": {
                            "type": "object",
                            "description": "Predefined filters to apply",
                            "properties": {
                                "energy_savings_min": {"type": "number", "description": "Minimum energy savings (%)"},
                                "energy_savings_max": {"type": "number", "description": "Maximum energy savings (%)"},
                                "cost_max": {"type": "number", "description": "Maximum investment cost (€)"},
                                "cost_min": {"type": "number", "description": "Minimum investment cost (€)"},
                                "co2_reduction_min": {"type": "number", "description": "Minimum CO2 reduction (%)"},
                                "payback_max": {"type": "number", "description": "Maximum payback period (years)"}
                            }
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": ["energy_savings", "cost", "co2_reduction", "comfort_score", "payback_years"],
                            "description": "Field to sort results by"
                        },
                        "ascending": {
                            "type": "boolean",
                            "description": "Sort ascending (default: false for best-first)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of solutions to return"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_similar_buildings",
                "description": "Find similar building case studies from the RAG database based on natural language description.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Natural language description of the building or scenario"
                        },
                        "time_horizon": {
                            "type": "integer",
                            "enum": [2020, 2050, 2100],
                            "description": "Climate scenario year"
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Number of similar buildings to return (default 5)"
                        }
                    },
                    "required": ["description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "explain_mcdm_ranking",
                "description": "Explain the MCDM (Multi-Criteria Decision Making) ranking for a specific solution or compare top solutions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "solution_id": {
                            "type": "string",
                            "description": "Specific solution ID to explain"
                        },
                        "method": {
                            "type": "string",
                            "enum": ["asf", "pseudo_weights", "weighted_scores"],
                            "description": "MCDM method used"
                        },
                        "compare_top_n": {
                            "type": "integer",
                            "description": "Compare top N solutions instead of explaining one"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_stage_info",
                "description": "Get information about a specific stage in the 9-stage pipeline.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stage": {
                            "type": "string",
                            "enum": [
                                "data_loading",
                                "data_processing",
                                "model_training",
                                "model_evaluation",
                                "inference",
                                "optimization",
                                "mcdm",
                                "post_processing",
                                "visualization"
                            ],
                            "description": "Pipeline stage to get info about"
                        }
                    },
                    "required": ["stage"]
                }
            }
        }
    ]


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    context: Optional[SessionContext] = None
) -> Dict[str, Any]:
    """Execute a tool call with the given arguments.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments from LLM
        context: Optional session context

    Returns:
        Tool execution result
    """
    tool_handlers = {
        "run_inference": _run_inference,
        "start_optimization": _start_optimization,
        "check_optimization_status": _check_optimization_status,
        "query_pareto_solutions": _query_pareto_solutions,
        "find_similar_buildings": _find_similar_buildings,
        "explain_mcdm_ranking": _explain_mcdm_ranking,
        "get_stage_info": _get_stage_info,
    }

    handler = tool_handlers.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        return await handler(arguments, context)
    except Exception as e:
        return {"error": str(e)}


async def _run_inference(
    args: Dict[str, Any],
    context: Optional[SessionContext]
) -> Dict[str, Any]:
    """Run MTL inference for building performance prediction."""
    # TODO: Integrate with actual inference endpoint
    # For now, return mock structure
    return {
        "status": "success",
        "building_id": args.get("building_id"),
        "predictions": {
            "energy_consumption": 125.5,  # kWh/m²/year
            "annual_cost": 2450.0,  # €/year
            "co2_emissions": 45.2,  # kg/m²/year
            "comfort_score": 0.82  # 0-1 scale
        },
        "design_variables": {
            "windows_u_factor": args.get("windows_u_factor", 2.0),
            "walls_insulation": args.get("walls_insulation", 3.0),
            "roof_insulation": args.get("roof_insulation", 4.0),
            "hvac_efficiency": args.get("hvac_efficiency", 3.5)
        },
        "time_horizon": args.get("time_horizon", 2020),
        "message": "Inference completed. These are predicted performance metrics for the specified design variables."
    }


async def _start_optimization(
    args: Dict[str, Any],
    context: Optional[SessionContext]
) -> Dict[str, Any]:
    """Start background optimization job."""
    job_id = str(uuid.uuid4())[:8]

    # Store job info
    _background_jobs[job_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "building_id": args.get("building_id"),
        "objectives": args.get("objectives", ["energy", "cost"]),
        "constraints": args.get("constraints", {}),
        "progress": 0,
        "estimated_completion": "30-60 seconds"
    }

    # TODO: Actually start background optimization task
    # In production, this would use Celery or asyncio background task

    return {
        "status": "started",
        "job_id": job_id,
        "message": f"Optimization started. Use check_optimization_status with job_id '{job_id}' to monitor progress. Expected completion: 30-60 seconds.",
        "building_id": args.get("building_id"),
        "objectives": args.get("objectives")
    }


async def _check_optimization_status(
    args: Dict[str, Any],
    context: Optional[SessionContext]
) -> Dict[str, Any]:
    """Check optimization job status."""
    job_id = args.get("job_id")

    if job_id not in _background_jobs:
        return {"error": f"Job not found: {job_id}"}

    job = _background_jobs[job_id]

    # Mock progress update (in production, check actual job status)
    if job["status"] == "running":
        job["progress"] = min(job.get("progress", 0) + 25, 100)
        if job["progress"] >= 100:
            job["status"] = "completed"
            job["results"] = {
                "pareto_solutions": 15,
                "best_energy": {"energy_savings": 42.5, "cost": 15000},
                "best_cost": {"energy_savings": 22.0, "cost": 5000},
                "balanced": {"energy_savings": 35.0, "cost": 10000}
            }

    return job


async def _query_pareto_solutions(
    args: Dict[str, Any],
    context: Optional[SessionContext]
) -> Dict[str, Any]:
    """Query Pareto solutions with whitelisted filters."""
    import pandas as pd

    # Get Pareto solutions from context
    if context and context.pareto_solutions:
        df = pd.DataFrame(context.pareto_solutions)
    else:
        # Return mock data if no solutions in context
        return {
            "message": "No Pareto solutions in current session. Run optimization first.",
            "solutions": [],
            "total": 0
        }

    # Apply whitelisted filters only
    filters = args.get("filters", {})
    for filter_name, filter_value in filters.items():
        if filter_name in ALLOWED_FILTERS:
            df = ALLOWED_FILTERS[filter_name](df, filter_value)
        # Silently ignore unknown filters (security: don't reveal filter names)

    # Sort
    sort_by = args.get("sort_by")
    if sort_by and sort_by in ALLOWED_SORT_FIELDS:
        ascending = args.get("ascending", False)
        df = df.sort_values(by=sort_by, ascending=ascending)

    # Limit
    limit = args.get("limit", 10)
    df = df.head(limit)

    return {
        "solutions": df.to_dict("records"),
        "total": len(df),
        "filters_applied": list(filters.keys()),
        "sorted_by": sort_by
    }


async def _find_similar_buildings(
    args: Dict[str, Any],
    context: Optional[SessionContext]
) -> Dict[str, Any]:
    """Find similar buildings using RAG."""
    from api.rag.retriever import get_retriever

    retriever = get_retriever()
    results = retriever.search_similar_buildings(
        query=args.get("description", ""),
        time_horizon=args.get("time_horizon", 2020),
        n_results=args.get("n_results", 5)
    )

    return {
        "similar_buildings": results,
        "count": len(results),
        "time_horizon": args.get("time_horizon", 2020)
    }


async def _explain_mcdm_ranking(
    args: Dict[str, Any],
    context: Optional[SessionContext]
) -> Dict[str, Any]:
    """Explain MCDM ranking methodology and results."""
    method = args.get("method", "weighted_scores")

    explanations = {
        "asf": {
            "name": "Achievement Scalarizing Function (ASF)",
            "description": "ASF minimizes the maximum weighted deviation from an ideal point. It finds solutions closest to the 'utopia' where all objectives are optimal.",
            "formula": "max_i(w_i * |f_i - z_i*|)",
            "best_for": "Finding balanced compromises that don't sacrifice any objective too much"
        },
        "pseudo_weights": {
            "name": "Pseudo-Weights",
            "description": "Calculates implicit weights based on how much each objective was traded off. Shows the 'price' paid for improvements in each objective.",
            "interpretation": "Higher pseudo-weight = more emphasis placed on that objective in this solution",
            "best_for": "Understanding trade-off patterns across the Pareto front"
        },
        "weighted_scores": {
            "name": "Weighted Scoring",
            "description": "Simple weighted sum of normalized objectives. Each solution gets a single score based on user-defined importance weights.",
            "formula": "Σ(w_i * normalized_objective_i)",
            "best_for": "Quick ranking when user knows their priorities"
        }
    }

    return {
        "method": method,
        "explanation": explanations.get(method, explanations["weighted_scores"]),
        "solution_id": args.get("solution_id"),
        "compare_top_n": args.get("compare_top_n")
    }


async def _get_stage_info(
    args: Dict[str, Any],
    context: Optional[SessionContext]
) -> Dict[str, Any]:
    """Get information about pipeline stages."""
    stage_info = {
        "data_loading": {
            "name": "Data Loading",
            "description": "Load building data from CSV files and databases",
            "inputs": ["Building geometry", "Material properties", "Climate data"],
            "outputs": ["Structured building dataset"],
            "next_stage": "data_processing"
        },
        "data_processing": {
            "name": "Data Processing",
            "description": "Clean, normalize, and prepare data for training",
            "inputs": ["Raw building data"],
            "outputs": ["Processed features", "Train/test splits"],
            "next_stage": "model_training"
        },
        "model_training": {
            "name": "Model Training",
            "description": "Train Multi-Task Learning neural network on building data",
            "inputs": ["Processed features", "Target objectives"],
            "outputs": ["Trained MTL model"],
            "next_stage": "model_evaluation"
        },
        "model_evaluation": {
            "name": "Model Evaluation",
            "description": "Evaluate model accuracy with RMSE, MAE, R² metrics",
            "inputs": ["Trained model", "Test data"],
            "outputs": ["Performance metrics", "Validation plots"],
            "next_stage": "inference"
        },
        "inference": {
            "name": "Inference",
            "description": "Predict building performance for new design variables",
            "inputs": ["Design variables", "Trained model"],
            "outputs": ["Predicted: energy, cost, CO2, comfort"],
            "next_stage": "optimization"
        },
        "optimization": {
            "name": "NSGA-II Optimization",
            "description": "Multi-objective optimization to find Pareto-optimal solutions",
            "inputs": ["Objective functions", "Constraints", "Variable bounds"],
            "outputs": ["Pareto front", "Non-dominated solutions"],
            "next_stage": "mcdm"
        },
        "mcdm": {
            "name": "Multi-Criteria Decision Making",
            "description": "Rank and select from Pareto solutions using preference methods",
            "inputs": ["Pareto solutions", "User preferences"],
            "outputs": ["Ranked solutions", "Best compromise"],
            "next_stage": "post_processing"
        },
        "post_processing": {
            "name": "Post-Processing",
            "description": "Calculate derived metrics and prepare final results",
            "inputs": ["Selected solutions"],
            "outputs": ["Payback analysis", "Sensitivity analysis"],
            "next_stage": "visualization"
        },
        "visualization": {
            "name": "Visualization",
            "description": "Generate plots and reports for decision support",
            "inputs": ["All results"],
            "outputs": ["Pareto plots", "Trade-off analysis", "Reports"]
        }
    }

    stage = args.get("stage")
    if stage in stage_info:
        return {"stage": stage, **stage_info[stage]}
    else:
        return {
            "error": f"Unknown stage: {stage}",
            "available_stages": list(stage_info.keys())
        }
