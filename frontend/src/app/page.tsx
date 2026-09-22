/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useEffect, useState } from "react";
import { getDashboard, DashboardData } from "@/lib/api";
import { Card } from "@/components/ui";
import { Activity, AlertTriangle, ShieldCheck, HelpCircle, TrendingUp, ShieldX, BarChart3, RefreshCw } from "lucide-react";

type LoadState = "loading" | "success" | "error";

export default function Overview() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");

  const load = () => {
    setState("loading");
    setErrorMsg("");
    getDashboard()
      .then((res) => {
        setData(res);
        setState("success");
      })
      .catch((err) => {
        console.error("Dashboard load failed:", err);
        setErrorMsg(err.message || "Failed to load dashboard data.");
        setState("error");
      });
  };

  useEffect(() => { load(); }, []);

  // LOADING
  if (state === "loading") {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-secondary rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-secondary rounded-lg"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-64 bg-secondary rounded-lg"></div>
            <div className="h-64 bg-secondary rounded-lg"></div>
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
          <h2 className="text-lg font-semibold mb-2">Unable to load dashboard</h2>
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

  if (!data) return null;

  const metrics = [
    {
      label: "Active Investigations",
      value: data.active_investigations,
      icon: Activity,
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      label: "Awaiting Approval",
      value: data.cases_awaiting_approval,
      icon: AlertTriangle,
      color: "text-warning",
      bg: "bg-warning/10",
    },
    {
      label: "Confirmed Fraud",
      value: data.fraud_cases,
      icon: ShieldCheck,
      color: "text-danger",
      bg: "bg-danger/10",
    },
    {
      label: "Uncertain Cases",
      value: data.uncertain_cases,
      icon: HelpCircle,
      color: "text-accent",
      bg: "bg-accent/10",
    },
  ];

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="text-sm text-secondary-foreground mt-1">
            Platform health and investigation metrics — {data.total_cases} total cases on file
          </p>
        </div>
        <button
          onClick={load}
          className="p-2 text-secondary-foreground hover:bg-secondary rounded-md transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Primary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((m) => (
          <Card key={m.label} className="p-6 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-secondary-foreground">{m.label}</p>
              <p className="text-3xl font-semibold mt-2">{m.value}</p>
            </div>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${m.bg}`}>
              <m.icon className={`w-6 h-6 ${m.color}`} />
            </div>
          </Card>
        ))}
      </div>

      {/* Secondary Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Fraud Patterns */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-medium">Top Fraud Patterns</h2>
          </div>
          <div className="space-y-3">
            {data.top_patterns.length > 0 ? (
              data.top_patterns.map((p, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 border border-border"
                >
                  <span className="text-sm font-medium">
                    {p.pattern.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </span>
                  <span className="text-sm text-secondary-foreground bg-surface px-2 py-1 rounded border border-border">
                    {p.count} {p.count === 1 ? "case" : "cases"}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-sm text-secondary-foreground text-center py-8 border border-border border-dashed rounded-lg">
                No fraud patterns detected yet. Cases will appear once investigations are completed.
              </div>
            )}
          </div>
        </Card>

        {/* System Metrics */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-medium">System Metrics</h2>
          </div>
          <div className="space-y-4">
            <MetricRow label="Total Cases Processed" value={String(data.total_cases)} />
            <MetricRow label="High Risk Cases" value={String(data.high_risk_cases)} />
            <MetricRow label="Cleared Cases" value={String(data.cleared_cases)} />
            <MetricRow
              label="Avg Fraud Probability"
              value={
                data.total_cases > 0
                  ? `${(data.avg_fraud_probability * 100).toFixed(1)}%`
                  : "N/A"
              }
            />
          </div>
        </Card>
      </div>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border pb-3 last:border-0 last:pb-0">
      <span className="text-sm text-secondary-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}
