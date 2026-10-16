"use client";

import React, { useEffect, useState, useRef } from "react";
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
  StopCircle,
  Database,
  UploadCloud,
  FileText,
  Lock,
  X,
  Search,
  FileJson,
  AlertCircle,
  Check,
  ShieldCheck
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
  sample_size?: number;
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
  dataset_name?: string;
  dataset_identity?: string;
  evaluation_method?: string;
  records_submitted?: number;
  records_completed?: number;
  records_failed?: number;
  records_excluded?: number;
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
  dataset_name?: string;
  dataset_provenance?: string;
  records_total?: number;
  records_evaluated?: number;
  records_failed?: number;
  records_excluded?: number;
  validation_report?: {
    status: string;
    unsupported_records: Array<{ record_id: string; error: string }>;
  };
}

// Evaluation Dataset Interfaces (Phase 5.1/5.2)
interface EvaluationDatasetSummary {
  dataset_name: string;
  description?: string;
  provenance: string;
  records_count: number;
  created_at: string;
  tags: string[];
}

interface EvaluationRecordStep {
  step_number: number;
  action: string;
  resource: string;
  operation?: string;
  amount?: number;
  parameters?: Record<string, any>;
  prompt?: string;
  is_terminal_step?: boolean;
}

interface EvaluationRecordAgentProfile {
  agent_code: string;
  name: string;
  autonomy_level: string;
  department?: string;
  granted_permissions?: Array<{ action: string; resource_type: string; resource_name: string }>;
  daily_budget?: number;
}

interface EvaluationDatasetRecordItem {
  dataset_id: string;
  record_id: string;
  provenance: string;
  agent_profile: EvaluationRecordAgentProfile;
  initial_history?: Array<Record<string, any>>;
  action_sequence: EvaluationRecordStep[];
  ground_truth_label: "SAFE" | "RISKY";
  ground_truth_notes?: string;
  tags?: string[];
}

interface EvaluationDatasetDetail {
  dataset_name: string;
  description: string;
  provenance: string;
  records: EvaluationDatasetRecordItem[];
  created_at: string;
  updated_at?: string;
  tags: string[];
}

interface ImportResponse {
  status: "SUCCESS" | "REJECTED" | "PARTIAL";
  dataset_name: string;
  provenance: string;
  imported_records_count: number;
  validation_errors: string[];
  notice: string;
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
  // Main view navigation tab: "scenarios" | "datasets"
  const [activeMainTab, setActiveMainTab] = useState<"scenarios" | "datasets">("scenarios");

