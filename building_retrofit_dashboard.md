## Final Plan Summary

### Phase 0: Docker (Isabella2)

- Create `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.dockerignore`
- Run API on port 8000

### Phase 1: Verify Backend

- Existing endpoints: `/api/inference`, `/api/optimize`, `/api/mcdm`
- No changes needed to `api/server.py`

### Phases 2-4: Frontend (dt-generic-cesium)

**12 files to create/modify:**

| Component | Purpose |
| --- | --- |
| `retrofitInputStore.ts` | Scenario state management |
| `RetrofitPresetService.ts` | Preset configurations |
| `ScenarioTabs.svelte` | A, B, C, D scenario tabs |
| `DesignVariableSliders.svelte` | 4 input sliders |
| `TimeHorizonPicker.svelte` | 2020/2050/2100 selector |
| `PredictionsTable.svelte` | Scenario comparison table |
| `TopRecommendations.svelte` | Top 3 solution cards |
| `MCDMWeightSliders.svelte` | 4 weight sliders |
| `ParetoFrontier.svelte` | Enhance with click-to-select |
| `RetrofitDetailed.svelte` | Main component |

### Success Criteria

1. Docker runs API on port 8000
2. Compare multiple scenarios (A, B, C, D)
3. Predictions in <1 second
4. Pareto optimization in <30 seconds
5. MCDM weights re-rank in real-time
6. 3D building coloring
7. Export to CSV

**Claude’s Plan**

# Isabella2 Retrofit Optimization Dashboard - Unified Plan

## Architecture Overview

`┌────────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM ARCHITECTURE                                    │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│   dt-generic-cesium (Svelte)              Isabella2 (Docker)                       │
│   ┌─────────────────────────┐             ┌─────────────────────────┐             │
│   │  LEFT PANEL             │             │  FastAPI Server         │             │
│   │  - Scenario Tabs A,B,C  │             │  ├─ /api/inference      │             │
│   │  - Design Sliders       │  HTTP/JSON  │  ├─ /api/optimize       │             │
│   │  - Presets              │ ◄─────────► │  ├─ /api/mcdm           │             │
│   │                         │             │  │                      │             │
│   │  RIGHT PANEL            │             │  ├─ MTL Model (PyTorch) │             │
│   │  - Predictions Table    │             │  └─ NSGA-II (pymoo)     │             │
│   │  - Pareto Chart         │             │                         │             │
│   │  - MCDM Weights         │             │                         │             │
│   │  - Top 3 Solutions      │             │                         │             │
│   │                         │             └─────────────────────────┘             │
│   │  MIDDLE: Cesium 3D Map  │                                                      │
│   └─────────────────────────┘                                                      │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘`

---

## Phase 0: Dockerize Isabella2 API (DO FIRST)

### Files to Create in `D:\__desktop\Isabella\Isa\Isabella2\`

**0.1 Create `Dockerfile`**

`FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY src/ ./src/
COPY utils/ ./utils/
COPY models/ ./models/
COPY scalers/ ./scalers/

EXPOSE 8000

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]`

**0.2 Create `docker-compose.yml`**

`version: '3.8'
services:
  isabella2-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - ./scalers:/app/scalers
    environment:
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3`

**0.3 Create `requirements.txt`**

`fastapi>=0.104.0
uvicorn>=0.24.0
torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
joblib>=1.3.0
pydantic>=2.0.0
pymoo>=0.6.0`

**0.4 Create `.dockerignore`**

`__pycache__/
*.pyc
.git/
.env
*.md
inputs/
ARCHIEVE/
.pytest_cache/`

### Docker Commands

`# Build and run
docker-compose up -d

# Verify
curl http://localhost:8000/api/health`

---

## Phase 1: Verify Backend API

### File: `api/server.py` (EXISTS - no changes needed)

Existing endpoints to use:

- `GET /api/health` - Check API status
- `POST /api/inference` - ML predictions
- `POST /api/optimize` - NSGA-II Pareto optimization
- `POST /api/mcdm` - Multi-criteria ranking

**Note:** LLM integration deferred to future phase.

