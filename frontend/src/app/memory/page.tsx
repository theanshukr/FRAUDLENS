/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useEffect, useState } from "react";
import { getMemory, MemoryResponse } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { Database, RefreshCw, ShieldX } from "lucide-react";

type LoadState = "loading" | "success" | "error";

export default function MemoryPage() {
  const [data, setData] = useState<MemoryResponse | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");

  const load = () => {
    setState("loading");
    setErrorMsg("");
    getMemory()
      .then((res) => { setData(res); setState("success"); })
      .catch((err) => { setErrorMsg(err.message); setState("error"); });
  };

  useEffect(() => { load(); }, []);

  if (state === "loading") {
    return (
      <div className="p-8 space-y-8 max-w-[1400px] mx-auto animate-pulse">
        <div>
          <div className="h-8 bg-secondary rounded w-1/4 mb-2"></div>
          <div className="h-4 bg-secondary rounded w-2/4"></div>
        </div>
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="px-4 py-3"><div className="h-4 bg-secondary rounded w-16"></div></th>
                  <th className="px-4 py-3"><div className="h-4 bg-secondary rounded w-32"></div></th>
                  <th className="px-4 py-3"><div className="h-4 bg-secondary rounded w-24"></div></th>
                  <th className="px-4 py-3"><div className="h-4 bg-secondary rounded w-20"></div></th>
                  <th className="px-4 py-3"><div className="h-4 bg-secondary rounded w-32"></div></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[1, 2, 3, 4, 5].map(i => (
                  <tr key={i}>
                    <td className="px-4 py-4"><div className="h-4 bg-secondary rounded w-20"></div></td>
                    <td className="px-4 py-4"><div className="h-4 bg-secondary rounded w-48"></div></td>
                    <td className="px-4 py-4"><div className="h-6 bg-secondary rounded-full w-24"></div></td>
                    <td className="px-4 py-4"><div className="h-4 bg-secondary rounded w-24"></div></td>
                    <td className="px-4 py-4"><div className="h-6 bg-secondary rounded w-32"></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <Card className="p-8 max-w-md text-center">
          <ShieldX className="w-12 h-12 text-danger mx-auto mb-4" />
          <h2 className="text-lg font-semibold mb-2">Unable to load case memory</h2>
          <p className="text-sm text-secondary-foreground mb-6">{errorMsg}</p>
          <button onClick={load} className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="p-8 space-y-8 max-w-[1400px] mx-auto">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <Database className="w-6 h-6 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight">Case Memory</h1>
        </div>
        <p className="text-sm text-secondary-foreground mt-1">
          {data.total} historical closed cases used by the AI agent for pattern matching
        </p>
      </div>

      {data.historical_cases.length === 0 ? (
        <Card className="p-8 text-center text-secondary-foreground text-sm border-dashed">
          No historical cases available. The closed_cases_history.csv may be missing from dataset_sample/.
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="px-4 py-3 text-xs font-medium text-secondary-foreground uppercase">Case ID</th>
                  <th className="px-4 py-3 text-xs font-medium text-secondary-foreground uppercase">Pattern</th>
                  <th className="px-4 py-3 text-xs font-medium text-secondary-foreground uppercase">Outcome</th>
                  <th className="px-4 py-3 text-xs font-medium text-secondary-foreground uppercase">Exposure</th>
                  <th className="px-4 py-3 text-xs font-medium text-secondary-foreground uppercase">Actions</th>
                  <th className="px-4 py-3 text-xs font-medium text-secondary-foreground uppercase">SAR</th>
                  <th className="px-4 py-3 text-xs font-medium text-secondary-foreground uppercase">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.historical_cases.map((c) => (
                  <tr key={c.case_id} className="hover:bg-secondary/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-mono font-medium">{c.case_id}</td>
                    <td className="px-4 py-3 text-sm">
                      {c.pattern.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase())}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={c.outcome === "fraud_confirmed" ? "danger" : c.outcome === "cleared" ? "success" : "warning"}>
                        {c.outcome.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase())}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm font-medium">${c.exposure_usd.toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex flex-wrap gap-1">
                        {c.actions_taken.map((a, i) => (
                          <span key={i} className="text-xs bg-secondary px-1.5 py-0.5 rounded border border-border">
                            {a.replace(/_/g, " ")}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {c.report_filed ? <Badge variant="danger">Filed</Badge> : <span className="text-secondary-foreground">No</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-secondary-foreground max-w-[200px] truncate" title={c.analyst_notes || ""}>
                      {c.analyst_notes || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