  // --- Scenarios State ---
  const [scenarios, setScenarios] = useState<SimulationScenario[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [activeScenario, setActiveScenario] = useState<SimulationScenario | null>(null);
  const [loadingScenarios, setLoadingScenarios] = useState(true);

  // Simulation execution state
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<SimulationRunResponse | null>(null);
  const [selectedResult, setSelectedResult] = useState<ScenarioRunResult | null>(null);
  const [runMode, setRunMode] = useState<"BASELINE_VS_PACE" | "PACE_ONLY" | "BASELINE_ONLY">("BASELINE_VS_PACE");

  // --- Dataset Manager State ---
  const [datasets, setDatasets] = useState<EvaluationDatasetSummary[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState(false);
  const [datasetListError, setDatasetListError] = useState<string | null>(null);
  const [isPermissionDenied, setIsPermissionDenied] = useState(false);
  const [datasetSearchQuery, setDatasetSearchQuery] = useState("");

  // Selected Dataset Detail State
  const [selectedDatasetName, setSelectedDatasetName] = useState<string | null>(null);
  const [datasetDetail, setDatasetDetail] = useState<EvaluationDatasetDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [recordFilterLabel, setRecordFilterLabel] = useState<"ALL" | "SAFE" | "RISKY">("ALL");

  // Import Modal & File Picker State
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importJsonPreview, setImportJsonPreview] = useState<any | null>(null);
  const [fileValidationError, setFileValidationError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResponse | null>(null);
  const [importApiError, setImportApiError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Dataset Comparative Evaluation State (Phase 6)
  const [showDatasetRunModal, setShowDatasetRunModal] = useState(false);
  const [isDatasetRunning, setIsDatasetRunning] = useState(false);
  const [datasetRunResponse, setDatasetRunResponse] = useState<SimulationRunResponse | null>(null);
  const [datasetRunError, setDatasetRunError] = useState<string | null>(null);

  // --------------------------------------------------------------------------
  // Scenario Loading
  // --------------------------------------------------------------------------
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

  // --------------------------------------------------------------------------
  // Dataset Manager Data Fetching
  // --------------------------------------------------------------------------
  const loadDatasets = async () => {
    try {
      setLoadingDatasets(true);
      setDatasetListError(null);
      setIsPermissionDenied(false);
      const data: EvaluationDatasetSummary[] = await fetchApi("/simulation/eval-data");
      setDatasets(data || []);
      if (data && data.length > 0 && !selectedDatasetName) {
        setSelectedDatasetName(data[0].dataset_name);
      }
    } catch (err: any) {
      const errMsg = err?.message || String(err);
      if (errMsg.toLowerCase().includes("forbidden") || errMsg.toLowerCase().includes("insufficient privileges") || errMsg.toLowerCase().includes("agent")) {
        setIsPermissionDenied(true);
      } else {
        setDatasetListError(errMsg);
      }
    } finally {
      setLoadingDatasets(false);
    }
  };

  useEffect(() => {
    if (activeMainTab === "datasets") {
      loadDatasets();
    }
  }, [activeMainTab]);

  const loadDatasetDetail = async (datasetName: string) => {
    try {
      setLoadingDetail(true);
      setDetailError(null);
      const data: EvaluationDatasetDetail = await fetchApi(`/simulation/eval-data/${encodeURIComponent(datasetName)}`);
      setDatasetDetail(data);
    } catch (err: any) {
      setDetailError(err?.message || "Failed to load evaluation dataset details.");
      setDatasetDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    if (selectedDatasetName) {
      loadDatasetDetail(selectedDatasetName);
      setDatasetRunResponse(null);
      setDatasetRunError(null);
    } else {
      setDatasetDetail(null);
    }
  }, [selectedDatasetName]);

  const handleStartDatasetSimulation = async () => {
    if (!datasetDetail) return;
    try {
      setIsDatasetRunning(true);
      setDatasetRunError(null);
      const res: SimulationRunResponse = await fetchApi("/simulation/runs", {
        method: "POST",
        body: JSON.stringify({
          dataset_name: datasetDetail.dataset_name,
          mode: "BASELINE_VS_PACE"
        })
      });
      setDatasetRunResponse(res);
      setShowDatasetRunModal(false);
    } catch (err: any) {
      setDatasetRunError(err?.message || "Failed to execute dataset comparative simulation.");
    } finally {
      setIsDatasetRunning(false);
    }
  };

  // --------------------------------------------------------------------------
  // File Upload & JSON Benchmark Parsing
  // --------------------------------------------------------------------------
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setImportResult(null);
    setImportApiError(null);
    setFileValidationError(null);

    if (!file) {
      setImportFile(null);
      setImportJsonPreview(null);
      return;
    }

    // 1. Validate file extension
    if (!file.name.toLowerCase().endsWith(".json")) {
      setFileValidationError("Invalid file extension. Please select a .json benchmark file.");
      setImportFile(null);
      setImportJsonPreview(null);
      return;
    }

    // 2. Validate file size (max 5MB)
    const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFileValidationError(`File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 5 MB limit.`);
      setImportFile(null);
      setImportJsonPreview(null);
      return;
    }

    setImportFile(file);

    // 3. Parse JSON & inspect preview
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);

        // Basic structural validation
        if (!parsed.dataset_name || typeof parsed.dataset_name !== "string") {
          setFileValidationError("JSON must include a valid string field 'dataset_name'.");
        } else if (!parsed.records || !Array.isArray(parsed.records)) {
          setFileValidationError("JSON must include a 'records' array of evaluation items.");
        } else if (parsed.records.length === 0) {
          setFileValidationError("Dataset must contain at least one evaluation record.");
        }

        setImportJsonPreview(parsed);
      } catch (jsonErr: any) {
        setFileValidationError(`Invalid JSON syntax: ${jsonErr.message}`);
        setImportJsonPreview(null);
      }
    };
    reader.readAsText(file);
  };

  const handleImportSubmit = async () => {
    if (!importJsonPreview || fileValidationError) return;

    try {
      setIsImporting(true);
      setImportResult(null);
      setImportApiError(null);

      const res: ImportResponse = await fetchApi("/simulation/eval-data/import", {
        method: "POST",
        body: JSON.stringify(importJsonPreview)
      });

      setImportResult(res);

      if (res.status === "SUCCESS") {
        // Refresh dataset list and auto-select newly imported dataset
        await loadDatasets();
        setSelectedDatasetName(res.dataset_name);
      }
    } catch (err: any) {
      setImportApiError(err?.message || "Import failed due to server error.");
    } finally {
      setIsImporting(false);
    }
  };

  const resetImportForm = () => {
    setImportFile(null);
    setImportJsonPreview(null);
    setFileValidationError(null);
    setImportResult(null);
    setImportApiError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // --------------------------------------------------------------------------
  // Simulation Benchmark Handlers
  // --------------------------------------------------------------------------
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

  // Filter datasets by search query
  const filteredDatasets = datasets.filter(ds =>
    ds.dataset_name.toLowerCase().includes(datasetSearchQuery.toLowerCase()) ||
    (ds.description && ds.description.toLowerCase().includes(datasetSearchQuery.toLowerCase())) ||
    ds.tags.some(t => t.toLowerCase().includes(datasetSearchQuery.toLowerCase()))
  );

  // Filter records by ground truth label
  const filteredRecords = (datasetDetail?.records || []).filter(rec => {
    if (recordFilterLabel === "ALL") return true;
    return rec.ground_truth_label === recordFilterLabel;
  });

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
            Deterministic baseline-versus-PACE comparative simulation, early lead-time tracking, and durable evaluation dataset registry.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2.5">
          {activeMainTab === "scenarios" ? (
            <>
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
            </>
          ) : (
            <>
              <button
                onClick={loadDatasets}
                disabled={loadingDatasets}
                className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-bold text-[#1F1F1F] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] hover:bg-[#FCFCFA] shadow-xs cursor-pointer transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-[#666666] ${loadingDatasets ? "animate-spin" : ""}`} />
                Refresh
              </button>
              <button
                onClick={() => {
                  resetImportForm();
                  setShowImportModal(true);
                }}
                className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-bold text-[#FFFFFF] bg-[#2E9D50] hover:bg-[#237A3C] rounded-[8px] shadow-sm cursor-pointer transition-colors"
              >
                <UploadCloud className="w-4 h-4" />
                Import Dataset (JSON)
              </button>
            </>
          )}
        </div>
      </div>

      {/* Primary Section Switcher Tabs */}
      <div className="flex items-center gap-2 border-b border-[#E8E8E4] pb-2">
        <button
          onClick={() => setActiveMainTab("scenarios")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-[8px] text-[12px] font-bold transition-colors cursor-pointer ${
            activeMainTab === "scenarios"
              ? "bg-[#2E9D50] text-[#FFFFFF] shadow-xs"
              : "bg-[#FFFFFF] text-[#666666] border border-[#E8E8E4] hover:bg-[#FCFCFA]"
          }`}
        >
          <Layers className="w-4 h-4" />
          Scenario Benchmarks
        </button>
        <button
          onClick={() => setActiveMainTab("datasets")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-[8px] text-[12px] font-bold transition-colors cursor-pointer ${
            activeMainTab === "datasets"
              ? "bg-[#2E9D50] text-[#FFFFFF] shadow-xs"
              : "bg-[#FFFFFF] text-[#666666] border border-[#E8E8E4] hover:bg-[#FCFCFA]"
          }`}
        >
          <Database className="w-4 h-4" />
          Evaluation Datasets
          {datasets.length > 0 && (
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                activeMainTab === "datasets" ? "bg-[#FFFFFF]/25 text-[#FFFFFF]" : "bg-[#EAF7EE] text-[#237A3C]"
              }`}
            >
              {datasets.length}
            </span>
          )}
        </button>
      </div>

      {/* ==================================================================== */}
      {/* VIEW 1: SCENARIO BENCHMARKS & PACE SIMULATION RUNNER                  */}
      {/* ==================================================================== */}
      {activeMainTab === "scenarios" && (
        <div className="space-y-6">
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
                      vs {(currentRun.metrics.baseline_metrics.f1_score * 100).toFixed(1)}% base
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
                      vs {(currentRun.metrics.baseline_metrics.precision * 100).toFixed(1)}% base
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
                      vs {(currentRun.metrics.baseline_metrics.recall * 100).toFixed(1)}% base
                    </span>
                  </div>
                </div>

                <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                  <span className="text-[10px] text-[#666666] uppercase block font-bold">False Positive Rate</span>
                  <div className="flex items-baseline gap-1.5 mt-0.5">
                    <span className="text-[17px] font-bold text-[#2E9D50]">
                      {(currentRun.metrics.pace_metrics.false_positive_rate * 100).toFixed(1)}%
                    </span>
                    <span className="text-[10px] text-[#666666]">
                      vs {(currentRun.metrics.baseline_metrics.false_positive_rate * 100).toFixed(1)}% base
                    </span>
                  </div>
                </div>

                <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                  <span className="text-[10px] text-[#666666] uppercase block font-bold">False Negative Rate</span>
                  <div className="flex items-baseline gap-1.5 mt-0.5">
                    <span className="text-[17px] font-bold text-[#2E9D50]">
                      {(currentRun.metrics.pace_metrics.false_negative_rate * 100).toFixed(1)}%
                    </span>
                    <span className="text-[10px] text-[#666666]">
                      vs {(currentRun.metrics.baseline_metrics.false_negative_rate * 100).toFixed(1)}% base
                    </span>
                  </div>
                </div>

                <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                  <span className="text-[10px] text-[#666666] uppercase block font-bold">Avg Early Lead</span>
                  <div className="flex items-baseline gap-1.5 mt-0.5">
                    <span className="text-[17px] font-bold text-[#2E9D50]">
                      +{currentRun.metrics.avg_detection_lead_steps.toFixed(1)}
                    </span>
                    <span className="text-[10px] text-[#666666]">steps before breach</span>
                  </div>
                </div>
              </div>

              {/* Transparent Disclosure */}
              <div className="text-[11px] text-[#666666] bg-[#FCFCFA] p-3 rounded-[8px] border border-[#E8E8E4]">
                <span className="font-bold text-[#1F1F1F]">Benchmark Limitations:</span> {currentRun.metrics.evaluation_limitations}
              </div>
            </div>
          )}

          {/* Scenarios Master-Detail Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Left Column: Scenario List */}
            <div className="space-y-3">
              <h2 className="text-[13px] font-bold text-[#1F1F1F] uppercase font-mono tracking-wider">
                Scenario Suite ({scenarios.length})
              </h2>

              {loadingScenarios ? (
                <div className="p-6 text-center text-[#666666] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px]">
                  Loading scenario library...
                </div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                  {scenarios.map((sc) => {
                    const isSelected = activeScenario?.scenario_id === sc.scenario_id;
                    const isRisky = sc.ground_truth_label === "RISKY";
                    return (
                      <div
                        key={sc.scenario_id}
                        onClick={() => setActiveScenario(sc)}
                        className={`p-3.5 rounded-[10px] border transition-all cursor-pointer ${
                          isSelected
                            ? "bg-[#FCFCFA] border-[#2E9D50] shadow-xs"
                            : "bg-[#FFFFFF] border-[#E8E8E4] hover:border-[#CCCCCC]"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-mono text-[#666666]">{sc.scenario_id}</span>
                          <span
                            className={`text-[9px] font-bold uppercase px-1.5 py-0.2 rounded ${
                              isRisky ? "bg-[#FDE8E8] text-[#9C1C1C]" : "bg-[#EAF7EE] text-[#237A3C]"
                            }`}
                          >
                            {sc.ground_truth_label}
                          </span>
                        </div>
                        <h3 className="text-[12px] font-bold text-[#1F1F1F] mt-1">{sc.title}</h3>
                        <p className="text-[11px] text-[#666666] mt-0.5 line-clamp-2">{sc.description}</p>
                        <div className="flex items-center gap-2 mt-2 text-[10px] text-[#666666]">
                          <span>Agent: {sc.agent_profile.agent_code}</span>
                          <span>&bull;</span>
                          <span>{sc.action_sequence.length} actions</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Column: Scenario Detail & Action Sequence Inspection */}
            <div className="md:col-span-2 space-y-4">
              {activeScenario ? (
                <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 shadow-sm space-y-5">
                  {/* Scenario Header */}
                  <div className="border-b border-[#E8E8E4] pb-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] font-mono font-bold text-[#2E9D50]">
                        {activeScenario.scenario_id} (v{activeScenario.version})
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded text-[#666666]">
                        Provenance: {activeScenario.provenance}
                      </span>
                    </div>
                    <h2 className="text-[16px] font-bold text-[#1F1F1F] mt-1">{activeScenario.title}</h2>
                    <p className="text-[12px] text-[#666666] mt-1">{activeScenario.description}</p>
                  </div>

                  {/* Agent Profile & Expected Outcomes */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[12px]">
                    <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                      <span className="text-[10px] uppercase font-bold text-[#666666] block">Agent Profile</span>
                      <p className="font-bold text-[#1F1F1F]">{activeScenario.agent_profile.name} ({activeScenario.agent_profile.agent_code})</p>
                      <p className="text-[11px] text-[#666666]">
                        Autonomy: <span className="font-mono text-[#1F1F1F]">{activeScenario.agent_profile.autonomy_level}</span> | Dept: {activeScenario.agent_profile.department}
                      </p>
                    </div>

                    <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-1">
                      <span className="text-[10px] uppercase font-bold text-[#666666] block">Benchmark Ground Truth</span>
                      <p className="font-bold text-[#1F1F1F]">
                        Label:{" "}
                        <span className={activeScenario.ground_truth_label === "RISKY" ? "text-[#E05656]" : "text-[#2E9D50]"}>
                          {activeScenario.ground_truth_label}
                        </span>
                      </p>
                      <p className="text-[11px] text-[#666666]">
                        Expected Intervention: <span className="font-mono text-[#1F1F1F]">{activeScenario.expected_pace_intervention}</span>
                      </p>
                    </div>
                  </div>

                  {/* Action Sequence Timeline */}
                  <div>
                    <h3 className="text-[12px] font-bold text-[#1F1F1F] uppercase font-mono tracking-wider mb-2.5">
                      Evaluated Action Sequence Timeline ({activeScenario.action_sequence.length} steps)
                    </h3>
                    <div className="space-y-2">
                      {activeScenario.action_sequence.map((step) => (
                        <div
                          key={step.step_index}
                          className="p-3 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] space-y-1 text-[12px]"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-[#2E9D50]">Step #{step.step_index}</span>
                              <span className="font-mono px-1.5 py-0.2 bg-[#FCFCFA] border border-[#E8E8E4] rounded text-[11px]">
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
                          <p className="text-[11px] text-[#666666] italic">&quot;{step.prompt}&quot;</p>
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
      )}

      {/* ==================================================================== */}
      {/* VIEW 2: EVALUATION DATASET MANAGER (Phase 5.2)                        */}
      {/* ==================================================================== */}
      {activeMainTab === "datasets" && (
        <div className="space-y-6">
          {/* Permission Denied Banner (if non-authorized role) */}
          {isPermissionDenied && (
            <div className="bg-[#FFF4E5] border border-[#F59A23]/30 rounded-[10px] p-4 text-[12px] text-[#C45E00] flex items-center gap-3">
              <Lock className="w-5 h-5 text-[#F59A23] shrink-0" />
              <div>
                <p className="font-bold">Access Restricted</p>
                <p>
                  Access to evaluation datasets is restricted to authorized human roles (ADMIN, SECURITY_OFFICER, MANAGER, AUDITOR). Machine identities (AGENT) cannot manage evaluation datasets.
                </p>
              </div>
            </div>
          )}

          {/* Dataset Manager Overview Header Banner */}
          <div className="bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] p-3.5 text-[12px] text-[#666666] flex items-start gap-3">
            <Database className="w-4 h-4 text-[#2E9D50] shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <p className="font-bold text-[#1F1F1F]">Durable Evaluation Dataset Registry</p>
              <p>
                Evaluation datasets contain authorized, ground-truth labeled action traces stored durably in the organization database. Datasets survive backend restarts and are segregated from live production telemetry.
              </p>
            </div>
          </div>

          {/* Master-Detail Layout */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Left Column: Datasets List */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-[13px] font-bold text-[#1F1F1F] uppercase font-mono tracking-wider">
                  Datasets ({filteredDatasets.length})
                </h2>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-[#666666] absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search datasets by name or tag..."
                  value={datasetSearchQuery}
                  onChange={(e) => setDatasetSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-[12px] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
                />
              </div>

              {/* Dataset Cards List */}
              {loadingDatasets ? (
                <div className="p-8 text-center text-[#666666] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-2">
                  <RefreshCw className="w-4 h-4 animate-spin mx-auto text-[#2E9D50]" />
                  <p className="text-[12px]">Loading evaluation datasets...</p>
                </div>
              ) : datasetListError ? (
                <div className="p-4 text-center text-[#9C1C1C] bg-[#FDE8E8] border border-[#E05656]/30 rounded-[10px] space-y-2">
                  <AlertCircle className="w-4 h-4 mx-auto text-[#E05656]" />
                  <p className="text-[12px] font-bold">Failed to load datasets</p>
                  <p className="text-[11px]">{datasetListError}</p>
                  <button
                    onClick={loadDatasets}
                    className="mt-2 text-[11px] font-bold underline cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              ) : filteredDatasets.length === 0 ? (
                <div className="p-8 text-center text-[#666666] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-3">
                  <Database className="w-6 h-6 mx-auto text-[#94A3B8]" />
                  <div className="space-y-1">
                    <p className="text-[13px] font-bold text-[#1F1F1F]">No Evaluation Datasets Found</p>
                    <p className="text-[11px]">
                      {datasetSearchQuery
                        ? "No datasets match your filter query."
                        : "Import a labeled benchmark JSON file to persist and review action sequences."}
                    </p>
                  </div>
                  {!datasetSearchQuery && (
                    <button
                      onClick={() => {
                        resetImportForm();
                        setShowImportModal(true);
                      }}
                      className="px-3 py-1.5 text-[11px] font-bold text-[#2E9D50] border border-[#2E9D50] hover:bg-[#EAF7EE] rounded-[6px] transition-colors cursor-pointer"
                    >
                      Import Benchmark JSON
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                  {filteredDatasets.map((ds) => {
                    const isSelected = selectedDatasetName === ds.dataset_name;
                    return (
                      <div
                        key={ds.dataset_name}
                        onClick={() => setSelectedDatasetName(ds.dataset_name)}
                        className={`p-3.5 rounded-[10px] border transition-all cursor-pointer ${
                          isSelected
                            ? "bg-[#FCFCFA] border-[#2E9D50] shadow-xs"
                            : "bg-[#FFFFFF] border-[#E8E8E4] hover:border-[#CCCCCC]"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] font-mono font-bold text-[#1F1F1F] truncate">
                            {ds.dataset_name}
                          </span>
                          <span className="text-[9px] font-bold uppercase px-1.5 py-0.2 bg-[#EAF7EE] text-[#237A3C] rounded whitespace-nowrap">
                            {ds.records_count} records
                          </span>
                        </div>

                        {ds.description && (
                          <p className="text-[11px] text-[#666666] mt-1 line-clamp-2">{ds.description}</p>
                        )}

                        <div className="flex flex-wrap items-center gap-1 mt-2">
                          <span className="text-[9px] font-mono px-1.5 py-0.2 bg-[#FCFCFA] text-[#666666] border border-[#E8E8E4] rounded">
                            {ds.provenance}
                          </span>
                          {ds.tags.slice(0, 3).map((tag) => (
                            <span
                              key={tag}
                              className="text-[9px] font-mono px-1.5 py-0.2 bg-[#FCFCFA] text-[#666666] border border-[#E8E8E4] rounded"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>

                        <div className="flex items-center justify-between mt-2 pt-1 border-t border-[#E8E8E4]/50 text-[10px] text-[#94A3B8]">
                          <span>
                            Created {new Date(ds.created_at).toLocaleDateString()}
                          </span>
                          <span className="text-[#2E9D50] font-bold flex items-center gap-0.5">
                            Inspect <ChevronRight className="w-3 h-3" />
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Column: Dataset Detail & Records View */}
            <div className="md:col-span-2 space-y-4">
              {loadingDetail ? (
                <div className="p-12 text-center text-[#666666] bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] space-y-2">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto text-[#2E9D50]" />
                  <p className="text-[13px] font-bold text-[#1F1F1F]">Loading dataset records...</p>
                </div>
              ) : detailError ? (
                <div className="p-6 text-center text-[#9C1C1C] bg-[#FDE8E8] border border-[#E05656]/30 rounded-[12px] space-y-2">
                  <AlertCircle className="w-5 h-5 mx-auto text-[#E05656]" />
                  <p className="text-[13px] font-bold">Failed to load dataset details</p>
                  <p className="text-[11px]">{detailError}</p>
                </div>
              ) : datasetDetail ? (
                <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-5 shadow-sm space-y-5">
                  {/* Dataset Detail Header */}
                  <div className="border-b border-[#E8E8E4] pb-4">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-[#2E9D50]" />
                        <h2 className="text-[16px] font-bold text-[#1F1F1F] font-mono">
                          {datasetDetail.dataset_name}
                        </h2>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded font-bold">
                        {datasetDetail.records.length} Labeled Records
                      </span>
                    </div>

                    {datasetDetail.description && (
                      <p className="text-[12px] text-[#666666] mt-1.5">{datasetDetail.description}</p>
                    )}

                    <div className="flex flex-wrap items-center gap-3 mt-3 text-[11px] text-[#666666]">
                      <div>
                        Provenance: <span className="font-mono text-[#1F1F1F]">{datasetDetail.provenance}</span>
                      </div>
                      <span>&bull;</span>
                      <div>
                        Created: <span className="text-[#1F1F1F]">{new Date(datasetDetail.created_at).toLocaleString()}</span>
                      </div>
                      {datasetDetail.updated_at && (
                        <>
                          <span>&bull;</span>
                          <div>
                            Updated: <span className="text-[#1F1F1F]">{new Date(datasetDetail.updated_at).toLocaleString()}</span>
                          </div>
                        </>
                      )}
                    </div>

                    {datasetDetail.tags.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                        {datasetDetail.tags.map(t => (
                          <span
                            key={t}
                            className="text-[10px] font-mono px-2 py-0.5 bg-[#FCFCFA] text-[#666666] border border-[#E8E8E4] rounded"
                          >
                            #{t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Error Alert Banner */}
                  {datasetRunError && (
                    <div className="bg-[#FDE8E8] border border-[#E05656]/30 rounded-[10px] p-4 text-[12px] text-[#9C1C1C] flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 shrink-0 text-[#E05656]" />
                        <span>{datasetRunError}</span>
                      </div>
                      <button
                        onClick={() => setDatasetRunError(null)}
                        className="text-[11px] font-bold underline hover:no-underline cursor-pointer"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}

                  {/* Running State Banner */}
                  {isDatasetRunning && (
                    <div className="bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-[10px] p-6 text-center space-y-2">
                      <RefreshCw className="w-6 h-6 animate-spin text-[#2E9D50] mx-auto" />
                      <h4 className="text-[13px] font-bold text-[#1F1F1F]">
                        Running Baseline vs. PACE Comparative Simulation...
                      </h4>
                      <p className="text-[11px] text-[#666666] max-w-lg mx-auto">
                        Evaluating {datasetDetail.records.length} persisted records from &quot;{datasetDetail.dataset_name}&quot; through isolated in-memory baseline and PACE decision engines. Zero external tools are called.
                      </p>
                    </div>
                  )}

                  {/* Completed Dataset Simulation Results View (Phase 6) */}
                  {datasetRunResponse && datasetRunResponse.metrics && !isDatasetRunning && (
                    <div className="bg-[#FFFFFF] border-2 border-[#2E9D50]/40 rounded-[12px] p-5 space-y-4 shadow-sm">
                      {/* Results Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E8E8E4] pb-3">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-[14px] text-[#1F1F1F]">
                              Comparative Simulation Results: {datasetRunResponse.dataset_name}
                            </span>
                            <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] rounded">
                              {datasetRunResponse.dataset_provenance || "AUTHORIZED_LABELED_DATA"}
                            </span>
                          </div>
                          <p className="text-[11px] text-[#666666]">
                            Run ID: <span className="font-mono text-[#1F1F1F]">{datasetRunResponse.run_id}</span> &bull; Status: <span className="font-bold text-[#2E9D50]">{datasetRunResponse.status}</span> &bull; Runtime: {datasetRunResponse.metrics.runtime_ms}ms &bull; Method: {datasetRunResponse.metrics.evaluation_method}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setShowDatasetRunModal(true)}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold text-[#FFFFFF] bg-[#2E9D50] hover:bg-[#237A3C] rounded-[6px] cursor-pointer shadow-sm"
                          >
                            <Play className="w-3.5 h-3.5" />
                            Run Again
                          </button>
                          <button
                            onClick={() => setDatasetRunResponse(null)}
                            className="px-3 py-1.5 text-[11px] font-bold text-[#666666] bg-[#FCFCFA] border border-[#E8E8E4] hover:bg-[#F1F1EF] rounded-[6px] cursor-pointer"
                          >
                            Close Results
                          </button>
                        </div>
                      </div>

                      {/* Excluded Records Alert Banner (If partial validation) */}
                      {datasetRunResponse.records_excluded !== undefined && datasetRunResponse.records_excluded > 0 && (
                        <div className="bg-[#FFF4E5] border border-[#F59A23]/30 rounded-[8px] p-3 text-[11px] text-[#C45E00] space-y-1">
                          <div className="flex items-center gap-1.5 font-bold">
                            <AlertTriangle className="w-4 h-4 text-[#F59A23]" />
                            <span>Excluded Records Notice: {datasetRunResponse.records_excluded} record(s) omitted due to validation constraints</span>
                          </div>
                          {datasetRunResponse.validation_report?.unsupported_records && (
                            <ul className="list-disc pl-5 text-[10px] space-y-0.5">
                              {datasetRunResponse.validation_report.unsupported_records.map((r, i) => (
                                <li key={i}>
                                  <span className="font-mono font-bold">{r.record_id}</span>: {r.error}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}

                      {/* Metric Comparison Cards Grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                          <span className="text-[10px] font-bold text-[#666666] uppercase block">Records Evaluated</span>
                          <span className="text-[18px] font-mono font-bold text-[#1F1F1F]">
                            {datasetRunResponse.records_evaluated} / {datasetRunResponse.records_total}
                          </span>
                        </div>
                        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                          <span className="text-[10px] font-bold text-[#666666] uppercase block">Accuracy (Base / PACE)</span>
                          <div className="flex items-baseline gap-1 text-[16px] font-mono font-bold">
                            <span className="text-[#666666]">
                              {((datasetRunResponse.metrics.baseline_metrics.accuracy || 0) * 100).toFixed(0)}%
                            </span>
                            <span className="text-[#CCCCCC]">&rarr;</span>
                            <span className="text-[#2E9D50]">
                              {((datasetRunResponse.metrics.pace_metrics.accuracy || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                          <span className="text-[10px] font-bold text-[#666666] uppercase block">Precision (Base / PACE)</span>
                          <div className="flex items-baseline gap-1 text-[16px] font-mono font-bold">
                            <span className="text-[#666666]">
                              {((datasetRunResponse.metrics.baseline_metrics.precision || 0) * 100).toFixed(0)}%
                            </span>
                            <span className="text-[#CCCCCC]">&rarr;</span>
                            <span className="text-[#2E9D50]">
                              {((datasetRunResponse.metrics.pace_metrics.precision || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                          <span className="text-[10px] font-bold text-[#666666] uppercase block">Recall (Base / PACE)</span>
                          <div className="flex items-baseline gap-1 text-[16px] font-mono font-bold">
                            <span className="text-[#666666]">
                              {((datasetRunResponse.metrics.baseline_metrics.recall || 0) * 100).toFixed(0)}%
                            </span>
                            <span className="text-[#CCCCCC]">&rarr;</span>
                            <span className="text-[#2E9D50]">
                              {((datasetRunResponse.metrics.pace_metrics.recall || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                          <span className="text-[10px] font-bold text-[#666666] uppercase block">F1 Score (Base / PACE)</span>
                          <div className="flex items-baseline gap-1 text-[16px] font-mono font-bold">
                            <span className="text-[#666666]">
                              {(datasetRunResponse.metrics.baseline_metrics.f1_score || 0).toFixed(2)}
                            </span>
                            <span className="text-[#CCCCCC]">&rarr;</span>
                            <span className="text-[#2E9D50]">
                              {(datasetRunResponse.metrics.pace_metrics.f1_score || 0).toFixed(2)}
                            </span>
                          </div>
                        </div>
                        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px]">
                          <span className="text-[10px] font-bold text-[#666666] uppercase block">Avg Lead Time</span>
                          <span className="text-[18px] font-mono font-bold text-[#2E9D50]">
                            {datasetRunResponse.metrics.avg_detection_lead_steps.toFixed(1)} <span className="text-[11px] font-normal text-[#666666]">steps</span>
                          </span>
                        </div>
                      </div>

                      {/* Side-by-Side Confusion Matrix */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold text-[#1F1F1F] uppercase font-mono">
                              Baseline Policy Confusion Matrix
                            </span>
                            <span className="text-[10px] text-[#666666]">
                              N = {datasetRunResponse.metrics.baseline_metrics.sample_size || datasetRunResponse.records_evaluated}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-center text-[11px] font-mono">
                            <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                              <span className="text-[9px] uppercase text-[#666666] block">True Positives</span>
                              <span className="text-[15px] font-bold text-[#2E9D50]">
                                {datasetRunResponse.metrics.baseline_metrics.true_positives}
                              </span>
                            </div>
                            <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                              <span className="text-[9px] uppercase text-[#666666] block">False Positives</span>
                              <span className="text-[15px] font-bold text-[#E05656]">
                                {datasetRunResponse.metrics.baseline_metrics.false_positives}
                              </span>
                            </div>
                            <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                              <span className="text-[9px] uppercase text-[#666666] block">False Negatives</span>
                              <span className="text-[15px] font-bold text-[#E05656]">
                                {datasetRunResponse.metrics.baseline_metrics.false_negatives}
                              </span>
                            </div>
                            <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                              <span className="text-[9px] uppercase text-[#666666] block">True Negatives</span>
                              <span className="text-[15px] font-bold text-[#2E9D50]">
                                {datasetRunResponse.metrics.baseline_metrics.true_negatives}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold text-[#2E9D50] uppercase font-mono">
                              PACE Engine Confusion Matrix
                            </span>
                            <span className="text-[10px] text-[#666666]">
                              N = {datasetRunResponse.metrics.pace_metrics.sample_size || datasetRunResponse.records_evaluated}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-center text-[11px] font-mono">
                            <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                              <span className="text-[9px] uppercase text-[#666666] block">True Positives</span>
                              <span className="text-[15px] font-bold text-[#2E9D50]">
                                {datasetRunResponse.metrics.pace_metrics.true_positives}
                              </span>
                            </div>
                            <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                              <span className="text-[9px] uppercase text-[#666666] block">False Positives</span>
                              <span className="text-[15px] font-bold text-[#E05656]">
                                {datasetRunResponse.metrics.pace_metrics.false_positives}
                              </span>
                            </div>
                            <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                              <span className="text-[9px] uppercase text-[#666666] block">False Negatives</span>
                              <span className="text-[15px] font-bold text-[#E05656]">
                                {datasetRunResponse.metrics.pace_metrics.false_negatives}
                              </span>
                            </div>
                            <div className="p-2 bg-[#FFFFFF] border border-[#E8E8E4] rounded">
                              <span className="text-[9px] uppercase text-[#666666] block">True Negatives</span>
                              <span className="text-[15px] font-bold text-[#2E9D50]">
                                {datasetRunResponse.metrics.pace_metrics.true_negatives}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Per-Record Decision Comparison Table */}
                      <div className="space-y-2">
                        <span className="text-[11px] font-bold text-[#1F1F1F] uppercase font-mono block">
                          Record-Level Decision Outcomes ({datasetRunResponse.results.length})
                        </span>
                        <div className="border border-[#E8E8E4] rounded-[8px] overflow-x-auto">
                          <table className="w-full text-left border-collapse text-[11px]">
                            <thead>
                              <tr className="bg-[#FCFCFA] border-b border-[#E8E8E4] text-[#666666] font-mono text-[10px] uppercase">
                                <th className="p-2">Record ID</th>
                                <th className="p-2">Ground Truth</th>
                                <th className="p-2">Baseline Decision</th>
                                <th className="p-2">PACE Decision</th>
                                <th className="p-2">PACE Intervention</th>
                                <th className="p-2">Lead Steps</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[#E8E8E4]">
                              {datasetRunResponse.results.map((res) => (
                                <tr key={res.scenario_id} className="hover:bg-[#FCFCFA]">
                                  <td className="p-2 font-mono font-bold text-[#1F1F1F]">
                                    {res.scenario_id.includes(":") ? res.scenario_id.split(":")[1] : res.scenario_id}
                                  </td>
                                  <td className="p-2">
                                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                      res.ground_truth_label === "RISKY" ? "bg-[#FDE8E8] text-[#9C1C1C]" : "bg-[#EAF7EE] text-[#237A3C]"
                                    }`}>
                                      {res.ground_truth_label}
                                    </span>
                                  </td>
                                  <td className="p-2">
                                    <span className="font-mono">{res.baseline_final_decision}</span>
                                    {res.baseline_matches_ground_truth ? (
                                      <span className="text-[#2E9D50] ml-1 font-bold">&check;</span>
                                    ) : (
                                      <span className="text-[#E05656] ml-1 font-bold">&cross;</span>
                                    )}
                                  </td>
                                  <td className="p-2">
                                    <span className="font-mono">{res.pace_final_decision}</span>
                                    {res.pace_matches_ground_truth ? (
                                      <span className="text-[#2E9D50] ml-1 font-bold">&check;</span>
                                    ) : (
                                      <span className="text-[#E05656] ml-1 font-bold">&cross;</span>
                                    )}
                                  </td>
                                  <td className="p-2 font-mono text-[10px]">
                                    {res.pace_selected_intervention}
                                  </td>
                                  <td className="p-2 font-mono text-[11px]">
                                    {res.early_detection_lead_steps > 0 ? (
                                      <span className="font-bold text-[#2E9D50]">+{res.early_detection_lead_steps} steps</span>
                                    ) : (
                                      <span className="text-[#666666]">0</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Evaluation Limitations Disclosure */}
                      <div className="p-3 bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] text-[10px] text-[#666666] flex items-start gap-2">
                        <Info className="w-4 h-4 text-[#94A3B8] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold text-[#1F1F1F] block">Evaluation Disclaimer & Integrity Boundary:</span>
                          <p>{datasetRunResponse.metrics.evaluation_limitations}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Comparative Simulation Callout Banner (Phase 6 Live Action) */}
                  {!datasetRunResponse && !isDatasetRunning && (
                    <div className="bg-[#FCFCFA] border border-[#E8E8E4] rounded-[10px] p-4 text-[12px] space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <BarChart2 className="w-4 h-4 text-[#2E9D50]" />
                          <span className="font-bold text-[#1F1F1F]">Dataset-Driven Comparative Simulation</span>
                        </div>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-[#EAF7EE] text-[#237A3C] border border-[#2E9D50]/30 rounded">
                          ACTIVE &bull; PHASE 6
                        </span>
                      </div>
                      <p className="text-[11px] text-[#666666]">
                        Execute a deterministic baseline static policy evaluation alongside the Predictive Action Control Engine (PACE) over all {datasetDetail.records.length} persisted records in this dataset. Execution occurs strictly within an in-memory simulation sandbox without real tool calls or production state changes.
                      </p>
                      <div className="pt-1">
                        <button
                          type="button"
                          onClick={() => setShowDatasetRunModal(true)}
                          className="flex items-center gap-1.5 px-3.5 py-1.5 text-[11px] font-bold text-[#FFFFFF] bg-[#2E9D50] hover:bg-[#237A3C] rounded-[6px] shadow-sm cursor-pointer transition-colors"
                        >
                          <Play className="w-3.5 h-3.5" />
                          Run Comparative Simulation ({datasetDetail.records.length} Records)
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Records Inspection Filter Toolbar */}
                  <div className="flex items-center justify-between gap-2 pt-1 border-t border-[#E8E8E4]">
                    <h3 className="text-[12px] font-bold text-[#1F1F1F] uppercase font-mono tracking-wider">
                      Evaluation Records ({filteredRecords.length})
                    </h3>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] text-[#666666]">Filter Label:</span>
                      {(["ALL", "SAFE", "RISKY"] as const).map((lbl) => (
                        <button
                          key={lbl}
                          onClick={() => setRecordFilterLabel(lbl)}
                          className={`px-2 py-0.5 text-[10px] font-bold rounded cursor-pointer transition-colors ${
                            recordFilterLabel === lbl
                              ? "bg-[#2E9D50] text-[#FFFFFF]"
                              : "bg-[#FFFFFF] text-[#666666] border border-[#E8E8E4] hover:bg-[#FCFCFA]"
                          }`}
                        >
                          {lbl}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Records List */}
                  <div className="space-y-3">
                    {filteredRecords.map((rec) => {
                      const isRisky = rec.ground_truth_label === "RISKY";
                      return (
                        <div
                          key={rec.record_id}
                          className="p-4 bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] space-y-3 text-[12px]"
                        >
                          {/* Record Card Header */}
                          <div className="flex items-center justify-between border-b border-[#E8E8E4]/60 pb-2">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-[#1F1F1F]">{rec.record_id}</span>
                              <span
                                className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                                  isRisky ? "bg-[#FDE8E8] text-[#9C1C1C]" : "bg-[#EAF7EE] text-[#237A3C]"
                                }`}
                              >
                                Ground Truth: {rec.ground_truth_label}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono text-[#666666]">{rec.provenance}</span>
                          </div>

                          {/* Agent Profile & Notes */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
                            <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded">
                              <span className="font-bold text-[#666666] block text-[10px] uppercase">Agent Target</span>
                              <p className="font-bold text-[#1F1F1F] mt-0.5">
                                {rec.agent_profile.name} ({rec.agent_profile.agent_code})
                              </p>
                              <p className="text-[#666666] mt-0.5">
                                Autonomy: <span className="font-mono text-[#1F1F1F]">{rec.agent_profile.autonomy_level}</span>
                                {rec.agent_profile.daily_budget !== undefined && (
                                  <span> | Daily Budget: ₹{rec.agent_profile.daily_budget.toLocaleString()}</span>
                                )}
                              </p>
                            </div>

                            <div className="p-2.5 bg-[#FCFCFA] border border-[#E8E8E4] rounded">
                              <span className="font-bold text-[#666666] block text-[10px] uppercase">Audit Notes</span>
                              <p className="text-[#666666] mt-0.5 italic">
                                {rec.ground_truth_notes || "No audit rationale attached to record."}
                              </p>
                            </div>
                          </div>

                          {/* Action Sequence Steps */}
                          <div className="space-y-1.5 pt-1">
                            <span className="font-bold text-[#1F1F1F] block text-[11px] font-mono">
                              Action Sequence ({rec.action_sequence.length} steps):
                            </span>
                            <div className="space-y-1.5">
                              {rec.action_sequence.map((step, sIdx) => (
                                <div
                                  key={sIdx}
                                  className="p-2 bg-[#FCFCFA] border border-[#E8E8E4] rounded flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px]"
                                >
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono font-bold text-[#2E9D50]">
                                      #{step.step_number || sIdx + 1}
                                    </span>
                                    <span className="font-mono px-1.5 py-0.2 bg-[#FFFFFF] border border-[#E8E8E4] rounded font-bold">
                                      {step.action} &rarr; {step.resource}
                                    </span>
                                    {step.operation && (
                                      <span className="text-[10px] text-[#666666]">
                                        op: {step.operation}
                                      </span>
                                    )}
                                    {step.amount !== undefined && step.amount > 0 && (
                                      <span className="text-[10px] font-mono text-[#666666]">
                                        (₹{step.amount.toLocaleString()})
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-2">
                                    {step.prompt && (
                                      <span className="text-[10px] text-[#666666] italic truncate max-w-xs">
                                        &quot;{step.prompt}&quot;
                                      </span>
                                    )}
                                    {step.is_terminal_step && (
                                      <span className="text-[9px] font-bold uppercase px-1.5 py-0.2 bg-[#FFF4E5] text-[#C45E00] rounded whitespace-nowrap">
                                        Terminal
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[10px] p-8 text-center text-[#666666]">
                  Select an evaluation dataset from the list to view its records and action sequences.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* IMPORT MODAL: JSON Benchmark Dataset Uploader (Phase 5.2)             */}
      {/* ==================================================================== */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[14px] shadow-xl max-w-xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-[#2E9D50]" />
                <h3 className="text-[15px] font-bold text-[#1F1F1F]">Import Evaluation Dataset</h3>
              </div>
              <button
                onClick={() => setShowImportModal(false)}
                className="text-[#666666] hover:text-[#1F1F1F] p-1 rounded hover:bg-[#FCFCFA] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-[12px] text-[#666666]">
              Upload an authorized JSON benchmark file containing ground-truth labeled action sequence traces.
            </p>

            {/* File Input Dropzone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-[10px] p-6 text-center cursor-pointer transition-colors ${
                importFile
                  ? "border-[#2E9D50] bg-[#EAF7EE]/20"
                  : "border-[#E8E8E4] hover:border-[#CCCCCC] bg-[#FCFCFA]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                onChange={handleFileSelect}
                className="hidden"
              />
              <FileJson className={`w-8 h-8 mx-auto mb-2 ${importFile ? "text-[#2E9D50]" : "text-[#94A3B8]"}`} />
              {importFile ? (
                <div className="space-y-1">
                  <p className="text-[12px] font-bold text-[#1F1F1F]">{importFile.name}</p>
                  <p className="text-[10px] text-[#666666]">
                    {(importFile.size / 1024).toFixed(1)} KB &bull; Click to choose a different file
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-[12px] font-bold text-[#1F1F1F]">Click or drop a benchmark JSON file</p>
                  <p className="text-[10px] text-[#666666]">Supports .json files up to 5 MB</p>
                </div>
              )}
            </div>

            {/* Client-Side Validation Error */}
            {fileValidationError && (
              <div className="bg-[#FDE8E8] border border-[#E05656]/30 rounded-[8px] p-3 text-[11px] text-[#9C1C1C] flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-[#E05656]" />
                <span>{fileValidationError}</span>
              </div>
            )}

            {/* JSON Content Preview */}
            {importJsonPreview && !fileValidationError && (
              <div className="bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] p-3 text-[11px] space-y-2">
                <span className="font-bold text-[#1F1F1F] block text-[10px] uppercase font-mono">
                  Payload Preview
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-[#666666] block">Dataset Name:</span>
                    <span className="font-bold font-mono text-[#1F1F1F]">
                      {importJsonPreview.dataset_name || "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#666666] block">Record Count:</span>
                    <span className="font-bold font-mono text-[#2E9D50]">
                      {importJsonPreview.records?.length || 0} records
                    </span>
                  </div>
                  <div>
                    <span className="text-[#666666] block">Provenance:</span>
                    <span className="font-mono text-[#1F1F1F]">
                      {importJsonPreview.provenance || "AUTHORIZED_LABELED_DATA"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#666666] block">Description:</span>
                    <span className="text-[#1F1F1F] truncate block">
                      {importJsonPreview.description || "None"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* API Result Alert Banner (Success) */}
            {importResult && importResult.status === "SUCCESS" && (
              <div className="bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-[8px] p-3 text-[11px] text-[#237A3C] space-y-1">
                <div className="flex items-center gap-1.5 font-bold">
                  <CheckCircle2 className="w-4 h-4 text-[#2E9D50]" />
                  <span>Dataset &quot;{importResult.dataset_name}&quot; Imported Successfully!</span>
                </div>
                <p>
                  Persisted {importResult.imported_records_count} evaluation records into organization database storage.
                </p>
              </div>
            )}

            {/* API Result Alert Banner (Rejection) */}
            {importResult && importResult.status === "REJECTED" && (
              <div className="bg-[#FDE8E8] border border-[#E05656]/30 rounded-[8px] p-3 text-[11px] text-[#9C1C1C] space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold">
                  <XCircle className="w-4 h-4 text-[#E05656]" />
                  <span>Import Rejected by Security Boundary</span>
                </div>
                <ul className="list-disc pl-4 space-y-0.5">
                  {importResult.validation_errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* API Network/Auth Error */}
            {importApiError && (
              <div className="bg-[#FDE8E8] border border-[#E05656]/30 rounded-[8px] p-3 text-[11px] text-[#9C1C1C] flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-[#E05656]" />
                <span>{importApiError}</span>
              </div>
            )}

            {/* Modal Action Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#E8E8E4]">
              <button
                type="button"
                onClick={() => setShowImportModal(false)}
                className="px-3.5 py-2 text-[12px] font-bold text-[#666666] bg-[#FFFFFF] border border-[#E8E8E4] hover:bg-[#FCFCFA] rounded-[8px] cursor-pointer"
              >
                {importResult?.status === "SUCCESS" ? "Close" : "Cancel"}
              </button>
              <button
                type="button"
                onClick={handleImportSubmit}
                disabled={!importJsonPreview || !!fileValidationError || isImporting || importResult?.status === "SUCCESS"}
                className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-bold text-[#FFFFFF] bg-[#2E9D50] hover:bg-[#237A3C] rounded-[8px] shadow-sm cursor-pointer transition-colors disabled:opacity-50"
              >
                {isImporting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-4 h-4" />
                    Submit Import
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* CONFIRMATION MODAL: Comparative Dataset Simulation (Phase 6)         */}
      {/* ==================================================================== */}
      {showDatasetRunModal && datasetDetail && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[14px] shadow-xl max-w-lg w-full p-6 space-y-4">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#E8E8E4] pb-3">
              <div className="flex items-center gap-2">
                <Play className="w-5 h-5 text-[#2E9D50]" />
                <h3 className="text-[15px] font-bold text-[#1F1F1F]">Confirm Comparative Simulation</h3>
              </div>
              <button
                onClick={() => setShowDatasetRunModal(false)}
                className="text-[#666666] hover:text-[#1F1F1F] p-1 rounded hover:bg-[#FCFCFA] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-[12px] text-[#666666]">
              You are about to launch a side-by-side comparative simulation evaluating a static baseline policy against the Predictive Action Control Engine (PACE).
            </p>

            {/* Target Dataset Summary */}
            <div className="bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] p-3 text-[11px] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[#666666]">Target Dataset:</span>
                <span className="font-mono font-bold text-[#1F1F1F]">{datasetDetail.dataset_name}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#666666]">Provenance:</span>
                <span className="font-mono text-[#237A3C] bg-[#EAF7EE] px-1.5 py-0.5 rounded text-[10px] font-bold">
                  {datasetDetail.provenance}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#666666]">Record Count:</span>
                <span className="font-mono font-bold text-[#2E9D50]">{datasetDetail.records.length} records</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#666666]">Evaluation Mode:</span>
                <span className="font-mono text-[#1F1F1F] font-bold">BASELINE_VS_PACE</span>
              </div>
            </div>

            {/* In-Memory Isolation Safety Guarantee */}
            <div className="bg-[#EAF7EE] border border-[#2E9D50]/30 rounded-[8px] p-3 text-[11px] text-[#237A3C] flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5 text-[#2E9D50]" />
              <div>
                <span className="font-bold block">Simulation Safety Guarantee:</span>
                <p className="text-[10px] text-[#2E9D50]/90">
                  Runs strictly within transient in-memory simulation adapters. No real tool executions, external API calls, or production AuditLog/Decision writes will occur.
                </p>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#E8E8E4]">
              <button
                type="button"
                onClick={() => setShowDatasetRunModal(false)}
                className="px-3.5 py-2 text-[12px] font-bold text-[#666666] bg-[#FFFFFF] border border-[#E8E8E4] hover:bg-[#FCFCFA] rounded-[8px] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleStartDatasetSimulation}
                disabled={isDatasetRunning}
                className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-bold text-[#FFFFFF] bg-[#2E9D50] hover:bg-[#237A3C] rounded-[8px] shadow-sm cursor-pointer transition-colors disabled:opacity-50"
              >
                {isDatasetRunning ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Launch Simulation
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