---

## Phase 2: Frontend Component Architecture

### Location: `D:\Documents\Stefan_21\dt-generic-cesium\src\lib\components\Tools\RetrofitDetailed\`

`RetrofitDetailed/
├── RetrofitDetailed.svelte              # Main container (ENHANCE)
├── stores/
│   ├── retrofitInputStore.ts            # NEW: Scenarios + inputs
│   ├── retrofitResultsStore.ts          # EXISTS: Predictions
│   └── paretoStore.ts                   # EXISTS: Pareto solutions
├── services/
│   ├── Isabella2APIService.ts           # EXISTS: API client
│   └── RetrofitPresetService.ts         # NEW: Preset configurations
├── components/
│   ├── scenarios/
│   │   ├── ScenarioTabs.svelte          # NEW: A, B, C, D tabs
│   │   └── ScenarioEditor.svelte        # NEW: Single scenario form
│   ├── inputs/
│   │   ├── PresetSelector.svelte        # NEW: Preset dropdown
│   │   ├── DesignVariableSliders.svelte # NEW: 5 input sliders
│   │   └── TimeHorizonPicker.svelte     # NEW: 2020/2050/2100
│   ├── dashboard/
│   │   ├── PredictionsTable.svelte      # NEW: Comparison table
│   │   ├── MetricCardGrid.svelte        # NEW: 4 KPI cards
│   │   └── RetrofitMetricCard.svelte    # NEW: Single metric card
│   └── optimization/
│       ├── ParetoControls.svelte        # NEW: Run optimization
│       ├── MCDMWeightSliders.svelte     # NEW: 4 weight sliders
│       └── TopRecommendations.svelte    # NEW: Top 3 solution cards
└── charts/
    └── ParetoFrontier.svelte            # EXISTS: Enhance interactivity`

---

## Phase 3: UI Layout

### Left Panel - Scenario Input

`┌─────────────────────────────────────────────────────────────────┐
│  SCENARIOS                                              [+ Add] │
├─────────────────────────────────────────────────────────────────┤
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│   │    A    │ │    B    │ │    C    │ │    D    │              │
│   │ Baseline│ │  Basic  │ │  Deep   │ │ Custom  │              │
│   │  ● sel  │ │    ○    │ │    ○    │ │    ○    │              │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘              │
├─────────────────────────────────────────────────────────────────┤
│  ▼ SCENARIO A: Baseline                              [Rename]   │
│                                                                 │
│  Climate: [2020 ●] [2050 ○] [2100 ○]                           │
│                                                                 │
│  🪟 Windows U-Factor (W/m²K)                                    │
│  [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓●░░░░░░░░░░░░░] 1.5                          │
│  0.8                              2.9                           │
│                                                                 │
│  🏠 Floor R-Value (m²K/W)                                       │
│  [▓▓▓▓▓▓●░░░░░░░░░░░░░░░░░░░░░░░] 2.0                          │
│  0.4                              5.6                           │
│                                                                 │
│  🧱 Wall R-Value (m²K/W)                                        │
│  [▓▓▓▓▓▓▓▓▓▓●░░░░░░░░░░░░░░░░░░░] 3.5                          │
│  0.5                              6.7                           │
│                                                                 │
│  🏚️ Roof R-Value (m²K/W)                                        │
│  [▓▓▓▓▓▓▓▓▓▓▓▓▓●░░░░░░░░░░░░░░░░] 4.5                          │
│  0.5                              8.7                           │
│                                                                 │
│  PRESETS: [Baseline] [Basic] [Deep]                             │
├─────────────────────────────────────────────────────────────────┤
│  [🔮 RUN PREDICTIONS FOR ALL]                                   │
│  [⚡ RUN PARETO OPTIMIZATION]                                   │
└─────────────────────────────────────────────────────────────────┘`

### Right Panel - Results Dashboard

