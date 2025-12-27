# RetrofitDetailed Tool - Comprehensive Audit Report

**Date:** 2025-12-26
**Auditor:** Claude Code
**Tool Location:** `D:\Documents\Stefan_21\dt-generic-cesium\src\lib\components\Tools\RetrofitDetailed`

---

## Executive Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 5 |
| MEDIUM | 8 |
| LOW | 6 |
| **Total** | **20** |

---

## CRITICAL BUGS

### 1. MetricsTab crashes with undefined scenarios
**File:** `dashboard/tabs/MetricsTab.svelte:62,83`
**Error:** `Cannot read properties of undefined (reading 'map')`
**Root Cause:** When `scenarios` prop is undefined, the filter operation fails

```typescript
// Line 49 - crashes if scenarios is undefined
$: availableScenarios = scenarios.filter((s) => s.predictions);

// Line 62 - crashes if availableScenarios is undefined
const values = availableScenarios.map((s) => s.predictions?.[key] ?? 0);
```

**Fix Required:**
```typescript
$: availableScenarios = (scenarios ?? []).filter((s) => s.predictions);
```

---

## HIGH SEVERITY BUGS

### 2. Event Handler Mismatch (FIXED)
**File:** `sidebar-sections/RunControlsSection.svelte`
**Status:** Already fixed during this session
- Changed `runPredictions`/`runOptimization` to `run`
- Changed `openDashboard` to `openAnalysis`

### 3. Map Legend Overlaps Sidebar - Click Interception
**File:** CSS z-index issue
**Impact:** Users cannot click "Run Predictions" button without JavaScript workaround
**Root Cause:** Map legend element has higher z-index than sidebar

**Fix Required:** Add to RetrofitDetailed styles:
```css
.sidebar-content {
  position: relative;
  z-index: 100;
}
```

Or adjust map legend z-index in the parent component.

### 4. Constraint-Based UI Not Switching Properly
**File:** `RetrofitDetailed.svelte`
**Impact:** When switching to Constraint-Based mode, UI may not update to show constraint bounds
**Symptom:** Screenshot shows same UI as User-Driven mode

**Fix Required:** Verify reactive statement for `optimizationPath` properly triggers re-render.

### 5. HMR Error in MetricsTab
**Error:** `[HMR][Svelte] Unrecoverable HMR error in <MetricsTab>: next update will trigger a full reload`
**Impact:** Development experience degraded
**Root Cause:** Component state corruption during hot reload

---

## MEDIUM SEVERITY BUGS

### 6. 404 Resource Errors (2 occurrences)
**Console:** `Failed to load resource: the server responded with a status of 404 ()`
**Impact:** Missing assets/resources
**Fix Required:** Identify and fix missing resource paths

### 7. Invalid Domain Table XML (2 occurrences)
**Console:** `Invalid domain table XML`
**Impact:** Unknown - possibly affects map/GIS functionality
**Fix Required:** Investigate XML parsing issue

### 8. ScenarioImporter - Missing Download Link Implementation
**File:** `components/ScenarioImporter.svelte`
**Issue:** "Download Sample CSV" button may not have proper href

### 9. API Response Field Name Inconsistency
**Files:** `services/Isabella2APIService.ts`, `api/server.py`
**Issue:** Multiple field name aliases needed for same fields:
- `annual_energy_consumption_GJ` vs `annual_energy_GJ`
- `total_retrofit_cost_EUR` vs `total_cost_EUR`
- `total_co2_emission_kg` vs `total_co2_kg`

**Recommendation:** Standardize API response field names

### 10. Model Version Warning
**Console:** `InconsistentVersionWarning: Trying to unpickle estimator MinMaxScaler from version 1.5.2 when using version 1.7.2`
**Impact:** Potential prediction accuracy issues
**Fix Required:** Re-train and save scalers with current scikit-learn version

### 11. Plotly Type Casting Workarounds
**Files:** `charts/ParetoFrontier.svelte`, `charts/RetrofitComparisonChart.svelte`, `charts/CostBenefitScatter.svelte`
**Issue:** Using `(window as any).Plotly` and `(chartContainer as any).on()` casts
**Recommendation:** Add proper Plotly type definitions

### 12. Missing null checks in comparison metrics
**File:** `charts/RetrofitComparisonChart.svelte`
**Issue:** `outputs` may be undefined when accessed

### 13. Statistics calculation edge cases
**File:** `dashboard/tabs/MetricsTab.svelte`
**Issue:** Division by zero when `values.length === 0`:
```typescript
const avg = values.reduce((a, b) => a + b, 0) / values.length; // NaN if empty
```

---

## LOW SEVERITY / UI/UX ISSUES

### 14. Small Touch Targets
**Count:** 20+ buttons < 32px
**Impact:** Poor accessibility on touch devices
**WCAG Guideline:** Touch targets should be at least 44x44px
**Fix:** Increase button padding or min-width/height

