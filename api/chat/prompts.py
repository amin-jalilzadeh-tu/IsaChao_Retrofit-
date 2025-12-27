"""
System prompts and templates for LLM conversations.

Provides context-aware prompts for different conversation modes:
- Navigation: Guiding users through the pipeline
- Interpretation: Explaining results and trade-offs
- Technical: Answering methodology questions
"""
from typing import Optional, List, Dict, Any
from api.models import SessionContext


SYSTEM_PROMPT_BASE = """You are Isabella, an AI assistant for building retrofit optimization.
You help users navigate a 9-stage pipeline for multi-objective building performance optimization:

1. **Data Loading**: Import building geometry, materials, and climate data
2. **Data Processing**: Clean and prepare features for modeling
3. **Model Training**: Train Multi-Task Learning (MTL) neural networks
4. **Model Evaluation**: Validate model accuracy (RMSE, MAE, R²)
5. **Inference**: Predict energy, cost, CO2, and comfort for design variables
6. **Optimization**: Run NSGA-II to find Pareto-optimal retrofit solutions
7. **MCDM**: Rank solutions using multi-criteria decision making
8. **Post-Processing**: Calculate payback, sensitivity analysis
9. **Visualization**: Generate plots and reports

You can:
- Guide users through each pipeline stage
- Explain optimization results and Pareto trade-offs
- Compare retrofit solutions across 4 objectives
- Find similar building case studies
- Run inference and optimization via function calls

Always be concise and actionable. Use bullet points for comparisons.
When discussing trade-offs, quantify differences (e.g., "15% more energy savings for €5,000 extra").
"""

SYSTEM_PROMPT_NAVIGATION = """
Current focus: NAVIGATION MODE

Help users understand where they are in the pipeline and what to do next.
- Explain what each stage does and why it matters
- Guide users to the appropriate tools/endpoints
- Suggest next steps based on their progress
"""

SYSTEM_PROMPT_INTERPRETATION = """
Current focus: INTERPRETATION MODE

Help users understand optimization results and make decisions.
- Explain Pareto fronts: "these are all non-dominated solutions, meaning none is strictly better than another"
- Clarify trade-offs between objectives: energy vs cost vs CO2 vs comfort
- Recommend solutions based on user priorities
- Use MCDM methods (ASF, pseudo-weights, weighted scores) to justify rankings
"""

SYSTEM_PROMPT_TECHNICAL = """
Current focus: TECHNICAL MODE

Answer methodology questions with appropriate depth.
- Explain MTL architecture and why it works for building prediction
- Describe NSGA-II algorithm and constraint handling
- Discuss climate scenarios (2020, 2050, 2100) and their implications
- Reference relevant documentation when available
"""


def build_system_prompt(
    context: Optional[SessionContext] = None,
    rag_documents: Optional[List[Dict[str, Any]]] = None,
    mode: str = "general"
) -> str:
    """Build complete system prompt with context.

    Args:
        context: Session context with current state
        rag_documents: Retrieved documentation chunks
        mode: Conversation mode (general, navigation, interpretation, technical)

    Returns:
        Complete system prompt string
    """
    parts = [SYSTEM_PROMPT_BASE]

    # Add mode-specific prompt
    mode_prompts = {
        "navigation": SYSTEM_PROMPT_NAVIGATION,
        "interpretation": SYSTEM_PROMPT_INTERPRETATION,
        "technical": SYSTEM_PROMPT_TECHNICAL,
    }
    if mode in mode_prompts:
        parts.append(mode_prompts[mode])

    # Add session context
    if context:
        parts.append(_format_session_context(context))

    # Add RAG context
    if rag_documents:
        parts.append(_format_rag_context(rag_documents))

    return "\n\n".join(parts)


def _format_session_context(context: SessionContext) -> str:
    """Format session context for system prompt."""
    lines = ["## Current Session State"]

    if context.current_stage:
        lines.append(f"- Current pipeline stage: {context.current_stage}")

    if context.building_id:
        lines.append(f"- Building ID: {context.building_id}")

    if context.design_variables:
        lines.append("- Design variables:")
        for key, value in context.design_variables.items():
            lines.append(f"  - {key}: {value}")

    if context.pareto_solutions:
        n_solutions = len(context.pareto_solutions)
        lines.append(f"- Pareto solutions available: {n_solutions}")

        # Summarize solution range
        if n_solutions > 0:
            solutions = context.pareto_solutions
            lines.append("- Solution ranges:")
            for metric in ["energy_savings", "cost", "co2_reduction", "comfort_score"]:
                values = [s.get(metric) for s in solutions if s.get(metric) is not None]
                if values:
                    lines.append(f"  - {metric}: {min(values):.1f} to {max(values):.1f}")

    if context.selected_solution:
        lines.append(f"- Currently selected solution: ID {context.selected_solution}")

    if context.optimization_constraints:
        lines.append("- Active constraints:")
        for key, value in context.optimization_constraints.items():
            lines.append(f"  - {key}: {value}")

    return "\n".join(lines)


