/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useState } from "react";
import { getCases, getEvidence, CaseSummary } from "@/lib/api";
import { Card, Badge, cn } from "@/components/ui";
import { Search, Files, Activity, FileText, Smartphone, ShieldAlert } from "lucide-react";

export default function EvidencePage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    getCases()
      .then(res => setCases(res.cases || []))
      .catch(err => console.error(err))
      .finally(() => setLoadingCases(false));
  }, []);

  useEffect(() => {
    if (!selectedCase) {
      setEvidence([]);
      return;
    }
    setLoadingEvidence(true);
    getEvidence(selectedCase)
      .then(res => setEvidence(res.evidence || []))
      .catch(err => console.error(err))
      .finally(() => setLoadingEvidence(false));
  }, [selectedCase]);

  const filteredCases = cases.filter(c => 
    !search || c.case_id?.toLowerCase().includes(search.toLowerCase())
  );

  const getSourceIcon = (source: string, ref: string) => {
    const s = source?.toLowerCase() || "";
    const r = ref?.toLowerCase() || "";
    if (s === "graph" && r.includes("device")) return <Smartphone className="w-4 h-4" />;
    if (s === "graph" && r.includes("card")) return <Activity className="w-4 h-4" />;
    if (s === "graph") return <Activity className="w-4 h-4" />;
    if (s === "document" || r.includes("case")) return <FileText className="w-4 h-4" />;
    return <ShieldAlert className="w-4 h-4" />;
  };

  const getCategory = (source: string, ref: string) => {
    const r = ref?.toLowerCase() || "";
    if (r.includes("transaction") || r.includes("velocity")) return "Transaction History";
    if (r.includes("card")) return "Account Behavior";
    if (r.includes("device")) return "Device & Environment";
    if (r.includes("similar_cases") || r.includes("case")) return "Prior Cases";
    if (source === "graph") return "Graph Relationships";
    return "External Signals";
  };

  const groupedEvidence = evidence.reduce((acc, ev) => {
    const cat = getCategory(ev.source, ev.ref);
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(ev);
    return acc;
  }, {} as Record<string, any[]>);

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

      {/* Main: Evidence Display */}
      <div className="flex-1 bg-background flex flex-col overflow-hidden">
        <div className="px-8 py-6 border-b border-border bg-surface/30 shrink-0">
          <h1 className="text-2xl font-semibold tracking-tight">Evidence Explorer</h1>
          <p className="text-sm text-secondary-foreground mt-1">
            {selectedCase 
              ? `Viewing collected evidence for case ${selectedCase}` 
              : "Select an investigation from the sidebar to explore its evidence"}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-8">
          {!selectedCase ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
              <Files className="w-12 h-12 text-secondary-foreground mb-4" />
              <h2 className="text-lg font-medium mb-2">No Investigation Selected</h2>
              <p className="text-sm text-secondary-foreground">Choose a case from the sidebar to view its detailed evidence breakdown, sources, and confidence scoring.</p>
            </div>
          ) : loadingEvidence ? (
            <div className="animate-pulse space-y-8 max-w-4xl mx-auto">
              {[1, 2].map(i => (
                <div key={i}>
                  <div className="w-48 h-6 bg-secondary rounded mb-4"></div>
                  <div className="space-y-3">
                    <div className="w-full h-24 bg-secondary rounded"></div>
                    <div className="w-full h-24 bg-secondary rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : evidence.length === 0 ? (
            <div className="p-8 text-center text-secondary-foreground border border-dashed rounded-lg max-w-4xl mx-auto">
              No evidence collected for {selectedCase}.
            </div>
          ) : (
            <div className="space-y-8 max-w-4xl mx-auto pb-12">
              {Object.entries(groupedEvidence).map(([category, itemsArray]) => {
                const items = itemsArray as any[];
                return (
                <div key={category}>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-secondary-foreground mb-4 flex items-center gap-2">
                    <div className="p-1.5 bg-secondary rounded-md text-foreground">
                      {getSourceIcon(items[0]?.source, items[0]?.ref)}
                    </div>
                    {category}
                    <span className="text-secondary-foreground/60 font-normal ml-1">({items.length})</span>
                  </h3>
                  
                  <div className="space-y-3">
                    {items.map((ev, idx) => (
                      <Card key={idx} className={cn(
                        "p-5 border-l-4 transition-all hover:shadow-sm",
                        ev.supports_fraud === true ? "border-l-danger" :
                        ev.supports_fraud === false ? "border-l-success" :
                        "border-l-secondary-foreground"
                      )}>
                        <div className="flex items-start gap-4">
                          <div className="flex-1">
                            <div className="flex items-center flex-wrap gap-2 mb-2">
                              <span className="text-xs font-mono font-medium">{ev.evidence_id}</span>
                              <span className="text-xs text-secondary-foreground">·</span>
                              <span className="text-xs text-secondary-foreground uppercase tracking-wide">{ev.source}</span>
                              {ev.supports_fraud === true && <Badge variant="danger" className="py-0 h-5">Supports Fraud</Badge>}
                              {ev.supports_fraud === false && <Badge variant="success" className="py-0 h-5">Against Fraud</Badge>}
                            </div>
                            <p className="text-sm leading-relaxed text-foreground">{ev.claim}</p>
                            
                            {ev.entity_ids && ev.entity_ids.length > 0 && ev.entity_ids.some((id: string) => id) && (
                              <div className="mt-4 pt-3 border-t border-border flex items-center gap-2">
                                <span className="text-xs text-secondary-foreground">Related Entities:</span>
                                {ev.entity_ids.filter((id: string) => id).map((id: string, i: number) => (
                                  <span key={i} className="text-[11px] font-mono bg-secondary/50 px-1.5 py-0.5 rounded text-secondary-foreground">{id}</span>
                                ))}
                              </div>
                            )}
                          </div>
                          
                          <div className="text-right shrink-0 bg-surface rounded-lg p-3 border border-border min-w-[100px]">
                            <div className="text-[10px] text-secondary-foreground uppercase tracking-widest mb-1">Confidence</div>
                            <div className={cn(
                              "text-lg font-semibold",
                              ev.confidence > 0.8 ? "text-success" :
                              ev.confidence > 0.5 ? "text-warning" : "text-secondary-foreground"
                            )}>
                              {ev.confidence != null ? `${(ev.confidence * 100).toFixed(0)}%` : "—"}
                            </div>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              );
            })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