`┌─────────────────────────────────────────────────────────────────┐
│  PREDICTIONS COMPARISON                                         │
├─────────────────────────────────────────────────────────────────┤
│  │ Scenario │ Energy  │  Cost   │   CO2   │ Comfort │          │
│  ├──────────┼─────────┼─────────┼─────────┼─────────┤          │
│  │ A Base   │  65 🔴  │    €0   │  3,200  │  220 🔴 │          │
│  │ B Basic  │  45 🟡  │ €12,000 │  2,300  │  285 🟡 │          │
│  │ C Deep   │  32 🟢  │ €25,000 │  1,500  │  340 🟢 │          │
├─────────────────────────────────────────────────────────────────┤
│  PARETO OPTIMIZATION              [2D ●] [3D ○] [Table ○]      │
│  X: [Energy ▼]  Y: [Cost ▼]  Color: [CO2 ▼]                    │
│                                                                 │
│     Cost €                                                      │
│       ▲         ○  ○                                           │
│  30k  │      ○  ○  ○                                           │
│  20k  │   ●  ○  ○       ● = Selected                           │
│  10k  │○  ○  ○          ○ = Pareto optimal                     │
│       └──────────────────► Energy (GJ)                         │
│         25   35   45   55                                       │
├─────────────────────────────────────────────────────────────────┤
│  MCDM WEIGHTS                                                   │
│  ⚡ Energy  [████████████████░░░░░░░░░░░░░░] 30%                │
│  💰 Cost    [████████░░░░░░░░░░░░░░░░░░░░░░] 20%                │
│  🌱 CO2     [████████████░░░░░░░░░░░░░░░░░░] 25%                │
│  😊 Comfort [████████████░░░░░░░░░░░░░░░░░░] 25%                │
│                                                                 │
│  Presets: [Balanced] [Cost Focus] [Green] [Comfort]             │
├─────────────────────────────────────────────────────────────────┤
│  TOP RECOMMENDATIONS                                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ 🥇 BEST     │ │ 🥈 CHEAPEST │ │ 🥉 GREENEST │               │
│  │ Score: 0.87 │ │ Score: 0.79 │ │ Score: 0.82 │               │
│  │ Energy: 35  │ │ Energy: 42  │ │ Energy: 30  │               │
│  │ Cost: €15k  │ │ Cost: €8.5k │ │ Cost: €22k  │               │
│  │ [SELECT]    │ │ [SELECT]    │ │ [SELECT]    │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│  [📍 APPLY TO BUILDING] [📥 Export CSV] [📊 Report]            │
└─────────────────────────────────────────────────────────────────┘`

## Phase 4: Implementation Steps

### Step 4.1: Create Stores

**`stores/retrofitInputStore.ts`**

`interface Scenario {
  id: string;           // 'A', 'B', 'C', 'D'
  name: string;         // 'Baseline', 'Basic Retrofit', etc.
  timeHorizon: 2020 | 2050 | 2100;
  designVariables: {
    windows_U_Factor: number;
    groundfloor_thermal_resistance: number;
    ext_walls_thermal_resistance: number;
    roof_thermal_resistance: number;
  };
  predictions?: {
    energy: number;
    cost: number;
    co2: number;
    comfort: number;
  };
}

// Store: scenarios[], activeScenarioId, isLoading`

### Step 4.2: Create Preset Service

**`services/RetrofitPresetService.ts`**

`export const PRESETS = {
  baseline: { windows: 2.9, floor: 0.41, walls: 0.45, roof: 0.48 },
  basic:    { windows: 2.0, floor: 1.5,  walls: 1.5,  roof: 2.0  },
  standard: { windows: 1.5, floor: 3.0,  walls: 3.0,  roof: 4.0  },
  deep:     { windows: 0.9, floor: 5.0,  walls: 6.0,  roof: 8.0  }
};

export const MCDM_PRESETS = {
  balanced:  { energy: 0.25, cost: 0.25, co2: 0.25, comfort: 0.25 },
  costFocus: { energy: 0.20, cost: 0.50, co2: 0.20, comfort: 0.10 },
  green:     { energy: 0.30, cost: 0.10, co2: 0.40, comfort: 0.20 },
  comfort:   { energy: 0.20, cost: 0.10, co2: 0.20, comfort: 0.50 }
};`

