/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useEffect, useState } from "react";
import { getCases, getInvestigations, CaseSummary, InvestigationSummary } from "@/lib/api";
import { Card, Badge, Button, cn } from "@/components/ui";
import { Search, RefreshCw, ShieldX } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";

type LoadState = "loading" | "success" | "error";

export default function InvestigationsPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [liveInvestigations, setLiveInvestigations] = useState<InvestigationSummary[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [search, setSearch] = useState("");

  const load = () => {
    setState("loading");
    setErrorMsg("");
    Promise.all([getCases(), getInvestigations()])
      .then(([casesRes, invRes]) => {
        setCases(casesRes.cases || []);
        setLiveInvestigations(invRes.investigations || []);
        setState("success");
      })
      .catch((err) => {
        console.error("Investigations load failed:", err);
        setErrorMsg(err.message || "Failed to load investigations.");
        setState("error");
      });
  };

  useEffect(() => { load(); }, []);

  // Filter by search term
  const filteredCases = cases.filter((c) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      c.case_id?.toLowerCase().includes(s) ||
      c.pattern?.toLowerCase().includes(s) ||
      c.final_verdict?.toLowerCase().includes(s) ||
      c.status?.toLowerCase().includes(s)
    );
  });

  // ERROR
  if (state === "error") {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <Card className="p-8 max-w-md text-center">
          <ShieldX className="w-12 h-12 text-danger mx-auto mb-4" />
          <h2 className="text-lg font-semibold mb-2">Unable to load investigations</h2>
          <p className="text-sm text-secondary-foreground mb-6">{errorMsg}</p>
          <button
            onClick={load}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 h-full flex flex-col max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Investigations</h1>
          <p className="text-sm text-secondary-foreground mt-1">
            {state === "loading"
              ? "Loading..."
              : `${cases.length} cases on file, ${liveInvestigations.length} active investigations`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={load}
            className="p-2 text-secondary-foreground hover:bg-secondary rounded-md transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-3 mb-6 bg-surface p-1.5 rounded-lg border border-border shadow-sm">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-foreground" />
          <input
            type="text"
            placeholder="Search cases, patterns, verdicts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-transparent border-none text-sm focus:outline-none focus:ring-0"
          />
        </div>
      </div>

      {/* LOADING */}
      {state === "loading" ? (
        <Card className="flex-1 overflow-hidden flex flex-col">
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Case</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Pattern / Trigger</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Risk / Prob</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Verdict</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Age</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-secondary rounded w-20"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-secondary rounded w-32"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-secondary rounded w-16"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-secondary rounded w-24"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-secondary rounded w-24"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-secondary rounded w-16"></div></td>
                    <td className="px-6 py-4 text-right"><div className="h-8 bg-secondary rounded w-16 ml-auto"></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        /* Table */
        <Card className="flex-1 overflow-hidden flex flex-col">
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Case</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Pattern / Trigger</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Risk / Prob</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Verdict</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider">Age</th>
                  <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase tracking-wider text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {/* Live investigations first */}
                {liveInvestigations.map((inv) => (
                  <tr key={`inv-${inv.case_id}`} className="hover:bg-secondary/50 transition-colors group">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link href={`/investigations/${inv.case_id}`} className="font-mono text-sm font-medium text-primary hover:underline">
                        {inv.case_id}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-foreground">AI Agent</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant="primary">Calculating</Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-foreground">—</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-foreground">
                      {safeAge(inv.started_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <Link href={`/investigations/${inv.case_id}`}>
                        <Button variant="outline" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                          View
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}

                {/* Completed cases from disk */}
                {filteredCases.map((c) => (
                  <tr key={`case-${c.case_id}`} className="hover:bg-secondary/50 transition-colors group">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link href={`/investigations/${c.case_id}`} className="font-mono text-sm font-medium text-primary hover:underline">
                        {c.case_id}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {c.pattern
                        ? c.pattern.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase())
                        : "Unknown"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={cn(
                          "text-sm font-medium",
                          c.final_risk_level === "HIGH" || c.final_risk_level === "CRITICAL"
                            ? "text-danger"
                            : c.final_risk_level === "MEDIUM"
                            ? "text-warning"
                            : "text-success"
                        )}
                      >
                        {c.fraud_probability != null
                          ? `${(c.fraud_probability * 100).toFixed(0)}%`
                          : "N/A"}
                      </span>
                      {c.final_risk_level && (
                        <span className="text-xs text-secondary-foreground ml-2">{c.final_risk_level}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <VerdictBadge verdict={c.final_verdict} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-foreground">
                      {safeAge(c.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <Link href={`/investigations/${c.case_id}`}>
                        <Button variant="outline" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                          Review
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}

                {/* Empty state */}
                {filteredCases.length === 0 && liveInvestigations.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-16 text-center text-secondary-foreground text-sm">
                      No investigations are currently available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function safeAge(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return `${formatDistanceToNow(new Date(dateStr))} ago`;
  } catch {
    return "—";
  }
}

function StatusBadge({ status }: { status: string | null }) {
  const s = (status || "").toUpperCase();
  if (s.includes("RUNNING") || s === "CREATED") return <Badge variant="primary">Investigating</Badge>;
  if (s.includes("ACTION_RECOMMENDED") || s.includes("AWAITING")) return <Badge variant="warning">Action Required</Badge>;
  if (s === "ACTION_TAKEN" || s === "RESOLVED") return <Badge variant="success">Resolved</Badge>;
  if (s === "ERROR") return <Badge variant="danger">Error</Badge>;
  return <Badge>{status || "Unknown"}</Badge>;
}

function VerdictBadge({ verdict }: { verdict: string | null }) {
  if (!verdict) return <span className="text-sm text-secondary-foreground">—</span>;
  const v = verdict.toLowerCase();
  if (v === "fraud") return <Badge variant="danger">Fraud</Badge>;
  if (v === "cleared") return <Badge variant="success">Cleared</Badge>;
  if (v === "uncertain") return <Badge variant="warning">Uncertain</Badge>;
  return <Badge>{verdict}</Badge>;
}
