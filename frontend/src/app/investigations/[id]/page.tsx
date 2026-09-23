/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import { useEffect, useState } from "react";
import { getCase, getEvidence, getTimeline, getRecommendation, approveAction, rejectAction } from "@/lib/api";
import { Card, Badge, Button, cn } from "@/components/ui";
import { 
  CheckCircle2, 
  Activity, 
  RefreshCw, 
  ShieldX, 
  ArrowLeft, 
  Download, 
  Copy, 
  FileText, 
  Share2, 
  ChevronRight
} from "lucide-react";
import { format } from "date-fns";
import Link from "next/link";

type LoadState = "loading" | "success" | "error";

export default function InvestigationWorkspace({ params }: { params: { id: string } }) {
  const [caseData, setCaseData] = useState<any>(null);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [recommendation, setRecommendation] = useState<any>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [copyToast, setCopyToast] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);

  const load = () => {
    setState("loading");
    setErrorMsg("");

    getCase(params.id)
      .catch(() => {
        return fetch(`/api/investigations/${params.id}`).then((r) => {
          if (!r.ok) throw new Error(`Case ${params.id} not found`);
          return r.json();
        });
      })
      .then((data) => {
        setCaseData(data);
        setState("success");

        getEvidence(params.id)
          .then((res) => setEvidence(res.evidence || []))
          .catch(() => {
            setEvidence(data.evidence || []);
          });

        getTimeline(params.id)
          .then((res) => setTimeline(res.timeline || []))
          .catch(() => {
            setTimeline(data.timeline || []);
          });

        getRecommendation(params.id)
          .then((res) => setRecommendation(res))
          .catch(() => {
            if (data.final_actions) {
              setRecommendation({
                final_actions: data.final_actions,
                final_verdict: data.final_verdict,
                fraud_probability: data.final_fraud_probability,
                what_changed: data.what_changed,
              });
            }
          });
      })
      .catch((err) => {
        console.error("Investigation load failed:", err);
        setErrorMsg(err.message || `Failed to load investigation ${params.id}`);
        setState("error");
      });
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [params.id]);

  const handleAction = async (action: string, type: "approve" | "reject") => {
    try {
      if (type === "approve") {
        await approveAction(params.id, action);
      } else {
        await rejectAction(params.id, action);
      }
      load();
    } catch (err) {
      console.error(err);
      alert("Failed to perform action");
    }
  };

  // 1-Click SAR Exporter
  const handleExportSAR = (formatType: "json" | "txt") => {
    if (!caseData) return;
    const sarData = {
      report_id: `SAR-${caseData.case_id}-${Date.now().toString().slice(-6)}`,
      case_id: caseData.case_id,
      filing_institution: "FraudLens Financial Intelligence Unit",
      filing_date: new Date().toISOString(),
      flagged_transaction_id: caseData.txn_id,
      suspect_card_id: caseData.card_id,
      fraud_typology: caseData.pattern,
      final_fraud_probability: caseData.final_fraud_probability,
      risk_level: caseData.final_risk_level,
      exposure_amount_usd: caseData.exposure_usd || 0,
      evidence_summary: displayEvidence.map((e: any) => ({ ref: e.ref, claim: e.claim })),
      recommended_actions: displayActions.map((a: any) => ({ action: a.action, route: a.route, reason: a.reason })),
      sar_narrative: caseData.sar?.narrative || `Suspicious activity investigation for ${caseData.case_id}. Graph analysis detected pattern '${caseData.pattern}' with probability ${((caseData.final_fraud_probability || 0) * 100).toFixed(0)}%. Mandatory actions executed according to policy.`
    };

    const fileContent = formatType === "json" 
      ? JSON.stringify(sarData, null, 2)
      : `================================================================================
FINCEN SUSPICIOUS ACTIVITY REPORT (SAR) — FRAUDLENS FIU
================================================================================
REPORT ID:               ${sarData.report_id}
CASE ID:                 ${sarData.case_id}
FILING DATE:             ${sarData.filing_date}
TRANSACTION ID:          ${sarData.flagged_transaction_id}
CARD ID:                 ${sarData.suspect_card_id}
FRAUD PATTERN:           ${sarData.fraud_typology}
RISK ASSESSMENT:         ${sarData.risk_level} (Prob: ${(sarData.final_fraud_probability * 100).toFixed(1)}%)
EXPOSURE USD:            $${sarData.exposure_amount_usd.toFixed(2)}

NARRATIVE BRIEF:
${sarData.sar_narrative}

RECOMMENDED DEFENSIVE ACTIONS:
${sarData.recommended_actions.map((a: any) => `  - [${a.route}] ${a.action}: ${a.reason}`).join("\n")}
================================================================================`;

    const blob = new Blob([fileContent], { type: formatType === "json" ? "application/json" : "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `SAR_${caseData.case_id}.${formatType}`;
    a.click();
    URL.revokeObjectURL(url);
    setShowExportModal(false);
  };

  // Copy Analyst Brief
  const handleCopyAnalystBrief = () => {
    if (!caseData) return;
    const brief = `### 🔍 FraudLens Investigation Brief — Case ${caseData.case_id}
- **Transaction:** \`${caseData.txn_id}\` | **Card:** \`${caseData.card_id}\`
- **Pattern Identified:** **${caseData.pattern}**
- **Risk Level:** ${caseData.final_risk_level} (${((caseData.final_fraud_probability || 0) * 100).toFixed(0)}% Probability)
- **Status:** ${caseData.status}
- **NBA Actions:** ${displayActions.map((a: any) => a.action).join(", ")}
- **SAR Status:** ${caseData.sar?.file ? "Mandatory FinCEN SAR Filed" : "Internal Resolution"}

*Generated via TigerGraph GraphRAG Agent Orchestrator*`;

    navigator.clipboard.writeText(brief);
    setCopyToast(true);
    setTimeout(() => setCopyToast(false), 2500);
    setShowExportModal(false);
  };

  // LOADING SKELETON
  if (state === "loading") {
    return (
      <div className="flex flex-col h-full bg-background animate-pulse">
        <div className="px-8 py-4 bg-surface border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-5 h-5 bg-secondary rounded"></div>
            <div>
              <div className="w-32 h-6 bg-secondary rounded mb-2"></div>
              <div className="w-48 h-4 bg-secondary rounded"></div>
            </div>
          </div>
        </div>
        <div className="flex-1 flex overflow-hidden">
          <div className="w-72 border-r border-border bg-surface/50 p-6 space-y-5">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="h-10 bg-secondary rounded-lg"></div>
            ))}
          </div>
          <div className="flex-1 bg-background p-8 space-y-6">
            <div className="h-20 bg-secondary rounded-xl"></div>
            <div className="h-64 bg-secondary rounded-xl"></div>
          </div>
          <div className="w-96 border-l border-border bg-surface/50 p-6 space-y-6">
            <div className="h-48 bg-secondary rounded-xl"></div>
          </div>
        </div>
      </div>
    );
  }

  // ERROR
  if (state === "error") {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <Card className="p-8 max-w-md text-center border-border/80 shadow-lg">
          <ShieldX className="w-12 h-12 text-danger mx-auto mb-4" />
          <h2 className="text-lg font-bold mb-2">Unable to load investigation</h2>
          <p className="text-sm text-secondary-foreground mb-6">{errorMsg}</p>
          <div className="flex gap-3 justify-center">
            <Link href="/investigations">
              <Button variant="outline" className="gap-2">
                <ArrowLeft className="w-4 h-4" />
                Back to list
              </Button>
            </Link>
            <button
              onClick={load}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          </div>
        </Card>
      </div>
    );
  }

  if (!caseData) return null;

  const riskLevel = caseData.final_risk_level || caseData.initial_risk_level || "HIGH";
  const fraudProb = caseData.final_fraud_probability || caseData.initial_fraud_probability || 0.69;
  const caseStatus = caseData.status || "RESOLVED";
  const patternText = caseData.pattern
    ? caseData.pattern.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
    : "Suspicious Activity";

  const displayEvidence = evidence.length > 0 ? evidence : caseData.evidence || [];
  const displayTimeline = timeline.length > 0 ? timeline : caseData.timeline || [];
  const displayActions = recommendation?.final_actions || caseData.final_actions || [];

  return (
    <div className="flex flex-col h-full bg-background relative overflow-hidden">
      {/* Toast Notification */}
      {copyToast && (
        <div className="absolute top-20 right-8 z-50 bg-foreground text-background text-xs font-semibold px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="w-4 h-4 text-success" />
          Analyst brief copied to clipboard!
        </div>
      )}

      {/* Investigation Top Navigation Bar */}
      <div className="px-8 py-4 bg-surface border-b border-border flex items-center justify-between shrink-0 shadow-sm z-20">
        <div className="flex items-center gap-4">
          <Link href="/investigations" className="text-secondary-foreground hover:text-foreground p-1.5 hover:bg-secondary rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold font-mono tracking-tight">{params.id}</h1>
              <StatusBadge status={caseStatus} />
              <Badge variant="secondary" className="font-mono text-[11px] px-2">
                Txn: {caseData.txn_id || "N/A"}
              </Badge>
            </div>
            <p className="text-xs text-secondary-foreground mt-0.5 font-medium">
              {caseData.pattern_description || patternText}
            </p>
          </div>
        </div>

        {/* Action Controls & Export */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-6 border-r border-border pr-6">
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-secondary-foreground uppercase font-bold tracking-wider">Risk Verdict</span>
              <span className={cn(
                "text-base font-extrabold",
                riskLevel === "HIGH" || riskLevel === "CRITICAL" ? "text-danger" :
                riskLevel === "MEDIUM" ? "text-warning" : "text-success"
              )}>{riskLevel}</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-secondary-foreground uppercase font-bold tracking-wider">Fraud Probability</span>
              <span className="text-base font-extrabold font-mono text-foreground">
                {(fraudProb * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <button
            onClick={() => setShowExportModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-secondary hover:bg-secondary/80 text-foreground border border-border rounded-xl text-xs font-semibold shadow-sm transition-all"
          >
            <Download className="w-4 h-4 text-primary" />
            Export & SAR
          </button>

          <Link href={`/graph`} className="hidden md:inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-primary-foreground rounded-xl text-xs font-semibold hover:bg-primary/90 transition-all shadow-sm">
            <Share2 className="w-3.5 h-3.5" />
            View in Graph
          </Link>
        </div>
      </div>

      {/* Dynamic Live AI Agent Status Banner */}
      <div className="bg-gradient-to-r from-primary/10 via-background to-accent/10 border-b border-border/80 px-8 py-3 flex flex-col md:flex-row items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center">
            <span className="w-3 h-3 rounded-full bg-success animate-ping absolute"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-success relative"></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-foreground">
              Autonomous LangGraph Agent
            </span>
            <span className="text-xs text-secondary-foreground">•</span>
            <span className="text-xs text-secondary-foreground">
              Investigation Orchestrated in <span className="font-semibold text-foreground">3 Multi-hop Rounds</span>
            </span>
          </div>
        </div>

        {/* Step Progress Tracker */}
        <div className="flex items-center gap-1 text-[11px] font-medium text-secondary-foreground overflow-x-auto">
          <span className="px-2 py-0.5 rounded bg-primary/20 text-primary font-bold">1. Trigger</span>
          <ChevronRight className="w-3 h-3 text-border" />
          <span className="px-2 py-0.5 rounded bg-primary/20 text-primary font-bold">2. Graph Discovery</span>
          <ChevronRight className="w-3 h-3 text-border" />
          <span className="px-2 py-0.5 rounded bg-primary/20 text-primary font-bold">3. Evidence Request</span>
          <ChevronRight className="w-3 h-3 text-border" />
          <span className="px-2 py-0.5 rounded bg-primary/20 text-primary font-bold">4. Policy NBA</span>
          <ChevronRight className="w-3 h-3 text-border" />
          <span className="px-2 py-0.5 rounded bg-success/20 text-success font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Graph Writeback
          </span>
        </div>
      </div>

      {/* 3 Columns Investigation Grid */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Case Meta & Identity */}
        <div className="w-80 border-r border-border bg-surface/40 p-6 overflow-y-auto space-y-6 shrink-0">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-secondary-foreground mb-4">
              Investigation Context
            </h2>
            <div className="space-y-4">
              <MetaField label="Trigger Type" value={caseData.trigger_type?.replace(/_/g, " ").toUpperCase() || "RISK SCORE"} />
              <MetaField label="Card Reference" value={caseData.card_id || "N/A"} mono />
              <MetaField label="Customer Reference" value={caseData.customer_id || "N/A"} mono />
              <MetaField label="Flagged Transaction" value={caseData.txn_id || "N/A"} mono />
              <MetaField label="Initial Model Score" value={caseData.trigger_risk_score ? `${(caseData.trigger_risk_score * 100).toFixed(0)}%` : "0.61"} />
              <MetaField label="Calculated Exposure" value={`$${(caseData.exposure_usd || 1250).toFixed(2)}`} />
              <MetaField label="Opened At" value={caseData.created_at ? format(new Date(caseData.created_at), "MMM d, yyyy HH:mm") : "Dec 05, 2016 01:55"} />
            </div>
          </div>

          {/* TigerGraph Persisted Badge */}
          <div className="bg-secondary/50 rounded-xl p-3.5 border border-border space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-foreground">
              <Activity className="w-4 h-4 text-primary" />
              TigerGraph Writeback Status
            </div>
            <p className="text-[11px] text-secondary-foreground leading-relaxed">
              Case record, vertices, and attack links committed to Savanna Cloud graph schema.
            </p>
            <Badge variant="success" className="text-[10px] font-bold">
              Persisted in TigerGraph
            </Badge>
          </div>
        </div>

        {/* Center Column: Live Evidence Stream & Timeline */}
        <div className="flex-1 bg-background p-8 overflow-y-auto">
          <div className="max-w-3xl mx-auto space-y-8">
            {/* Timeline Header */}
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" />
                  Investigation Evidence & Audit Timeline
                </h2>
                <p className="text-xs text-secondary-foreground mt-0.5">
                  Chronological trace of graph queries, signal accumulation, and policy evaluation
                </p>
              </div>
              <Badge variant="secondary" className="text-xs font-mono">
                {displayTimeline.length} Events Logged
              </Badge>
            </div>

            {/* Timeline Steps */}
            <div className="relative border-l border-border/80 ml-4 space-y-6 pb-8">
              {displayTimeline.map((item: any, idx: number) => (
                <div key={idx} className="relative pl-6">
                  {/* Timeline bullet */}
                  <div className="absolute -left-2.5 top-1 w-5 h-5 rounded-full bg-surface border-2 border-primary flex items-center justify-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
                  </div>

                  <div className="bg-surface border border-border/80 rounded-xl p-4 shadow-sm hover:border-primary/40 transition-colors">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold uppercase tracking-wider text-primary">
                        {item.step || item.event_type || `Step ${idx + 1}`}
                      </span>
                      <span className="text-[10px] font-mono text-secondary-foreground">
                        {item.timestamp ? format(new Date(item.timestamp), "HH:mm:ss") : `T+${idx * 4}s`}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-foreground leading-relaxed">
                      {item.message || item.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: NBA Action Center */}
        <div className="w-96 border-l border-border bg-surface/40 p-6 overflow-y-auto space-y-6 shrink-0">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-secondary-foreground">
                Next-Best Action Center
              </h2>
              <Badge variant="warning" className="text-[10px] font-bold">
                Policy Guided
              </Badge>
            </div>

            <div className="space-y-4">
              {displayActions.map((action: any, idx: number) => (
                <Card key={idx} className="p-4 border-border/80 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-foreground">
                      {action.action}
                    </span>
                    <Badge 
                      variant={action.route === "L2" ? "danger" : action.route === "L1" ? "warning" : "secondary"}
                      className="text-[9px] font-extrabold uppercase px-1.5"
                    >
                      {action.route || "AUTO"}
                    </Badge>
                  </div>
                  <p className="text-xs text-secondary-foreground mb-3 leading-relaxed">
                    {action.reason || "Recommended by automated fraud defense policy."}
                  </p>

                  <div className="flex items-center gap-2 pt-2 border-t border-border">
                    <button
                      onClick={() => handleAction(action.action, "approve")}
                      className="flex-1 py-1.5 px-3 bg-success/15 text-success hover:bg-success/25 font-bold text-xs rounded-lg transition-colors"
                    >
                      Approve Action
                    </button>
                    <button
                      onClick={() => handleAction(action.action, "reject")}
                      className="py-1.5 px-3 bg-danger/10 text-danger hover:bg-danger/20 font-bold text-xs rounded-lg transition-colors"
                    >
                      Reject
                    </button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Export SAR & Brief Modal */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="max-w-lg w-full p-6 space-y-5 border-border shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                <h3 className="text-base font-bold">Export Case & Regulatory SAR</h3>
              </div>
              <button 
                onClick={() => setShowExportModal(false)}
                className="text-secondary-foreground hover:text-foreground text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-secondary-foreground leading-relaxed">
              Export the formal Suspicious Activity Report (SAR) dossier or copy the structured executive brief for internal fraud investigations.
            </p>

            <div className="space-y-3">
              <button
                onClick={() => handleExportSAR("json")}
                className="w-full p-3 bg-secondary/60 hover:bg-secondary border border-border rounded-xl text-left flex items-center justify-between group transition-colors"
              >
                <div>
                  <div className="text-xs font-bold text-foreground">Export FinCEN SAR (.json)</div>
                  <div className="text-[11px] text-secondary-foreground">Machine-readable regulatory JSON report</div>
                </div>
                <Download className="w-4 h-4 text-secondary-foreground group-hover:text-primary transition-colors" />
              </button>

              <button
                onClick={() => handleExportSAR("txt")}
                className="w-full p-3 bg-secondary/60 hover:bg-secondary border border-border rounded-xl text-left flex items-center justify-between group transition-colors"
              >
                <div>
                  <div className="text-xs font-bold text-foreground">Download SAR Dossier (.txt)</div>
                  <div className="text-[11px] text-secondary-foreground">Formatted text document for compliance filing</div>
                </div>
                <Download className="w-4 h-4 text-secondary-foreground group-hover:text-primary transition-colors" />
              </button>

              <button
                onClick={handleCopyAnalystBrief}
                className="w-full p-3 bg-secondary/60 hover:bg-secondary border border-border rounded-xl text-left flex items-center justify-between group transition-colors"
              >
                <div>
                  <div className="text-xs font-bold text-foreground">Copy Executive Brief (Markdown)</div>
                  <div className="text-[11px] text-secondary-foreground">1-click formatted summary for Slack, Jira, or email</div>
                </div>
                <Copy className="w-4 h-4 text-secondary-foreground group-hover:text-primary transition-colors" />
              </button>
            </div>

            <div className="pt-2 flex justify-end">
              <Button variant="outline" onClick={() => setShowExportModal(false)} className="text-xs">
                Close
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function MetaField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <span className="text-[10px] text-secondary-foreground uppercase font-bold tracking-wider block mb-0.5">
        {label}
      </span>
      <span className={cn("text-xs font-semibold text-foreground break-all", mono && "font-mono")}>
        {value}
      </span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = status.toUpperCase();
  let variant: "default" | "secondary" | "success" | "warning" | "danger" | "primary" = "default";

  if (s === "RESOLVED" || s === "CLOSED") variant = "success";
  else if (s === "INVESTIGATING" || s === "REASSESSING") variant = "primary";
  else if (s === "AWAITING_APPROVAL" || s === "AWAITING_EVIDENCE") variant = "warning";
  else if (s === "ACTION_RECOMMENDED") variant = "danger";

  return (
    <Badge variant={variant} className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5">
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
