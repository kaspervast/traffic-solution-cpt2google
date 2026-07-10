# AI Traffic Simulation Platform — Critical Review and Suggested Changes

**Reviews:** `AI_Traffic_Simulation_Platform_Build_Specification.md`
**Purpose:** Identify what is missing, what will decide whether the project succeeds, and concrete changes to fold back into the specification.
**Bottom line:** The software architecture and guardrails are strong. The unaddressed risks are all *upstream* of the code — ground-truth data access, demand identifiability, and Indian mixed-traffic calibration. Prove those in Phase 0 before writing much application code, and demote both the AI assistant and Google-as-a-calibration-source out of the MVP.

---

## 1. Highest-priority risks (these decide the project)

### 1.1 Data access is the real Phase 0 exit criterion

The pilot assumes manual counts for a peak hour, both-direction travel times, and real signal timings. In India these come from the municipal corporation or traffic police — not from an API. If there is no signed access to ground truth for the target Rajkot corridor, the calibration story collapses and nothing downstream matters.

**Change:** Make a written data-access agreement (turning-movement counts, travel times, signal plans, or a verified "unsignalized" statement) the *first* Phase 0 exit gate, ahead of the API proofs. If no partner is committed, treat the project as an exploration/demo tool only and say so explicitly.

### 1.2 Demand is not identifiable from speeds alone

The confidence hierarchy already admits this quietly: without classified counts you land at grade C or below, which the spec itself calls "directional, not final." The mathematical reason should be stated outright: speed/travel-time observations do not pin down flow. The fundamental diagram is non-unique — the same speed occurs at very different flows on the free-flow versus congested branch. Calibrating demand "mainly from speed/travel-time observations" (grade C) is underdetermined; you can fit travel times and still have the wrong volumes.

**Change:** State plainly that classified counts are a hard prerequisite for any result intended to inform a real decision. Label speed-only operation as a demonstration/exploration mode in the UI and in every report generated from it. Do not let a grade-C baseline render a green "improvement" badge without an explicit "directional only" watermark.

### 1.3 SUMO vs. Indian mixed traffic is a modelling gap, not a parameter list

The spec lists Indian vehicle classes and passenger-car equivalents (PCE). PCE is a workaround, not a model of heterogeneous, non-lane-disciplined traffic (motorcycle filtering, auto-rickshaws, lateral movement, gap-acceptance behaviour). SUMO's default Krauss car-following and lane-based movement are calibrated to European lane-disciplined traffic and represent Indian conditions poorly.

**Change:** Explicitly commit to SUMO's **sublane model** (`lateral-resolution`, lane-change model tuning) and treat mixed-traffic calibration as a research-grade effort with its own validation and risk entry — not a bullet inside the vehicle-class section. Budget time for it and set expectations accordingly.

---

## 2. Missing pieces to add to the specification

### 2.1 Numeric calibration acceptance criteria

The spec repeatedly says "acceptable error" but never defines it, which makes "calibrated" subjective and confidence grade A unfalsifiable.

**Change — add explicit targets, e.g.:**

- Link flows: GEH < 5 for the majority (target ≥ 85%) of modelled links.
- Travel time: modelled within ±15% of observed for each corridor direction.
- Queue length: within a stated tolerance at instrumented approaches.

Cite a recognised standard (e.g. GEH statistic; DMRB/Highways England calibration guidance) so the criteria are defensible in a report.

### 2.2 Origin-destination estimation mechanism

"Create origin/destination zones" appears as a one-click area action, but turning counts → routable demand (gravity model, `od2trips`/`activitygen`, or OD matrix estimation from counts) is an entire discipline that is currently absent.

**Change:** Add a demand-generation subsection specifying how counts become routes, which SUMO tools are used, and how the OD matrix is estimated and versioned.

### 2.3 Boundary / cordon loading strategy

For a 3–5 junction corridor, fringe demand injection *dominates* the result. The spec flags boundary queues only as a warning.

**Change:** Specify an explicit buffer-zone / cordon-loading approach (extend the network past the study area, load fringe demand from screen-line counts) rather than warning after the fact.

### 2.4 Statistical significance across seeds

Section 11.5 requests 5–10 seeds and "mean and uncertainty," but section 15.2 declares improvements. Seed noise can masquerade as a policy finding.

**Change:** Add a rule — do not label a change an improvement unless it exceeds seed-to-seed variability. Report confidence intervals on every KPI delta and, where feasible, a significance test on the baseline-vs-proposal difference.

### 2.5 Reproducibility vs. retention conflict

Reports promise another analyst can reproduce a run, but retention policies may force deletion of the source observations. The two guarantees contradict.

**Change:** At run time, snapshot an immutable, licence-permitted **evidence bundle** (the exact observations, versions, seeds, and configuration used). Reproducibility is defined against the bundle, not against live provider data that may be deleted.