### Step 4.3: Create Input Components

1. **ScenarioTabs.svelte** - Tab bar with A, B, C, D + Add button
2. **DesignVariableSliders.svelte** - 4 sliders with labels
3. **TimeHorizonPicker.svelte** - ContentSwitcher for 2020/2050/2100
4. **PresetSelector.svelte** - Dropdown with preset options

### Step 4.4: Create Dashboard Components

1. **PredictionsTable.svelte** - DataTable comparing all scenarios
2. **MetricCardGrid.svelte** - 2x2 grid of metric cards
3. **TopRecommendations.svelte** - Top 3 solution cards

### Step 4.5: Create Optimization Components

1. **ParetoControls.svelte** - Settings + Run button
2. **MCDMWeightSliders.svelte** - 4 normalized sliders
3. **Enhance ParetoFrontier.svelte** - Click to select solution

### Step 4.6: Enhance Main Component

**RetrofitDetailed.svelte** - Compose all components:

- Left panel: ScenarioTabs + ScenarioEditor
- Right panel: Dashboard + Pareto + MCDM + Recommendations

---

## Phase 5: Files Summary

| File | Action | Priority |
| --- | --- | --- |
| `Dockerfile` | CREATE | P0 |
| `docker-compose.yml` | CREATE | P0 |
| `stores/retrofitInputStore.ts` | CREATE | P1 |
| `services/RetrofitPresetService.ts` | CREATE | P1 |
| `components/scenarios/ScenarioTabs.svelte` | CREATE | P1 |
| `components/inputs/DesignVariableSliders.svelte` | CREATE | P1 |
| `components/inputs/TimeHorizonPicker.svelte` | CREATE | P1 |
| `components/dashboard/PredictionsTable.svelte` | CREATE | P1 |
| `components/dashboard/TopRecommendations.svelte` | CREATE | P1 |
| `components/optimization/MCDMWeightSliders.svelte` | CREATE | P1 |
| `charts/ParetoFrontier.svelte` | MODIFY | P1 |
| `RetrofitDetailed.svelte` | MODIFY | P1 |

---

## API Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/health` | GET | Check API status |
| `/api/inference` | POST | Get predictions for design variables |
| `/api/optimize` | POST | Run NSGA-II Pareto optimization |
| `/api/mcdm` | POST | Rank solutions with weights |

---

## Data Flow

`Scenario Tabs → retrofitInputStore → Isabella2API.inference() → PredictionsTable
                                                              → MetricCardGrid
                     ↓
Run Optimize → Isabella2API.optimize() → paretoStore → ParetoFrontier
                                                     → TopRecommendations
                     ↓
MCDM Weights → Isabella2API.mcdm() → Re-ranked solutions
                     ↓
Select Solution → retrofitInputStore → Sliders updated → 3D building colored`

---

## Success Criteria

- [ ]  Docker container runs Isabella2 API on port 8000
- [ ]  User can create/compare multiple scenarios (A, B, C, D)
- [ ]  Predictions appear in <1 second
- [ ]  Pareto optimization completes in <30 seconds
- [ ]  MCDM weights re-rank solutions in real-time
- [ ]  Top 3 recommendations update based on weights
- [ ]  3D buildings colored based on selected metric
- [ ]  Export to CSV works

---

## Quick Start

`# Terminal 1: Start Isabella2 API (Docker)
cd D:\__desktop\Isabella\Isa\Isabella2
docker-compose up -d

# Terminal 2: Start Frontend
cd D:\Documents\Stefan_21\dt-generic-cesium
npm run dev

# Verify API
curl http://localhost:8000/api/health`













































# Plan 1



# Retrofit Analysis UI - Implementation Plan

## Overview

Build a focused Retrofit Analysis interface in the Cesium digital twin application that uses pre-trained Isabella2 ML models to predict building retrofit performance.