def _format_rag_context(documents: List[Dict[str, Any]]) -> str:
    """Format RAG documents for system prompt."""
    if not documents:
        return ""

    lines = ["## Relevant Documentation"]

    for i, doc in enumerate(documents, 1):
        source = doc.get("metadata", {}).get("source", "Unknown")
        section = doc.get("metadata", {}).get("section", "")
        text = doc.get("text", "")

        # Truncate long documents
        if len(text) > 500:
            text = text[:500] + "..."

        lines.append(f"\n### Source {i}: {source}")
        if section:
            lines.append(f"Section: {section}")
        lines.append(text)

    return "\n".join(lines)


def get_interpretation_prompt(
    solution_type: str,
    solutions: List[Dict[str, Any]]
) -> str:
    """Get prompt for specific solution interpretation.

    Args:
        solution_type: Type of interpretation needed
        solutions: Solutions to interpret

    Returns:
        Interpretation guidance prompt
    """
    prompts = {
        "pareto_overview": """
Explain this Pareto front to the user:
- How many solutions are on the front
- The range of each objective
- Key trade-off patterns (e.g., "high energy savings solutions cost 2-3x more")
- Suggest which solutions to explore based on common priorities
""",
        "solution_comparison": """
Compare these specific solutions:
- Quantify differences in each objective
- Highlight the key trade-off (what you gain vs. what you give up)
- Make a recommendation based on typical priorities
- Mention payback period if cost data is available
""",
        "mcdm_ranking": """
Explain the MCDM ranking:
- Which method was used (ASF, pseudo-weights, or weighted scores)
- Why the top solution ranks highest
- How sensitive the ranking is to weight changes
- Alternative solutions that might be preferred with different priorities
""",
        "climate_comparison": """
Compare results across climate scenarios:
- How objectives change from 2020 to 2050 to 2100
- Which retrofit measures become more/less valuable
- Climate adaptation recommendations
"""
    }

    return prompts.get(solution_type, prompts["pareto_overview"])


def get_error_recovery_prompt(error_type: str) -> str:
    """Get prompt for handling errors gracefully.

    Args:
        error_type: Type of error encountered

    Returns:
        Error recovery guidance
    """
    error_prompts = {
        "no_pareto_solutions": """
The user is asking about Pareto solutions, but none are available yet.
Explain that they need to:
1. First run inference to predict building performance
2. Then run NSGA-II optimization to generate the Pareto front
Offer to help them start the optimization process.
""",
        "optimization_timeout": """
The optimization is taking longer than expected.
Explain that:
1. NSGA-II optimization typically takes 30-60 seconds
2. They can check the job status using the job_id
3. Complex problems with many constraints may take longer
Offer to check the current job status.
""",
        "invalid_design_variables": """
The user specified invalid design variables.
Clarify the valid ranges:
- Windows U-factor: 0.8-5.0 W/m²K
- Wall insulation R-value: 1-10 m²K/W
- Roof insulation R-value: 1-10 m²K/W
- HVAC efficiency (COP): 2-5
Ask them to provide corrected values.
""",
        "no_similar_buildings": """
No similar buildings were found in the case study database.
Explain that:
1. The RAG database contains pre-computed scenarios
2. Their specific building characteristics may not have direct matches
3. Offer to run fresh inference/optimization for their building
"""
    }

    return error_prompts.get(error_type, "An unexpected error occurred. Please try again or rephrase your request.")


CONVERSATION_STARTERS = [
    "What would you like to optimize for your building?",
    "I can help you find the best retrofit solution. What are your priorities - energy savings, cost, or comfort?",
    "Would you like to see similar buildings and their retrofit results?",
    "I can explain the trade-offs between different solutions. Which aspect interests you most?",
]


def get_conversation_starter(context: Optional[SessionContext] = None) -> str:
    """Get appropriate conversation starter based on context.

    Args:
        context: Current session context

    Returns:
        Appropriate greeting/starter message
    """
    if not context:
        return "Hello! I'm Isabella, your building retrofit optimization assistant. How can I help you today?"

    if context.pareto_solutions:
        n = len(context.pareto_solutions)
        return f"Welcome back! You have {n} Pareto-optimal solutions from your last optimization. Would you like me to help you compare them or find the best fit for your priorities?"

    if context.current_stage:
        stage_starters = {
            "data_loading": "I see you're at the data loading stage. Need help importing your building data?",
            "inference": "Ready to predict building performance? I can run inference with your design variables.",
            "optimization": "Time to find optimal solutions! What constraints should I apply to the optimization?",
            "mcdm": "Let's rank your Pareto solutions. What matters most - energy savings, cost, CO2, or comfort?",
        }
        return stage_starters.get(context.current_stage, CONVERSATION_STARTERS[0])

    return CONVERSATION_STARTERS[0]