### 15. Icon Sizes Non-Standard
**Files:** Various (fixed during session)
**Issue:** Used size 12, should use 16, 20, 24, or 32
**Status:** Fixed

### 16. Button Kind Naming
**Files:** Various (fixed during session)
**Issue:** Used "danger--tertiary" instead of "danger-tertiary"
**Status:** Fixed

### 17. Navigation Tree Depth Indicator
**Issue:** Current navigation position not clearly highlighted
**Recommendation:** Add active state styling to navigation items

### 18. No Loading State for Charts
**Impact:** Charts appear blank while loading
**Recommendation:** Add skeleton loaders or spinners

### 19. Console Log Not Capturing Activity
**Issue:** Console panel shows "No activity yet" even after predictions run
**Fix Required:** Ensure logStore properly updates console component

---

## UI/UX RECOMMENDATIONS

### A. Layout Improvements

1. **Sidebar Scrolling**
   - Sidebar content requires scrolling
   - Consider collapsible sections to reduce scroll
   - Add section indicators for long content

2. **Split Pane Responsiveness**
   - Test on smaller screens
   - Add minimum width constraints
   - Consider mobile layout

3. **Header Information Density**
   - Status indicators are small
   - Consider larger status badges with color coding

### B. Interaction Improvements

1. **Feedback on Actions**
   - Add toast notifications for success/error
   - Show progress indicators during API calls
   - Confirm destructive actions (reset, remove scenario)

2. **Keyboard Navigation**
   - Tab order should follow logical flow
   - Add keyboard shortcuts for common actions
   - Escape should close panels/modals

3. **Drag and Drop**
   - Allow reordering scenarios via drag
   - Support drag-drop CSV import

### C. Visual Design

1. **Color Consistency**
   - Use consistent color scheme for metrics
   - Energy: Blue, Cost: Gold, CO2: Green, Comfort: Purple

2. **Data Visualization**
   - Add legends to all charts
   - Consistent axis formatting
   - Hover states with detailed tooltips

3. **Empty States**
   - "No Results Yet" could be more informative
   - Add quick-start guide or tutorial link

### D. Accessibility

1. **Color Contrast**
   - Some secondary text may have low contrast
   - Test with contrast checker tool

2. **Screen Reader Support**
   - Add ARIA labels to interactive elements
   - Proper heading hierarchy

3. **Focus Indicators**
   - Ensure visible focus states on all interactive elements

---

## PRIORITY FIX ORDER

1. **CRITICAL:** MetricsTab undefined crash (blocks usage)
2. **HIGH:** Map legend z-index overlap (blocks interaction)
3. **HIGH:** Constraint-Based mode UI switch
4. **MEDIUM:** Standardize API field names
5. **MEDIUM:** Re-save scalers to fix version warning
6. **LOW:** Improve touch targets and accessibility

---

## FILES REQUIRING CHANGES

| File | Changes Needed |
|------|----------------|
| `dashboard/tabs/MetricsTab.svelte` | Add null guards, fix empty array handling |
| `RetrofitDetailed.svelte` | Fix z-index, verify mode switching |
| `RetrofitSplitPaneLayout.svelte` | Add z-index to sidebar |
| `api/server.py` | Standardize response field names |
| Various chart components | Add proper Plotly types |
| `stores/logStore.ts` | Verify console logging |

---

## CSV IMPORT FORMAT

For reference, the expected CSV format:

```csv
scenario_name,time_horizon,windows_U_Factor,groundfloor_thermal_resistance,ext_walls_thermal_resistance,roof_thermal_resistance,tags
Baseline 2020,2020,2.9,0.41,0.45,0.48,baseline
Basic Retrofit,2020,2.0,1.5,1.5,2.0,retrofit
Deep Retrofit,2020,0.9,5.0,6.0,8.0,deep
```

**Required columns:** time_horizon, windows_U_Factor, groundfloor_thermal_resistance, ext_walls_thermal_resistance, roof_thermal_resistance
**Optional columns:** scenario_name, tags
**Valid time_horizon values:** 2020, 2050, 2100

---

## TESTING CHECKLIST

- [x] User-Driven path - Predictions work
- [x] Scenario tabs A/B/C - Switchable
- [x] Time horizon buttons - Work
- [x] Preset buttons - Available
- [x] Run Predictions - Works (via JS click)
- [ ] Constraint-Based path - UI not switching
- [ ] NSGA-II optimization - Not tested
- [ ] CSV Import - Not tested
- [ ] CSV Export - Not tested
- [ ] MCDM ranking - Not tested
- [ ] 2D/3D Charts - Not fully tested
- [ ] Parallel coordinates - Not tested

---

*Report generated by comprehensive-audit.cjs*