**Target Location:** `D:\Documents\Stefan_21\dt-generic-cesium\src\lib\components\Tools\RetrofitDetailed\`

**Backend:** Isabella2 FastAPI (Dockerized)

---

## Phase 0: Dockerize Isabella2 API (DO THIS FIRST)

### Files to Create in Isabella2 Project

**0.1 Create `Dockerfile`**

`FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY src/ ./src/
COPY utils/ ./utils/
COPY models/ ./models/
COPY scalers/ ./scalers/

# Expose port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]`

**0.2 Create `docker-compose.yml`**

`version: '3.8'
services:
  isabella2-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models      # Hot-reload models
      - ./scalers:/app/scalers    # Hot-reload scalers
    environment:
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3`

**0.3 Create `requirements.txt`** (if not complete)

`fastapi>=0.104.0
uvicorn>=0.24.0
torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
joblib>=1.3.0
pydantic>=2.0.0
pymoo>=0.6.0`

**0.4 Create `.dockerignore`**

`__pycache__/
*.pyc
.git/
.env
*.md
inputs/
ARCHIEVE/
.pytest_cache/`

### Docker Commands

`# Build the image
docker build -t isabella2-api .

# Run the container
docker run -p 8000:8000 isabella2-api

# Or use docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down`

### Verify API Works

`# Health check
curl http://localhost:8000/api/health

# Test inference
curl -X POST http://localhost:8000/api/inference \
  -H "Content-Type: application/json" \
  -d '{"method":"uncertainty","model_type":"Data_Based_Isa","design_variables":[{"time_horizon":2020,"windows_U_Factor":2.0,"groundfloor_thermal_resistance":1.5,"ext_walls_thermal_resistance":1.5,"roof_thermal_resistance":2.0}]}'`

---

---

## Component Architecture

`RetrofitDetailed/
├── RetrofitDetailed.svelte          # Main container (ENHANCE)
├── stores/
│   └── retrofitInputStore.ts        # NEW: Input/preset state
├── services/
│   └── RetrofitPresetService.ts     # NEW: Preset configurations
├── components/
│   ├── inputs/
│   │   ├── PresetSelector.svelte    # NEW: Scenario dropdown
│   │   ├── DesignVariableSliders.svelte # NEW: 5 input sliders
│   │   └── TimeHorizonPicker.svelte # NEW: Climate year selector
│   ├── dashboard/
│   │   ├── MetricCardGrid.svelte    # NEW: 4 KPI cards layout
│   │   └── RetrofitMetricCard.svelte # NEW: Single metric with bar
│   └── optimization/
│       ├── ParetoControls.svelte    # NEW: Optimization trigger
│       ├── MCDMWeightSliders.svelte # NEW: 4 weight sliders
│       └── SolutionRankingList.svelte # NEW: Ranked solutions
└── charts/
    └── ParetoFrontier.svelte        # EXISTS - enhance`

---

## Implementation Steps

### Phase 1: Foundation (Store & Presets)

**1.1 Create `retrofitInputStore.ts`**

- Store design variable values (5 inputs)
- Track selected preset (basic/standard/deep/custom)
- Store baseline for comparison
- Track predictions and loading state

**1.2 Create `RetrofitPresetService.ts`** Define 3 preset configurations:

`basic:    { windows: 2.0, floor: 1.5, walls: 1.5, roof: 2.0 }  // Minimal
standard: { windows: 1.5, floor: 3.0, walls: 3.0, roof: 4.0 }  // Balanced
deep:     { windows: 0.9, floor: 5.0, walls: 6.0, roof: 8.0 }  // Maximum`

---

### Phase 2: Input Components

**2.1 Create `PresetSelector.svelte`**

- Carbon Dropdown with 4 options
- On select → fill sliders from preset
- Auto-switch to "Custom" when sliders adjusted

**2.2 Create `DesignVariableSliders.svelte`** 5 sliders with ranges:

| Variable | Range | Unit |
| --- | --- | --- |
| windows_U_Factor | 0.8 - 2.9 | W/m²K |
| groundfloor_thermal_resistance | 0.41 - 5.6 | m²K/W |
| ext_walls_thermal_resistance | 0.45 - 6.7 | m²K/W |
| roof_thermal_resistance | 0.48 - 8.7 | m²K/W |

