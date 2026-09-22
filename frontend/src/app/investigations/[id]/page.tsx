/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useEffect, useState } from "react";
import { getCase, getEvidence, getTimeline, getRecommendation, approveAction, rejectAction } from "@/lib/api";
import { Card, Badge, Button, cn } from "@/components/ui";
import { CheckCircle2, AlertCircle, Activity, Cpu, RefreshCw, ShieldX, ArrowLeft } from "lucide-react";
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

  const load = () => {
    setState("loading");
    setErrorMsg("");

    // Fetch case from /api/cases/:id first (disk data).
    // If 404, try /api/investigations/:id (live in-memory data).
    getCase(params.id)
      .catch(() => {
        // Fallback: try investigation endpoint
        return fetch(`http://localhost:8000/api/investigations/${params.id}`).then((r) => {
          if (!r.ok) throw new Error(`Case ${params.id} not found`);
          return r.json();
        });
      })
      .then((data) => {
        setCaseData(data);
        setState("success");

        // Load sub-resources in parallel (these use /api/investigations/ endpoints)
        getEvidence(params.id)
          .then((res) => setEvidence(res.evidence || []))
          .catch(() => {
            // Use evidence from case data itself
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
            // Build recommendation from case data
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
      load(); // Refresh
    } catch (err) {
      console.error(err);
      alert("Failed to perform action");
    }
  };

  // LOADING
  if (state === "loading") {
    return (
      <div className="flex flex-col h-full bg-background animate-pulse">
        {/* Header Skeleton */}
        <div className="px-8 py-4 bg-surface border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-5 h-5 bg-secondary rounded"></div>
            <div>
              <div className="w-32 h-6 bg-secondary rounded mb-2"></div>
              <div className="w-48 h-4 bg-secondary rounded"></div>
            </div>
          </div>
          <div className="flex gap-6">
            <div className="w-16 h-10 bg-secondary rounded"></div>
            <div className="w-16 h-10 bg-secondary rounded"></div>
          </div>
        </div>
        {/* 3 Columns Skeleton */}
        <div className="flex-1 flex overflow-hidden">
          <div className="w-72 border-r border-border bg-surface/50 p-6 space-y-5">
            <div className="w-24 h-4 bg-secondary rounded mb-4"></div>
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i}>
                <div className="w-16 h-3 bg-secondary rounded mb-1"></div>
                <div className="w-full h-4 bg-secondary rounded"></div>
              </div>
            ))}
          </div>
          <div className="flex-1 bg-background p-8">
            <div className="max-w-2xl mx-auto space-y-8">
              <div className="w-32 h-6 bg-secondary rounded mb-6"></div>
              {[1, 2, 3].map(i => (
                <div key={i} className="w-full h-24 bg-secondary rounded"></div>
              ))}
            </div>
          </div>
          <div className="w-96 border-l border-border bg-surface/50 p-6 space-y-6">
            <div className="w-24 h-4 bg-secondary rounded"></div>
            <div className="w-full h-32 bg-secondary rounded"></div>
            <div className="w-24 h-4 bg-secondary rounded"></div>
            <div className="w-full h-48 bg-secondary rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  // ERROR
  if (state === "error") {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <Card className="p-8 max-w-md text-center">
          <ShieldX className="w-12 h-12 text-danger mx-auto mb-4" />
          <h2 className="text-lg font-semibold mb-2">Unable to load investigation</h2>
          <p className="text-sm text-secondary-foreground mb-4">{errorMsg}</p>
          <div className="flex gap-3 justify-center">
            <Link href="/investigations">
              <Button variant="outline" className="gap-2">
                <ArrowLeft className="w-4 h-4" />
                Back to list
              </Button>
            </Link>
            <button
              onClick={load}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
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

  const riskLevel = caseData.final_risk_level || caseData.initial_risk_level || "N/A";
  const fraudProb = caseData.final_fraud_probability || caseData.initial_fraud_probability || 0;
  const caseStatus = caseData.status || "UNKNOWN";
  const verdictText = caseData.final_verdict || "pending";
  const patternText = caseData.pattern
    ? caseData.pattern.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
    : "Suspicious Activity";

  // Use evidence and timeline from loaded data, or from caseData directly
  const displayEvidence = evidence.length > 0 ? evidence : caseData.evidence || [];
  const displayTimeline = timeline.length > 0 ? timeline : caseData.timeline || [];
  const displayActions = recommendation?.final_actions || caseData.final_actions || [];

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Investigation Header */}
      <div className="px-8 py-4 bg-surface border-b border-border flex items-center justify-between shrink-0 shadow-sm z-10">
        <div className="flex items-center gap-4">
          <Link href="/investigations" className="text-secondary-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold font-mono tracking-tight">{params.id}</h1>
              <StatusBadge status={caseStatus} />
            </div>
            <p className="text-sm text-secondary-foreground mt-1">
              {caseData.pattern_description || patternText}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end">
            <span className="text-xs text-secondary-foreground uppercase tracking-wide">Risk</span>
            <span className={cn(
              "text-lg font-semibold",
              riskLevel === "HIGH" || riskLevel === "CRITICAL" ? "text-danger" :
              riskLevel === "MEDIUM" ? "text-warning" : "text-success"
            )}>{riskLevel}</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-xs text-secondary-foreground uppercase tracking-wide">Fraud Prob</span>
            <span className="text-lg font-semibold text-foreground">
              {fraudProb > 0 ? `${(fraudProb * 100).toFixed(0)}%` : "N/A"}
            </span>
          </div>
          <button
            onClick={load}
            className="p-2 text-secondary-foreground hover:bg-secondary rounded-md transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 3-Column Workspace */}
      <div className="flex-1 flex overflow-hidden">

        {/* LEFT: Case Context */}
        <div className="w-72 border-r border-border bg-surface/50 overflow-y-auto shrink-0 p-6 space-y-5">
          <h2 className="text-xs font-semibold text-secondary-foreground uppercase tracking-wider mb-4">Case Context</h2>

          <ContextBlock label="Case ID" value={caseData.case_id} mono />
          <ContextBlock label="Transaction" value={caseData.txn_id || "N/A"} mono />
          <ContextBlock label="Card" value={caseData.card_id} mono />
          <ContextBlock label="Customer" value={caseData.customer_id} mono />
          <ContextBlock label="Trigger" value={caseData.trigger_type?.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())} />
          <ContextBlock label="Trigger Risk Score" value={caseData.trigger_risk_score != null ? `${(caseData.trigger_risk_score * 100).toFixed(0)}%` : undefined} />
          <ContextBlock label="Pattern" value={patternText} />
          <ContextBlock label="Created" value={safeDate(caseData.created_at)} />
          <ContextBlock label="Updated" value={safeDate(caseData.updated_at)} />

          <div className="pt-4 border-t border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary-foreground">Evidence Items</span>
              <span className="text-sm font-medium">{displayEvidence.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary-foreground">Timeline Events</span>
              <span className="text-sm font-medium">{displayTimeline.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary-foreground">Confidence</span>
              <span className="text-sm font-medium">
                {caseData.final_confidence ? `${(caseData.final_confidence * 100).toFixed(0)}%` : "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* CENTER: Evidence & Timeline */}
        <div className="flex-1 overflow-y-auto bg-background p-8">
          <div className="max-w-2xl mx-auto space-y-8">

            {/* Evidence Section */}
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Activity className="w-5 h-5 text-primary" />
                </div>
                <h2 className="text-lg font-medium">Evidence ({displayEvidence.length} items)</h2>
              </div>

              {displayEvidence.length > 0 ? (
                <div className="space-y-3">
                  {displayEvidence.map((ev: any, idx: number) => (
                    <Card key={ev.evidence_id || idx} className={cn(
                      "p-4 border-l-4",
                      ev.supports_fraud === true ? "border-l-danger" :
                      ev.supports_fraud === false ? "border-l-success" :
                      "border-l-secondary-foreground"
                    )}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono text-secondary-foreground">{ev.evidence_id}</span>
                            <span className="text-xs text-secondary-foreground">·</span>
                            <span className="text-xs text-secondary-foreground">{ev.source}</span>
                            {ev.supports_fraud === true && <Badge variant="danger">Supports Fraud</Badge>}
                            {ev.supports_fraud === false && <Badge variant="success">Against Fraud</Badge>}
                          </div>
                          <p className="text-sm text-foreground leading-relaxed">{ev.claim}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-xs text-secondary-foreground">Confidence</div>
                          <div className="text-sm font-medium">
                            {ev.confidence != null ? `${(ev.confidence * 100).toFixed(0)}%` : "—"}
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <Card className="p-8 text-center text-secondary-foreground text-sm border-dashed">
                  No evidence collected yet.
                </Card>
              )}
            </div>

            {/* Timeline Section */}
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-accent/10 rounded-lg">
                  <Cpu className="w-5 h-5 text-accent" />
                </div>
                <h2 className="text-lg font-medium">Investigation Timeline ({displayTimeline.length} events)</h2>
              </div>

              {displayTimeline.length > 0 ? (
                <div className="space-y-4 relative">
                  <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-border"></div>
                  {displayTimeline.map((evt: any, idx: number) => (
                    <div key={idx} className="relative flex gap-4 pl-12">
                      <div className="absolute left-3 top-1 w-4 h-4 rounded-full border-2 border-background bg-surface shadow z-10 flex items-center justify-center">
                        {evt.event_type === "action_approved" ? (
                          <div className="w-2 h-2 rounded-full bg-success"></div>
                        ) : evt.event_type === "action_rejected" ? (
                          <div className="w-2 h-2 rounded-full bg-danger"></div>
                        ) : (
                          <div className="w-2 h-2 rounded-full bg-primary"></div>
                        )}
                      </div>
                      <Card className="flex-1 p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                            {(evt.event_type || "event").replace(/_/g, " ")}
                          </span>
                          <time className="text-xs text-secondary-foreground">
                            {safeTime(evt.timestamp)}
                          </time>
                        </div>
                        <p className="text-sm text-foreground leading-relaxed">{evt.description}</p>
                      </Card>
                    </div>
                  ))}
                </div>
              ) : (
                <Card className="p-8 text-center text-secondary-foreground text-sm border-dashed">
                  No timeline events recorded.
                </Card>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT: Assessment & Next Best Action */}
        <div className="w-96 border-l border-border bg-surface/50 overflow-y-auto shrink-0 p-6 flex flex-col gap-6">

          {/* Verdict Panel */}
          <div>
            <h2 className="text-xs font-semibold text-secondary-foreground uppercase tracking-wider mb-4">Assessment</h2>
            <Card className="p-4">
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-secondary-foreground mb-1">Verdict</p>
                  <p className={cn(
                    "text-lg font-semibold uppercase",
                    verdictText === "fraud" ? "text-danger" :
                    verdictText === "cleared" ? "text-success" : "text-warning"
                  )}>
                    {verdictText}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-secondary-foreground mb-1">Fraud Probability</p>
                  <p className="text-lg font-semibold">{fraudProb > 0 ? `${(fraudProb * 100).toFixed(1)}%` : "N/A"}</p>
                </div>
                {caseData.what_changed && (
                  <div>
                    <p className="text-sm text-secondary-foreground mb-1">What Changed</p>
                    <p className="text-sm">{caseData.what_changed}</p>
                  </div>
                )}
              </div>
            </Card>
          </div>

          {/* Key Evidence Summary */}
          <div>
            <h2 className="text-xs font-semibold text-secondary-foreground uppercase tracking-wider mb-4">Key Findings</h2>
            {displayEvidence.filter((e: any) => e.supports_fraud === true).length > 0 ? (
              <ul className="text-sm text-secondary-foreground space-y-2 pl-4 list-disc marker:text-danger">
                {displayEvidence.filter((e: any) => e.supports_fraud === true).map((e: any, i: number) => (
                  <li key={i}>{e.claim}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-secondary-foreground">No fraud-supporting evidence found.</p>
            )}
          </div>

          {/* Next Best Action */}
          <div className="flex-1 flex flex-col">
            <h2 className="text-xs font-semibold text-secondary-foreground uppercase tracking-wider mb-4">Next Best Action</h2>

            {displayActions.length > 0 ? (
              <div className="space-y-4">
                {displayActions.map((action: any, i: number) => (
                  <Card key={i} className={cn(
                    "p-5 flex flex-col gap-3 border-2 transition-colors",
                    action.status === "approved" ? "border-success bg-success/5" :
                    action.status === "rejected" ? "border-danger bg-danger/5" :
                    "border-primary shadow-sm"
                  )}>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant={
                          action.status === "approved" ? "success" :
                          action.status === "rejected" ? "danger" : "primary"
                        }>
                          {action.status === "approved" ? "Executed" :
                           action.status === "rejected" ? "Rejected" : "Recommended"}
                        </Badge>
                        {action.approval_route && (
                          <span className="text-xs text-secondary-foreground">{action.approval_route} approval</span>
                        )}
                      </div>
                      <h3 className="text-base font-semibold">
                        {(action.action || "").replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}
                      </h3>
                      {action.policy_rationale && (
                        <p className="text-sm text-secondary-foreground mt-2 line-clamp-3">{action.policy_rationale}</p>
                      )}
                      {action.policy_rule && (
                        <p className="text-xs text-secondary-foreground mt-1">Policy: {action.policy_rule}</p>
                      )}
                    </div>

                    {!action.status || action.status === "pending" ? (
                      <div className="flex gap-2">
                        <Button variant="primary" className="flex-1" onClick={() => handleAction(action.action, "approve")}>
                          Approve
                        </Button>
                        <Button
                          variant="outline"
                          className="flex-1 text-danger hover:text-danger hover:bg-danger/10 border-danger/20"
                          onClick={() => handleAction(action.action, "reject")}
                        >
                          Reject
                        </Button>
                      </div>
                    ) : (
                      <div className="text-sm text-secondary-foreground flex items-center gap-2">
                        {action.status === "approved" ? (
                          <CheckCircle2 className="w-4 h-4 text-success" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-danger" />
                        )}
                        By {action.approved_by || action.rejected_by || "Analyst"}
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="flex-1 flex items-center justify-center border-dashed text-secondary-foreground text-sm p-6 text-center">
                No actions recommended for this case.
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ContextBlock({ label, value, mono }: { label: string; value: string | undefined | null; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs text-secondary-foreground uppercase tracking-wide mb-1">{label}</p>
      <p className={cn("text-sm font-medium", mono && "font-mono text-primary")}>
        {value || <span className="text-secondary-foreground">N/A</span>}
      </p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = status.toUpperCase();
  if (s.includes("RUNNING") || s === "CREATED") return <Badge variant="primary">Investigating</Badge>;
  if (s.includes("ACTION_RECOMMENDED") || s.includes("AWAITING")) return <Badge variant="warning">Action Required</Badge>;
  if (s === "ACTION_TAKEN" || s === "RESOLVED") return <Badge variant="success">Resolved</Badge>;
  if (s === "ERROR") return <Badge variant="danger">Error</Badge>;
  return <Badge>{status}</Badge>;
}

function safeDate(dateStr: string | null | undefined): string | undefined {
  if (!dateStr) return undefined;
  try {
    return format(new Date(dateStr), "PPP p");
  } catch {
    return dateStr;
  }
}

function safeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  try {
    return format(new Date(dateStr), "HH:mm:ss");
  } catch {
    return "";
  }
}
