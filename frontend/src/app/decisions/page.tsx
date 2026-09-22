/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useState } from "react";
import { getCases, getTimeline, getRecommendation, CaseSummary } from "@/lib/api";
import { Card, Badge, cn } from "@/components/ui";
import { Search, BrainCircuit, Cpu, ArrowRight, ShieldCheck, AlertTriangle } from "lucide-react";
import { format } from "date-fns";

export default function DecisionsPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [recommendation, setRecommendation] = useState<any>(null);
  
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingDecisions, setLoadingDecisions] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    getCases()
      .then(res => setCases(res.cases || []))
      .catch(err => console.error(err))
      .finally(() => setLoadingCases(false));
  }, []);

  useEffect(() => {
    if (!selectedCase) {
      setTimeline([]);
      setRecommendation(null);
      return;
    }
    
    setLoadingDecisions(true);
    Promise.all([
      getTimeline(selectedCase).catch(() => ({ timeline: [] })),
      getRecommendation(selectedCase).catch(() => null)
    ])
      .then(([timeRes, recRes]) => {
        setTimeline(timeRes.timeline || []);
        setRecommendation(recRes);
      })
      .finally(() => setLoadingDecisions(false));
  }, [selectedCase]);

  const filteredCases = cases.filter(c => 
    !search || c.case_id?.toLowerCase().includes(search.toLowerCase())
  );

  const safeTime = (dateStr: string) => {
    try { return format(new Date(dateStr), "MMM d, HH:mm:ss"); } 
    catch { return dateStr || ""; }
  };

  const getEventIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('approved') || t.includes('cleared')) return <ShieldCheck className="w-4 h-4 text-success" />;
    if (t.includes('rejected') || t.includes('fraud')) return <AlertTriangle className="w-4 h-4 text-danger" />;
    return <Cpu className="w-4 h-4 text-primary" />;
  };

  return (
    <div className="flex h-full max-w-[1600px] mx-auto">
      {/* Sidebar: Case Selector */}
      <div className="w-80 border-r border-border bg-surface/50 flex flex-col shrink-0">
        <div className="p-4 border-b border-border">
          <h2 className="text-xs font-semibold text-secondary-foreground uppercase tracking-wider mb-4">Select Investigation</h2>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-foreground" />
            <input
              type="text"
              placeholder="Search Case ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingCases ? (
            <div className="p-4 text-center text-sm text-secondary-foreground animate-pulse">Loading cases...</div>
          ) : filteredCases.length > 0 ? (
            filteredCases.map(c => (
              <button
                key={c.case_id}
                onClick={() => setSelectedCase(c.case_id)}
                className={cn(
                  "w-full text-left p-3 rounded-md transition-colors flex items-center justify-between group",
                  selectedCase === c.case_id 
                    ? "bg-primary text-primary-foreground" 
                    : "hover:bg-secondary text-foreground"
                )}
              >
                <span className="font-mono text-sm font-medium">{c.case_id}</span>
                <span className={cn(
                  "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded",
                  selectedCase === c.case_id ? "bg-primary-foreground/20 text-primary-foreground" : 
                  c.final_risk_level === "HIGH" || c.final_risk_level === "CRITICAL" ? "bg-danger/10 text-danger" : 
                  "bg-surface text-secondary-foreground"
                )}>
                  {c.final_risk_level || "UNKNOWN"}
                </span>
              </button>
            ))
          ) : (
            <div className="p-4 text-center text-sm text-secondary-foreground">No cases found.</div>
          )}
        </div>
      </div>

      {/* Main: Audit Trail Display */}
      <div className="flex-1 bg-background flex flex-col overflow-hidden">
        <div className="px-8 py-6 border-b border-border bg-surface/30 shrink-0">
          <h1 className="text-2xl font-semibold tracking-tight">AI Decisions Audit Trail</h1>
          <p className="text-sm text-secondary-foreground mt-1">
            {selectedCase 
              ? `Agent reasoning and decisions for ${selectedCase}` 
              : "Select an investigation to view its decision history"}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-8">
          {!selectedCase ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
              <BrainCircuit className="w-12 h-12 text-secondary-foreground mb-4" />
              <h2 className="text-lg font-medium mb-2">No Investigation Selected</h2>
              <p className="text-sm text-secondary-foreground">Choose a case from the sidebar to trace the agent's analytical steps, evidence evaluation, and final recommended actions.</p>
            </div>
          ) : loadingDecisions ? (
            <div className="animate-pulse space-y-8 max-w-3xl mx-auto">
              <div className="w-48 h-6 bg-secondary rounded mb-8"></div>
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="flex gap-4">
                  <div className="w-4 h-4 rounded-full bg-secondary shrink-0 mt-1"></div>
                  <div className="w-full h-24 bg-secondary rounded"></div>
                </div>
              ))}
            </div>
          ) : (
            <div className="max-w-4xl mx-auto pb-12 flex gap-8">
              
              {/* Timeline (Left) */}
              <div className="flex-1">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-secondary-foreground mb-6">Analytical Steps</h3>
                {timeline.length > 0 ? (
                  <div className="space-y-6 relative">
                    <div className="absolute left-6 top-2 bottom-0 w-0.5 bg-border"></div>
                    {timeline.map((evt: any, idx: number) => (
                      <div key={idx} className="relative flex gap-6 pl-14">
                        <div className="absolute left-3 top-0 w-6 h-6 rounded-full border-2 border-background bg-surface shadow-sm z-10 flex items-center justify-center">
                           {getEventIcon(evt.event_type || "")}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-bold uppercase tracking-wider text-primary">
                              {(evt.event_type || "processing").replace(/_/g, " ")}
                            </span>
                            <time className="text-[11px] text-secondary-foreground font-mono">
                              {safeTime(evt.timestamp)}
                            </time>
                          </div>
                          <Card className="p-4 shadow-sm border border-border">
                            <p className="text-sm leading-relaxed text-foreground">{evt.description}</p>
                          </Card>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-secondary-foreground border border-dashed rounded-lg">
                    No timeline events recorded.
                  </div>
                )}
              </div>

              {/* Final Decision / NBA (Right) */}
              <div className="w-96 shrink-0 flex flex-col gap-6">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-secondary-foreground mb-0">Final Recommendation</h3>
                
                {recommendation ? (
                  <>
                    <Card className="p-5 border-l-4 border-l-primary shadow-sm">
                      <div className="text-xs text-secondary-foreground uppercase tracking-wide mb-1">Verdict</div>
                      <div className={cn(
                        "text-xl font-bold uppercase mb-4",
                        recommendation.final_verdict === "fraud" ? "text-danger" :
                        recommendation.final_verdict === "cleared" ? "text-success" : "text-warning"
                      )}>
                        {recommendation.final_verdict || "Unknown"}
                      </div>
                      
                      {recommendation.fraud_probability != null && (
                        <div className="mb-4">
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="text-secondary-foreground">Fraud Probability</span>
                            <span className="font-semibold">{(recommendation.fraud_probability * 100).toFixed(1)}%</span>
                          </div>
                          <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                            <div 
                              className={cn(
                                "h-full rounded-full",
                                recommendation.fraud_probability > 0.7 ? "bg-danger" : 
                                recommendation.fraud_probability > 0.4 ? "bg-warning" : "bg-success"
                              )}
                              style={{ width: `${recommendation.fraud_probability * 100}%` }}
                            />
                          </div>
                        </div>
                      )}
                      
                      {recommendation.what_changed && (
                        <div className="mt-4 pt-4 border-t border-border">
                          <div className="text-xs text-secondary-foreground uppercase tracking-wide mb-1">Reasoning</div>
                          <p className="text-sm text-foreground">{recommendation.what_changed}</p>
                        </div>
                      )}
                    </Card>

                    {recommendation.final_actions && recommendation.final_actions.length > 0 && (
                      <div className="space-y-3">
                        <div className="text-xs text-secondary-foreground uppercase tracking-wider">Next Best Actions</div>
                        {recommendation.final_actions.map((act: any, i: number) => (
                          <Card key={i} className="p-4 border-l-4 border-l-accent shadow-sm">
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <h4 className="font-semibold text-sm">{(act.action || "").replace(/_/g, " ")}</h4>
                              <Badge variant={act.status === "approved" ? "success" : "primary"}>
                                {act.status || "Pending"}
                              </Badge>
                            </div>
                            {act.policy_rationale && (
                              <p className="text-xs text-secondary-foreground mb-2">{act.policy_rationale}</p>
                            )}
                            <div className="flex items-center justify-between text-[10px] text-secondary-foreground font-mono">
                              <span>Rule: {act.policy_rule || "Auto"}</span>
                              <span>Route: {act.approval_route || "L1"}</span>
                            </div>
                          </Card>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <Card className="p-6 text-center text-sm text-secondary-foreground border-dashed">
                    Decision pending or unavailable.
                  </Card>
                )}
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
