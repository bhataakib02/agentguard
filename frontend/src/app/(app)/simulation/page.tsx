"use client";

import React, { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import {
  FlaskConical,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Shield,
  Activity,
  BarChart2,
  Download,
  RefreshCw,
  Filter,
  Layers,
  Zap,
  Info,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  StopCircle
} from "lucide-react";

interface ScenarioAgentProfile {
  agent_code: string;
  name: string;
  autonomy_level: string;
  department: string;
  granted_permissions: Array<{ action: string; resource_type: string; resource_name: string }>;
  daily_budget: number;
}

interface ScenarioActionStep {
  step_index: number;
  action: string;
  resource: string;
  operation?: string;
  amount: number;
  prompt: string;
  is_terminal_step: boolean;
}

interface SimulationScenario {
  scenario_id: string;
  version: string;
  category: string;
  title: string;
  description: string;
  provenance: string;
  agent_profile: ScenarioAgentProfile;
  initial_history: Array<Record<string, any>>;
  action_sequence: ScenarioActionStep[];
  expected_baseline_decision: string;
  expected_pace_decision: string;
  expected_risk_category: string;
  expected_pace_intervention: string;
  ground_truth_label: "SAFE" | "RISKY";
  relevance_justification: string;
  limitations: string;
}

interface SimulationStepOutcome {
  step_index: number;
  action: string;
  resource: string;
  amount: number;
  is_terminal_step: boolean;
  baseline_decision: string;
  baseline_risk_score: number;
  baseline_reason: string;
  pace_decision: string;
  pace_risk_score: number;
  pace_intervention: string;
  pace_intervention_rationale: string;
  sequence_risk_delta: number;
  reachability_reachable: boolean;
  candidate_target_chains: string[];
  pace_enforcement_status: string;
}

interface ScenarioRunResult {
  scenario_id: string;
  scenario_title: string;
  category: string;
  ground_truth_label: "SAFE" | "RISKY";
  steps: SimulationStepOutcome[];
  baseline_final_decision: string;
  pace_final_decision: string;
  pace_selected_intervention: string;
  early_detection_lead_steps: number;
  baseline_matches_ground_truth: boolean;
  pace_matches_ground_truth: boolean;
  detected_before_terminal: boolean;
}

interface ConfusionMatrixMetrics {
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
  accuracy: number;
  precision: number;
  recall: number;
  false_positive_rate: number;
  false_negative_rate: number;
  f1_score: number;
}

interface SimulationMetricsSummary {
  unit_of_measurement: string;
  total_scenarios_evaluated: number;
  total_actions_evaluated: number;
  baseline_metrics: ConfusionMatrixMetrics;
  pace_metrics: ConfusionMatrixMetrics;
  avg_detection_lead_steps: number;
  intervention_breakdown: Record<string, number>;
  unenforceable_recommendations_count: number;
  insufficient_data_count: number;
  category_breakdown: Record<string, { count: number; baseline_correct: number; pace_correct: number }>;
  runtime_ms: number;
  provenance: string;
  evaluation_limitations: string;
}

interface SimulationRunResponse {
  run_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
  mode: string;
  created_at: string;
  completed_at?: string;
  scenarios_total: number;
  scenarios_completed: number;
  results: ScenarioRunResult[];
  metrics?: SimulationMetricsSummary;
  error?: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  ALL: "All Categories",
  BENIGN_ROUTINE: "1. Benign Routine",
  UNAUTHORIZED_RESOURCE: "2. Unauthorized Resource",
  SUSPICIOUS_RECONNAISSANCE: "3. Suspicious Recon",
  SENSITIVE_DATA_EXFILTRATION: "4. Sensitive Data Exfiltration",
  REPEATED_REFUSAL_EVASION: "5. Repeated Refusal",
  CROSS_TENANT_ATTEMPT: "6. Cross-Tenant Attempt",
  PRIVILEGE_ESCALATION: "7. Privilege Escalation",
  NOVEL_SPARSE_HISTORY: "8. Novel / Sparse History",
  LEGITIMATE_HIGH_RISK_REVIEW: "9. High-Risk Review",
  FALSE_POSITIVE_EDGE: "10. False-Positive Edge"
};

export default function SimulationLabPage() {
  const [scenarios, setScenarios] = useState<SimulationScenario[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [activeScenario, setActiveScenario] = useState<SimulationScenario | null>(null);
  const [loadingScenarios, setLoadingScenarios] = useState(true);

  // Simulation execution state
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<SimulationRunResponse | null>(null);
  const [selectedResult, setSelectedResult] = useState<ScenarioRunResult | null>(null);
  const [runMode, setRunMode] = useState<"BASELINE_VS_PACE" | "PACE_ONLY" | "BASELINE_ONLY">("BASELINE_VS_PACE");

  const loadScenarios = async (category: string = "ALL") => {
    try {
      setLoadingScenarios(true);
      const url = category === "ALL" ? "/simulation/scenarios" : `/simulation/scenarios?category=${category}`;
      const data = await fetchApi(url);
      setScenarios(data || []);
      if (data && data.length > 0 && !activeScenario) {
        setActiveScenario(data[0]);
      }
    } catch (err) {
      console.error("Error loading scenarios:", err);
    } finally {
      setLoadingScenarios(false);
    }
  };

  useEffect(() => {
    loadScenarios(selectedCategory);
  }, [selectedCategory]);

  const handleStartSimulation = async () => {
    try {
      setIsRunning(true);
      const payload = {
        mode: runMode,
        categories: selectedCategory === "ALL" ? undefined : [selectedCategory],
        scenario_ids: undefined,
        seed: 42
      };

      const res: SimulationRunResponse = await fetchApi("/simulation/runs", {
        method: "POST",
        body: JSON.stringify(payload)
      });

      setCurrentRun(res);
      if (res.results && res.results.length > 0) {
        setSelectedResult(res.results[0]);
      }
    } catch (err: any) {
      alert(`Simulation failed: ${err.message || err}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleCancelRun = async () => {
    if (!currentRun) return;
    try {
      await fetchApi(`/simulation/runs/${currentRun.run_id}/cancel`, { method: "POST" });
      setIsRunning(false);
    } catch (err) {
      console.error("Cancel error:", err);
    }
  };

  const exportReportJson = () => {
    if (!currentRun) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentRun, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `AgentGuard_Simulation_Report_${currentRun.run_id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E8E8E4] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-[#2E9D50]" />
            <h1 className="text-[20px] font-bold text-[#1F1F1F]">Agent Simulation & Evaluation Lab</h1>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-[#FFF4E5] text-[#C45E00] border border-[#F59A23]/30 rounded">
              SIMULATED TEST ENVIRONMENT
            </span>
          </div>
          <p className="text-[12px] text-[#666666] mt-1">
            Reproducible benchmark harness comparing deterministic baseline policy against PACE sequence-risk, reachability analysis, and minimal interventions.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          {currentRun && (
            <button
              onClick={exportReportJson}
              className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-bold text-[#1F1F1F] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] hover:bg-[#FCFCFA] shadow-xs cursor-pointer transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-[#666666]" />
              Export Report
            </button>
          )}

          {isRunning ? (
            <button
              onClick={handleCancelRun}
              className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-bold text-[#FFFFFF] bg-[#E05656] hover:bg-[#C94040] rounded-[8px] shadow-sm cursor-pointer transition-colors"
            >
              <StopCircle className="w-4 h-4 animate-spin" />
              Cancel Run
            </button>
          ) : (
            <button
              onClick={handleStartSimulation}
              disabled={loadingScenarios}
              className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-bold text-[#FFFFFF] bg-[#2E9D50] hover:bg-[#237A3C] rounded-[8px] shadow-sm cursor-pointer transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-current" />
              Run Simulation Benchmark
            </button>
          )}
        </div>
      </div>

      {/* Safety & Isolation Invariant Banner */}
      <div className="bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] p-3.5 text-[12px] text-[#666666] flex items-start gap-3">
        <Shield className="w-4 h-4 text-[#2E9D50] shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <p className="font-bold text-[#1F1F1F]">Simulation Guardrails & Provenance Guarantee</p>
          <p>
            All actions execute against isolated in-memory simulation adapters. Hypothetical actions are never dispatched to real external tools or external systems. Results are recorded transiently in the simulation registry and are strictly excluded from production audit logs.
          </p>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-[#E8E8E4]">
        {Object.entries(CATEGORY_LABELS).map(([catKey, label]) => {
          const isActive = selectedCategory === catKey;
          return (
            <button
              key={catKey}
              onClick={() => setSelectedCategory(catKey)}
              className={`px-3 py-1.5 rounded-[6px] text-[11px] font-bold whitespace-nowrap transition-colors cursor-pointer ${
                isActive
                  ? "bg-[#2E9D50] text-[#FFFFFF]"
                  : "bg-[#FFFFFF] text-[#666666] border border-[#E8E8E4] hover:bg-[#FCFCFA]"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Comparative Evaluation Metrics (When a Run is Completed) */}
      {currentRun && currentRun.metrics && (
        <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E8E8E4] pb-3">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-[#2E9D50]" />
              <h2 className="text-[14px] font-bold text-[#1F1F1F]">Baseline vs. PACE Comparative Metrics</h2>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded">
                Run ID: {currentRun.run_id} ({currentRun.metrics.total_scenarios_evaluated} scenarios / {currentRun.metrics.total_actions_evaluated} actions in {currentRun.metrics.runtime_ms}ms)
              </span>
            </div>
            <div className="text-[11px] text-[#666666]">
              Early Lead Steps: <span className="font-bold text-[#2E9D50]">+{currentRun.metrics.avg_detection_lead_steps.toFixed(2)} steps</span>
            </div>
          </div>

          {/* Metric Comparison Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 text-[12px]">
            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[10px] text-[#666666] uppercase block font-bold">PACE F1 Score</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-[17px] font-bold text-[#2E9D50]">
                  {(currentRun.metrics.pace_metrics.f1_score * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-[#666666]">
                  (Base: {(currentRun.metrics.baseline_metrics.f1_score * 100).toFixed(1)}%)
                </span>
              </div>
            </div>

            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[10px] text-[#666666] uppercase block font-bold">PACE Precision</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-[17px] font-bold text-[#1F1F1F]">
                  {(currentRun.metrics.pace_metrics.precision * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-[#666666]">
                  (Base: {(currentRun.metrics.baseline_metrics.precision * 100).toFixed(1)}%)
                </span>
              </div>
            </div>

            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[10px] text-[#666666] uppercase block font-bold">PACE Recall</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-[17px] font-bold text-[#1F1F1F]">
                  {(currentRun.metrics.pace_metrics.recall * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-[#666666]">
                  (Base: {(currentRun.metrics.baseline_metrics.recall * 100).toFixed(1)}%)
                </span>
              </div>
            </div>

            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[10px] text-[#666666] uppercase block font-bold">False Positive Rate</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-[17px] font-bold text-[#F59A23]">
                  {(currentRun.metrics.pace_metrics.false_positive_rate * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-[#666666]">
                  (Base: {(currentRun.metrics.baseline_metrics.false_positive_rate * 100).toFixed(1)}%)
                </span>
              </div>
            </div>

            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[10px] text-[#666666] uppercase block font-bold">False Negative Rate</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-[17px] font-bold text-[#E05656]">
                  {(currentRun.metrics.pace_metrics.false_negative_rate * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-[#666666]">
                  (Base: {(currentRun.metrics.baseline_metrics.false_negative_rate * 100).toFixed(1)}%)
                </span>
              </div>
            </div>

            <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
              <span className="text-[10px] text-[#666666] uppercase block font-bold">Early Detection Lead</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-[17px] font-bold text-[#2E9D50]">
                  +{currentRun.metrics.avg_detection_lead_steps.toFixed(1)} steps
                </span>
                <span className="text-[10px] text-[#666666]">(ahead of terminal)</span>
              </div>
            </div>
          </div>

          {/* Side-by-Side Confusion Matrices */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            {/* Baseline Policy Matrix */}
            <div className="p-3.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-[#666666] uppercase">Baseline Deterministic Policy</span>
                <span className="text-[10px] font-mono px-2 py-0.5 bg-[#F4F4F2] text-[#666666] rounded">
                  Acc: {(currentRun.metrics.baseline_metrics.accuracy * 100).toFixed(1)}%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-center text-[11px]">
                <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                  <span className="block text-[9px] text-[#666666]">TRUE POSITIVES (TP)</span>
                  <span className="text-[14px] font-bold text-[#2E9D50]">
                    {currentRun.metrics.baseline_metrics.true_positives}
                  </span>
                </div>
                <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                  <span className="block text-[9px] text-[#666666]">FALSE POSITIVES (FP)</span>
                  <span className="text-[14px] font-bold text-[#F59A23]">
                    {currentRun.metrics.baseline_metrics.false_positives}
                  </span>
                </div>
                <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                  <span className="block text-[9px] text-[#666666]">FALSE NEGATIVES (FN)</span>
                  <span className="text-[14px] font-bold text-[#E05656]">
                    {currentRun.metrics.baseline_metrics.false_negatives}
                  </span>
                </div>
                <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                  <span className="block text-[9px] text-[#666666]">TRUE NEGATIVES (TN)</span>
                  <span className="text-[14px] font-bold text-[#1F1F1F]">
                    {currentRun.metrics.baseline_metrics.true_negatives}
                  </span>
                </div>
              </div>
            </div>

            {/* PACE Engine Matrix */}
            <div className="p-3.5 bg-[#EAF7EE]/30 border border-[#2E9D50]/40 rounded-[8px] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-[#237A3C] uppercase flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5 text-[#2E9D50]" />
                  PACE Engine (Sequence + Reachability)
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] rounded font-bold">
                  Acc: {(currentRun.metrics.pace_metrics.accuracy * 100).toFixed(1)}%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-center text-[11px]">
                <div className="p-2 bg-[#FFFFFF] border border-[#2E9D50]/30 rounded">
                  <span className="block text-[9px] text-[#666666]">TRUE POSITIVES (TP)</span>
                  <span className="text-[14px] font-bold text-[#2E9D50]">
                    {currentRun.metrics.pace_metrics.true_positives}
                  </span>
                </div>
                <div className="p-2 bg-[#FFFFFF] border border-[#2E9D50]/30 rounded">
                  <span className="block text-[9px] text-[#666666]">FALSE POSITIVES (FP)</span>
                  <span className="text-[14px] font-bold text-[#F59A23]">
                    {currentRun.metrics.pace_metrics.false_positives}
                  </span>
                </div>
                <div className="p-2 bg-[#FFFFFF] border border-[#2E9D50]/30 rounded">
                  <span className="block text-[9px] text-[#666666]">FALSE NEGATIVES (FN)</span>
                  <span className="text-[14px] font-bold text-[#E05656]">
                    {currentRun.metrics.pace_metrics.false_negatives}
                  </span>
                </div>
                <div className="p-2 bg-[#FFFFFF] border border-[#2E9D50]/30 rounded">
                  <span className="block text-[9px] text-[#666666]">TRUE NEGATIVES (TN)</span>
                  <span className="text-[14px] font-bold text-[#1F1F1F]">
                    {currentRun.metrics.pace_metrics.true_negatives}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Provenance & Limitations Disclosure */}
          <div className="p-2.5 bg-[#F9F9F8] border border-[#E8E8E4] rounded-[6px] text-[11px] text-[#666666]">
            <span className="font-bold text-[#1F1F1F]">Benchmark Limitations:</span> {currentRun.metrics.evaluation_limitations}
          </div>
        </div>
      )}

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Scenario Library / Run Results (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] p-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3 mb-3">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#2E9D50]" />
                <h3 className="text-[13px] font-bold text-[#1F1F1F]">
                  {currentRun ? "Benchmark Run Results" : "Scenario Library"}
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 bg-[#F4F4F2] text-[#666666] rounded">
                {currentRun ? `${currentRun.results.length} Scenarios` : `${scenarios.length} Scenarios`}
              </span>
            </div>

            {/* List */}
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {currentRun ? (
                // Display run results
                currentRun.results.map((res) => {
                  const isSelected = selectedResult?.scenario_id === res.scenario_id;
                  return (
                    <div
                      key={res.scenario_id}
                      onClick={() => {
                        setSelectedResult(res);
                        const sc = scenarios.find((s) => s.scenario_id === res.scenario_id);
                        if (sc) setActiveScenario(sc);
                      }}
                      className={`p-3 rounded-[8px] border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-[#EAF7EE] border-[#2E9D50]"
                          : "bg-[#FCFCFA] border-[#E8E8E4] hover:bg-[#F4F4F2]"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 bg-[#FFFFFF] border border-[#E8E8E4] rounded text-[#666666]">
                              {res.scenario_id.split("-").slice(0, 2).join("-")}
                            </span>
                            <span className="text-[12px] font-bold text-[#1F1F1F] leading-tight">
                              {res.scenario_title}
                            </span>
                          </div>
                          <span className="text-[10px] text-[#666666] block mt-1">
                            {CATEGORY_LABELS[res.category] || res.category}
                          </span>
                        </div>
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                            res.ground_truth_label === "RISKY"
                              ? "bg-[#FDE8E8] text-[#9C1C1C]"
                              : "bg-[#EAF7EE] text-[#237A3C]"
                          }`}
                        >
                          {res.ground_truth_label}
                        </span>
                      </div>

                      {/* Comparative Result Badges */}
                      <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-[#E8E8E4]/60 text-[10px]">
                        <div>
                          <span className="text-[#666666] block">Baseline:</span>
                          <span
                            className={`font-bold ${
                              res.baseline_final_decision === "ALLOW"
                                ? "text-[#2E9D50]"
                                : res.baseline_final_decision === "REVIEW"
                                ? "text-[#F59A23]"
                                : "text-[#E05656]"
                            }`}
                          >
                            {res.baseline_final_decision}
                          </span>
                        </div>
                        <div>
                          <span className="text-[#666666] block">PACE:</span>
                          <span
                            className={`font-bold ${
                              res.pace_final_decision === "ALLOW"
                                ? "text-[#2E9D50]"
                                : res.pace_final_decision === "REVIEW"
                                ? "text-[#F59A23]"
                                : "text-[#E05656]"
                            }`}
                          >
                            {res.pace_final_decision} ({res.pace_selected_intervention.split("_")[0]})
                          </span>
                        </div>
                      </div>

                      {res.detected_before_terminal && (
                        <div className="mt-1.5 text-[9px] font-bold text-[#237A3C] bg-[#EAF7EE] px-1.5 py-0.5 rounded flex items-center gap-1">
                          <Zap className="w-3 h-3 text-[#2E9D50]" />
                          Detected {res.early_detection_lead_steps} step(s) prior to terminal
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                // Display scenario library
                scenarios.map((sc) => {
                  const isSelected = activeScenario?.scenario_id === sc.scenario_id;
                  return (
                    <div
                      key={sc.scenario_id}
                      onClick={() => setActiveScenario(sc)}
                      className={`p-3 rounded-[8px] border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-[#EAF7EE] border-[#2E9D50]"
                          : "bg-[#FCFCFA] border-[#E8E8E4] hover:bg-[#F4F4F2]"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 bg-[#FFFFFF] border border-[#E8E8E4] rounded text-[#666666]">
                              {sc.scenario_id.split("-").slice(0, 2).join("-")}
                            </span>
                            <span className="text-[12px] font-bold text-[#1F1F1F] leading-tight">
                              {sc.title}
                            </span>
                          </div>
                          <span className="text-[10px] text-[#666666] block mt-1">
                            {CATEGORY_LABELS[sc.category] || sc.category}
                          </span>
                        </div>
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                            sc.ground_truth_label === "RISKY"
                              ? "bg-[#FDE8E8] text-[#9C1C1C]"
                              : "bg-[#EAF7EE] text-[#237A3C]"
                          }`}
                        >
                          {sc.ground_truth_label}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#666666] mt-2 line-clamp-2">
                        {sc.description}
                      </p>
                      <div className="flex items-center gap-2 mt-2 text-[10px] text-[#666666]">
                        <span>Agent: <strong>{sc.agent_profile.name}</strong></span>
                        <span>•</span>
                        <span>Autonomy: <strong>{sc.agent_profile.autonomy_level}</strong></span>
                        <span>•</span>
                        <span>Steps: <strong>{sc.action_sequence.length}</strong></span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Detailed Scenario & Comparative Timeline (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {activeScenario ? (
            <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] p-5 shadow-sm space-y-5">
              {/* Scenario Header */}
              <div className="border-b border-[#E8E8E4] pb-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-[#F4F4F2] text-[#666666] rounded">
                    {activeScenario.scenario_id} v{activeScenario.version}
                  </span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-[#FFF4E5] text-[#C45E00] rounded">
                    PROVENANCE: {activeScenario.provenance}
                  </span>
                </div>
                <h2 className="text-[16px] font-bold text-[#1F1F1F] mt-2">
                  {activeScenario.title}
                </h2>
                <p className="text-[12px] text-[#666666] mt-1">
                  {activeScenario.description}
                </p>

                {/* Relevance and Ground Truth limitations */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 text-[11px]">
                  <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]">
                    <span className="font-bold text-[#1F1F1F] block">Why Scenario is Relevant:</span>
                    <span className="text-[#666666]">{activeScenario.relevance_justification}</span>
                  </div>
                  <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[6px]">
                    <span className="font-bold text-[#1F1F1F] block">Ground Truth Label:</span>
                    <span className="text-[#666666]">{activeScenario.ground_truth_label} — {activeScenario.limitations}</span>
                  </div>
                </div>
              </div>

              {/* Agent Permissions and Autonomy */}
              <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[11px] space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#1F1F1F]">
                    Agent: {activeScenario.agent_profile.name} ({activeScenario.agent_profile.agent_code})
                  </span>
                  <span className="font-mono text-[#2E9D50] font-bold">
                    Autonomy: {activeScenario.agent_profile.autonomy_level}
                  </span>
                </div>
                <div className="text-[#666666]">
                  <strong>Granted Permissions: </strong>
                  {activeScenario.agent_profile.granted_permissions.map((p) => `${p.action} on ${p.resource_name}`).join(", ")}
                </div>
              </div>

              {/* Action-by-Action Comparative Timeline */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-[13px] font-bold text-[#1F1F1F] flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-[#2E9D50]" />
                    Action Sequence Timeline
                  </h3>
                  <span className="text-[10px] text-[#666666]">
                    {selectedResult ? "Evaluated Step Outcomes" : "Configured Sequence Steps"}
                  </span>
                </div>

                <div className="space-y-2.5">
                  {(selectedResult
                    ? selectedResult.steps
                    : activeScenario.action_sequence.map((st) => ({
                        step_index: st.step_index,
                        action: st.action,
                        resource: st.resource,
                        amount: st.amount,
                        is_terminal_step: st.is_terminal_step,
                        baseline_decision: activeScenario.expected_baseline_decision,
                        baseline_risk_score: 15,
                        baseline_reason: "Expected baseline policy decision.",
                        pace_decision: activeScenario.expected_pace_decision,
                        pace_risk_score: 75,
                        pace_intervention: activeScenario.expected_pace_intervention,
                        pace_intervention_rationale: "Expected PACE minimal intervention.",
                        sequence_risk_delta: 0,
                        reachability_reachable: false,
                        candidate_target_chains: [],
                        pace_enforcement_status: "ENFORCED"
                      }))
                  ).map((step, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-[8px] border text-[12px] space-y-2 ${
                        step.is_terminal_step
                          ? "bg-[#FFFDF7] border-[#F59A23]/40"
                          : "bg-[#FFFFFF] border-[#E8E8E4]"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-[#1F1F1F] text-[#FFFFFF] text-[10px] font-bold flex items-center justify-center">
                            {step.step_index}
                          </span>
                          <span className="font-mono font-bold text-[#1F1F1F]">
                            {step.action} &rarr; {step.resource}
                          </span>
                          {step.amount > 0 && (
                            <span className="text-[10px] font-mono text-[#666666]">
                              (₹{step.amount.toLocaleString()})
                            </span>
                          )}
                        </div>
                        {step.is_terminal_step && (
                          <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 bg-[#FFF4E5] text-[#C45E00] rounded">
                            Terminal Step
                          </span>
                        )}
                      </div>

                      {/* Side-by-Side Step Decisions */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-[11px]">
                        {/* Baseline Decision */}
                        <div className="p-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-[#666666]">Baseline Policy:</span>
                            <span
                              className={`font-bold px-1.5 py-0.2 rounded text-[10px] ${
                                step.baseline_decision === "ALLOW"
                                  ? "bg-[#EAF7EE] text-[#237A3C]"
                                  : step.baseline_decision === "REVIEW"
                                  ? "bg-[#FFF4E5] text-[#C45E00]"
                                  : "bg-[#FDE8E8] text-[#9C1C1C]"
                              }`}
                            >
                              {step.baseline_decision}
                            </span>
                          </div>
                          <p className="text-[10px] text-[#666666] mt-1 line-clamp-2">
                            {step.baseline_reason}
                          </p>
                        </div>

                        {/* PACE Decision */}
                        <div className="p-2 bg-[#EAF7EE]/30 border border-[#2E9D50]/30 rounded">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-[#237A3C]">PACE Intervention:</span>
                            <span
                              className={`font-bold px-1.5 py-0.2 rounded text-[10px] ${
                                step.pace_decision === "ALLOW"
                                  ? "bg-[#EAF7EE] text-[#237A3C]"
                                  : step.pace_decision === "REVIEW"
                                  ? "bg-[#FFF4E5] text-[#C45E00]"
                                  : "bg-[#FDE8E8] text-[#9C1C1C]"
                              }`}
                            >
                              {step.pace_decision}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-1 text-[10px]">
                            <span className="font-bold text-[#1F1F1F]">
                              Plan: {step.pace_intervention}
                            </span>
                            {step.sequence_risk_delta > 0 && (
                              <span className="text-[#F59A23] font-mono">
                                (&Delta;Risk: +{step.sequence_risk_delta})
                              </span>
                            )}
                          </div>
                          {step.reachability_reachable && (
                            <span className="inline-block text-[9px] font-bold text-[#C45E00] bg-[#FFF4E5] px-1 rounded mt-0.5">
                              Chain: {step.candidate_target_chains.join(" &rarr; ")}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] p-8 text-center text-[#666666]">
              Select a scenario from the library to view details and action timeline.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