### 2.6 Model-drift and provider-routing guards for the AI

`z-ai/glm-4.6` on OpenRouter can be re-routed across providers with differing tool-calling quality, and the model may be deprecated.

**Change:** Add a CI eval gate that pins expected tool-calling behaviour, records the actual provider/model used per call, and fails the build if valid-tool-call rate drops below a threshold.

---

## 3. Two decisions I would make differently

### 3.1 Assume Google Routes cannot calibrate SUMO; plan around TomTom

The Service-Specific Terms gate is correctly flagged, but blocking on a legal opinion puts the whole data layer on the critical path. The likely outcome is that Routes content cannot be persisted into your canonical dataset, cannot be used to derive simulation parameters, and possibly cannot be shown alongside non-Google overlays.

**Change:** Design now so that **TomTom is the calibration/observation source** and **Google is basemap + place search + polygon drawing only.** This removes the single largest legal dependency from the critical path and lets the licensing determination proceed in parallel instead of blocking.

### 3.2 Move the AI assistant out of the MVP

The spec's own final instruction says the AI is useful only after map objects, operations, and metrics are trustworthy — which is correct. But the AI layer also adds the largest attack surface (prompt injection via road names and imported files), real per-run cost, provider nondeterminism, and Phase 5's 3–4 weeks. A well-built form plus quick-action UI covers the great majority of scenario-creation value.

**Change:** Ship the pilot without the LLM. Add it only after calibration is proven on the corridor. Keep the typed scenario-operation contract (it is valuable regardless) and treat the LLM as an optional front-end that emits that same contract.

---

## 4. Smaller items

- **Timeline/team realism.** Phases 0–6 sum to ~19–26 weeks and implicitly assume a multi-person team (frontend, backend, GIS, traffic engineering, AI, DevOps). For a solo or two-person team this is a 12+ month effort. State the assumed team size in section 20.
- **OSM quality in Rajkot.** Lane counts, turn restrictions, and signal locations are frequently missing or wrong in Indian OSM. The validation list catches symptoms, but budget explicitly for the manual-correction volume — it will likely be the largest time sink in Phase 2.
- **Emissions model.** HBEFA is a European fleet model. Do not present emission/fuel figures for an Indian fleet without a caveat, or drop them from the MVP.
- **Accessibility.** WCAG 2.2 AA on a canvas map-selection tool is aspirational. Keep the specced tabular alternatives as the real accessibility path; do not over-promise on the map surface itself.
- **Signal ground truth.** Actuated-vs-fixed comparisons require the current timings. Obtaining real signal plans is a field-survey problem; treat it as a data-access dependency (see 1.1), not an assumption.

---

## 5. Suggested Phase 0 rewrite (drop-in)

**Phase 0 — Feasibility, data access and licensing (2–3 weeks)**

Exit only when *all* of the following hold:

1. **Signed data access** for the pilot corridor: at least one peak-hour classified count set, both-direction travel times, and either current signal timings or a verified unsignalized statement.
2. **Licensing determination** (or a decision to run TomTom-only for calibration and Google for basemap/search only) documented in writing.
3. **TomTom coverage verified** to return useful flow/incident results on the target roads.
4. **SUMO sublane feasibility check:** a toy mixed-traffic network reproduces plausible motorcycle/auto behaviour with the sublane model.
5. **OpenRouter `z-ai/glm-4.6` tool-call proof** (deferred component; nice-to-have, not a blocker for MVP).
6. **Selected corridor** of 3–5 connected junctions with a known congested junction and at least one alternative route.

If items 1–3 cannot be met, reclassify the project as a demonstration/exploration tool and remove all decision-support language from the UI and reports.

---

## 6. Risk register (add to the spec)

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | No ground-truth data access | High | Fatal | Phase 0 gate 1; fall back to demo-only mode |
| R2 | Demand unidentifiable from speeds | High | High | Require counts for decision-grade; watermark speed-only runs |
| R3 | SUMO misrepresents mixed traffic | High | High | Commit to sublane model; dedicated calibration + validation |
| R4 | Google Routes ToS blocks calibration use | Med–High | High | TomTom for calibration, Google basemap-only by design |
| R5 | Seed noise reported as findings | Med | High | Significance rule on KPI deltas |
| R6 | Poor Indian OSM topology | High | Med | Budget manual correction; strong validation UI |
| R7 | Retention deletes reproducibility source | Med | Med | Immutable evidence bundle at run time |
| R8 | AI prompt injection / cost / drift | Med | Med | Defer AI from MVP; CI eval gate; typed-contract boundary |
| R9 | Timeline underestimated for small team | High | Med | State team assumptions; sequence vertical slices |