**2.3 Create `TimeHorizonPicker.svelte`**

- Carbon ContentSwitcher: 2020 / 2050 / 2100
- Climate scenario descriptions

---

### Phase 3: Dashboard Components

**3.1 Create `RetrofitMetricCard.svelte`** Each card shows:

- Icon + Title (Energy, Cost, CO2, Comfort)
- Large value with unit
- Mini horizontal bar (position in typical range)
- Comparison to baseline (% change, color-coded)

**3.2 Create `MetricCardGrid.svelte`**

- 2x2 responsive grid
- Loading skeleton state
- Pass current + baseline values to cards

---

### Phase 4: Optimization Components

**4.1 Create `ParetoControls.svelte`**

- "Find Optimal Solutions" button
- Settings: generations (10-500), population (20-200)
- Progress indicator during optimization

**4.2 Create `MCDMWeightSliders.svelte`**

- 4 sliders: Energy, Cost, CO2, Comfort weights
- Auto-normalize to 100%
- Real-time re-ranking

**4.3 Create `SolutionRankingList.svelte`**

- Carbon DataTable with ranked solutions
- Click row → fill input sliders
- "Apply Solution" button

---

### Phase 5: Main Component Enhancement

**Enhance `RetrofitDetailed.svelte`**

- Section 1: Design Input (presets + sliders + predict button)
- Section 2: Results Dashboard (4 metric cards + comparison)
- Section 3: Optimization (Pareto + MCDM + ranking)

---

### Phase 6: Map Integration

**Enhance `retrofit-model-handler.ts`**

- Listen for Cesium building selection
- Pre-fill inputs from building properties
- Associate results with selected building
- Color building based on selected metric

---

## Key Files to Modify/Create

| File | Action |
| --- | --- |
| `stores/retrofitInputStore.ts` | CREATE |
| `services/RetrofitPresetService.ts` | CREATE |
| `components/inputs/PresetSelector.svelte` | CREATE |
| `components/inputs/DesignVariableSliders.svelte` | CREATE |
| `components/inputs/TimeHorizonPicker.svelte` | CREATE |
| `components/dashboard/MetricCardGrid.svelte` | CREATE |
| `components/dashboard/RetrofitMetricCard.svelte` | CREATE |
| `components/optimization/ParetoControls.svelte` | CREATE |
| `components/optimization/MCDMWeightSliders.svelte` | CREATE |
| `components/optimization/SolutionRankingList.svelte` | CREATE |
| `RetrofitDetailed.svelte` | ENHANCE |
| `retrofit-model-handler.ts` | ENHANCE |

---

## API Endpoints Used

| Endpoint | Purpose |
| --- | --- |
| `POST /api/inference` | ML predictions for design variables |
| `POST /api/optimize` | NSGA2 Pareto optimization |
| `POST /api/mcdm` | Multi-criteria ranking |
| `GET /api/health` | Backend availability check |

---

## Data Flow

`User Input → retrofitInputStore → Isabella2API.predict() → MetricCardGrid
                                         ↓
User Optimize → Isabella2API.optimize() → paretoStore → ParetoFrontier
                                                      → SolutionRankingList
                                         ↓
User MCDM Weights → Isabella2API.mcdm() → Re-ranked solutions
                                         ↓
User Select Solution → retrofitInputStore → Sliders updated`

---

## Prerequisites

1. Isabella2 API server running at `localhost:8000`
2. Pre-trained models in `Isabella2/models/` folder
3. Scalers in `Isabella2/scalers/` folder











# Plan 2

 Building Retrofit Optimization Dashboard

```

## DATA FLOW

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                    USER WORKFLOW                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

   STEP 1                    STEP 2                    STEP 3                    STEP 4
   ───────                   ───────                   ───────                   ───────
                                                       
┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  Define      │        │  Run         │        │  Optimize    │        │  Select &    │
│  Scenarios   │   ──►  │  Predictions │   ──►  │  + MCDM      │   ──►  │  Apply       │
│  A, B, C...  │        │              │        │              │        │              │
└──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
       │                       │                       │                       │
       ▼                       ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ Set sliders  │        │ API:         │        │ API:         │        │ Show on map  │
│ for each     │        │ /inference   │        │ /optimize    │        │ Export data  │
│ scenario     │        │              │        │ /mcdm        │        │              │
└──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
```

## SCENARIO COMPARISON DETAIL (Left Panel)

```
┌─────────────────────────────────────────────────────────────────┐
│  SCENARIOS                                              [+ Add] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│   │    A    │ │    B    │ │    C    │ │    D    │              │
│   │ Baseline│ │  Basic  │ │  Deep   │ │ Custom  │              │
│   │         │ │ Retrofit│ │ Retrofit│ │         │              │
│   │  ✓ ●    │ │    ○    │ │    ○    │ │    ○ ✕  │              │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘              │
│     active                                         can delete   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ▼ SCENARIO A: Baseline                              [Rename]   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Climate Scenario                                         │  │
│  │                                                           │  │
│  │    ┌──────────┐   ┌──────────┐   ┌──────────┐            │  │
│  │    │   2020   │   │   2050   │   │   2100   │            │  │
│  │    │  ● Now   │   │  ○ Mid   │   │  ○ Late  │            │  │
│  │    │   +0°C   │   │  +1.5°C  │   │  +3.0°C  │            │  │
│  │    └──────────┘   └──────────┘   └──────────┘            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │  🪟 Windows U-Factor                                      │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓●░░░░░░░░░░░░░░░░░░░░░░░░░░░░│  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  Poor 0.5                    ● 1.5              3.0 Good  │  │
│  │                                                 W/m²K     │  │
│  │                                                           │  │
│  │  🏠 Floor Thermal Resistance                              │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ ▓▓▓▓▓▓▓●░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  Poor 0.3            ● 2.0                      6.0 Good  │  │
│  │                                                 m²K/W     │  │
│  │                                                           │  │
│  │  🧱 Wall Thermal Resistance                               │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓●░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  Poor 0.3                   ● 3.5               7.0 Good  │  │
│  │                                                 m²K/W     │  │
│  │                                                           │  │
│  │  🏚️ Roof Thermal Resistance                               │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓●░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  Poor 0.3                       ● 4.5           9.0 Good  │  │
│  │                                                 m²K/W     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  QUICK PRESETS                                            │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │  Baseline  │ │   Basic    │ │    Deep    │            │  │
│  │  │  (as-is)   │ │  Retrofit  │ │  Retrofit  │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🔮  RUN PREDICTIONS FOR ALL SCENARIOS                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ⚡  RUN PARETO OPTIMIZATION                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## RIGHT PANEL DASHBOARD DETAIL

```
┌─────────────────────────────────────────────────────────────────┐
│  PREDICTIONS COMPARISON                               [Chart ▼] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Scenario │  Energy   │   Cost    │   CO2     │  Comfort   │  │
│  │          │  (GJ/yr)  │   (EUR)   │   (kg)    │  (days)    │  │
│  ├──────────┼───────────┼───────────┼───────────┼────────────┤  │
│  │ A Base   │    65 🔴  │      €0   │   3,200   │    220 🔴  │  │
│  │ B Basic  │    45 🟡  │  €12,000  │   2,300   │    285 🟡  │  │
│  │ C Deep   │    32 🟢  │  €25,000  │   1,500   │    340 🟢  │  │
│  │ D Custom │    28 🟢  │  €32,000  │   1,200   │    355 🟢  │  │
│  └──────────┴───────────┴───────────┴───────────┴────────────┘  │
│                                                                 │
│         A ████████████████████████████████████████ 65 GJ        │
│         B ██████████████████████████░░░░░░░░░░░░░ 45 GJ (-31%)  │
│         C ████████████████░░░░░░░░░░░░░░░░░░░░░░░ 32 GJ (-51%)  │
│         D ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░ 28 GJ (-57%)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PARETO OPTIMIZATION                        [2D] [3D] [Table]   │
├─────────────────────────────────────────────────────────────────┤
│  X-Axis: [Energy ▼]  Y-Axis: [Cost ▼]  Color: [CO2 ▼]          │
│                                                                 │
│     Cost (€)                                                    │
│       ▲                                                         │
│  35k  │                                          ○              │
│       │                                       ○                 │
│  30k  │                                    ○                    │
│       │                                 ○  ○                    │
│  25k  │                              ○  ○                       │
│       │                           ○  ○                          │
│  20k  │                        ●  ○                             │
│       │                     ○  ○          ● = Selected          │
│  15k  │                  ○  ○             ○ = Pareto optimal    │
│       │               ○  ○                                      │
│  10k  │            ○  ○                   Color: CO2 level      │
│       │         ○  ○                      🟢 Low  🟡 Med  🔴 High │
│   5k  │      ○                                                  │
│       │                                                         │
│       └──────────────────────────────────────────► Energy       │
│            25    30    35    40    45    50    55    60  (GJ)   │
│                                                                 │
│  📊 47 Pareto-optimal solutions found | Generation: 100/100     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  DECISION WEIGHTS (MCDM)                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  How important is each objective to you?                        │
│                                                                 │
│  ⚡ Energy    [████████████████████░░░░░░░░░░░░░░░░░░░] 30%     │
│  💰 Cost      [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 20%     │
│  🌱 CO2       [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░] 25%     │
│  😊 Comfort   [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░] 25%     │
│                                                    Total: 100%  │
│                                                                 │
│  Quick Presets:                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Balanced │ │   Cost   │ │  Green   │ │ Comfort  │           │
│  │  25/25/  │ │  Focus   │ │ Priority │ │  First   │           │
│  │  25/25   │ │  10/50/  │ │  20/10/  │ │  20/20/  │           │
│  │    ●     │ │  20/20   │ │  50/20   │ │  10/50   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TOP RECOMMENDATIONS                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────┐ ┌───────────────────┐ ┌─────────────────┐│
│  │  🥇 #1 BEST       │ │  🥈 #2 LOWEST     │ │  🥉 #3 GREENEST ││
│  │     OVERALL       │ │     COST          │ │                 ││
│  │                   │ │                   │ │                 ││
│  │  Score: 0.87      │ │  Score: 0.79      │ │  Score: 0.82    ││
│  │  ─────────────    │ │  ─────────────    │ │  ─────────────  ││
│  │  Energy:  35 GJ   │ │  Energy:  42 GJ   │ │  Energy:  30 GJ ││
│  │  Cost:    €15,200 │ │  Cost:    €8,500  │ │  Cost:    €22k  ││
│  │  CO2:     1,800kg │ │  CO2:     2,100kg │ │  CO2:     1,400 ││
│  │  Comfort: 320 days│ │  Comfort: 290 days│ │  Comfort: 345d  ││
│  │  ─────────────    │ │  ─────────────    │ │  ─────────────  ││
│  │  U-Factor:  1.2   │ │  U-Factor:  1.8   │ │  U-Factor:  0.9 ││
│  │  Floor R:   3.5   │ │  Floor R:   2.0   │ │  Floor R:   4.5 ││
│  │  Wall R:    4.2   │ │  Wall R:    2.8   │ │  Wall R:    5.5 ││
│  │  Roof R:    5.0   │ │  Roof R:   3.2    │ │  Roof R:    6.5 ││
│  │                   │ │                   │ │                 ││
│  │  [ ✓ SELECT ]     │ │  [   SELECT   ]   │ │  [   SELECT   ] ││
│  └───────────────────┘ └───────────────────┘ └─────────────────┘│
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  📍 APPLY TO BUILDING                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────┐ ┌─────────────────────────────┐   │
│  │  📥 Export CSV          │ │  📊 Generate Full Report    │   │
│  └─────────────────────────┘ └─────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Summary

| Panel  | Contents |
|--------|----------|
| LEFT   | Scenario tabs (A,B,C,D) + Sliders + Presets + Run buttons |
| MIDDLE | Cesium 3D Map (you handle) |
| RIGHT  | Predictions table + Pareto chart + MCDM weights + Top 3 cards + Export |
