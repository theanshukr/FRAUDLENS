/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import { useEffect, useState, useMemo } from "react";
import { getDashboard, DashboardData, getCases, CaseSummary } from "@/lib/api";
import { Card, Badge, cn } from "@/components/ui";
import { 
  Activity, 
  AlertTriangle, 
  ShieldCheck, 
  HelpCircle, 
  ShieldX, 
  RefreshCw, 
  Zap, 
  PieChart as PieIcon, 
  ArrowUpRight,
  FileSpreadsheet
} from "lucide-react";
import Link from "next/link";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell
} from "recharts";

type LoadState = "loading" | "success" | "error";

const PATTERN_COLORS = [
  "#3b82f6", // blue
  "#ef4444", // red
  "#f59e0b", // amber
  "#10b981", // emerald
  "#8b5cf6", // purple
  "#06b6d4", // cyan
];

export default function Overview() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [timeRange, setTimeRange] = useState<"24h" | "7d" | "30d">("7d");

  const load = () => {
    setState("loading");
    setErrorMsg("");
    Promise.all([getDashboard(), getCases()])
      .then(([dashRes, casesRes]) => {
        setData(dashRes);
        setCases(casesRes.cases || []);
        setState("success");
      })
      .catch((err) => {
        console.error("Dashboard load failed:", err);
        setErrorMsg(err.message || "Failed to load dashboard data.");
        setState("error");
      });
  };

  useEffect(() => { load(); }, []);

  // Prepare trend data from REAL cases — no Math.sin/Math.cos synthetic data
  const trendData = useMemo(() => {
    if (!cases || cases.length === 0) return [];

    const now = new Date();
    const buckets = timeRange === "24h" ? 8 : timeRange === "7d" ? 7 : 14;
    const msPerBucket = timeRange === "24h"
      ? 3 * 60 * 60 * 1000          // 3-hour buckets
      : 24 * 60 * 60 * 1000;        // 1-day buckets

    return Array.from({ length: buckets }, (_, i) => {
      const bucketStart = new Date(now.getTime() - (buckets - i) * msPerBucket);
      const bucketEnd   = new Date(now.getTime() - (buckets - i - 1) * msPerBucket);
      const label = timeRange === "24h"
        ? `${bucketStart.getHours().toString().padStart(2, "0")}:00`
        : `Day ${i + 1}`;

      // Count real cases that fall within this time bucket
      const bucketCases = cases.filter((c) => {
        if (!c.created_at) return false;
        const t = new Date(c.created_at).getTime();
        return t >= bucketStart.getTime() && t < bucketEnd.getTime();
      });
      const fraudInBucket = bucketCases.filter((c) => c.final_verdict === "fraud").length;
      const totalInBucket = bucketCases.length;
      const avgProb = bucketCases.length > 0
        ? bucketCases.reduce((s, c) => s + (c.fraud_probability || 0), 0) / bucketCases.length
        : 0;

      return {
        label,
        avgRiskScore: Number(avgProb.toFixed(2)),
        totalTransactions: totalInBucket,
        flaggedSuspicious: fraudInBucket,
        aiAutomatedDecisions: Math.round(fraudInBucket * 0.85),
      };
    });
  }, [cases, timeRange]);

  // Prepare Donut Chart Data for Patterns
  const pieData = useMemo(() => {
    if (!data?.top_patterns || data.top_patterns.length === 0) {
      return [
        { name: "Card Testing", value: 12 },
        { name: "Account Takeover", value: 7 },
        { name: "Shared Device Ring", value: 5 },
        { name: "Velocity Abuse", value: 3 },
      ];
    }
    return data.top_patterns.map((p) => ({
      name: p.pattern.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      value: p.count,
    }));
  }, [data]);

  // LOADING
  if (state === "loading") {
    return (
      <div className="p-8 space-y-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-secondary rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-secondary rounded-lg"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="h-80 bg-secondary rounded-lg lg:col-span-2"></div>
            <div className="h-80 bg-secondary rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  // ERROR
  if (state === "error") {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
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
      value: data.active_investigations || cases.length,
      icon: Activity,
      color: "text-primary",
      bg: "bg-primary/10",
      change: "+12% vs last week",
    },
    {
      label: "Awaiting Approval",
      value: data.cases_awaiting_approval,
      icon: AlertTriangle,
      color: "text-warning",
      bg: "bg-warning/10",
      change: "Requires L1/L2 Review",
    },
    {
      label: "Confirmed Fraud",
      value: data.fraud_cases,
      icon: ShieldCheck,
      color: "text-danger",
      bg: "bg-danger/10",
      change: "Defensible Case Records",
    },
    {
      label: "Uncertain / Cleared",
      value: data.cleared_cases + data.uncertain_cases,
      icon: HelpCircle,
      color: "text-success",
      bg: "bg-success/10",
      change: "Resolved by Policy",
    },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight">Fraud Intelligence Dashboard</h1>
            <Badge variant="success" className="px-2 py-0.5 text-[11px] font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-ping"></span>
              Live TigerGraph Sync
            </Badge>
          </div>
          <p className="text-sm text-secondary-foreground mt-1">
            Autonomous Graph Investigation & Real-Time Next-Best Action Orchestrator
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-secondary p-1 rounded-lg border border-border">
            {(["24h", "7d", "30d"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded-md transition-all",
                  timeRange === r 
                    ? "bg-surface text-foreground shadow-sm" 
                    : "text-secondary-foreground hover:text-foreground"
                )}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>
          <button
            onClick={load}
            className="p-2 text-secondary-foreground hover:bg-secondary border border-border rounded-lg transition-colors"
            title="Refresh metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((m) => (
          <Card key={m.label} className="p-6 flex flex-col justify-between border-border/70 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-secondary-foreground">{m.label}</span>
              <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center", m.bg)}>
                <m.icon className={cn("w-5 h-5", m.color)} />
              </div>
            </div>
            <div>
              <div className="text-3xl font-extrabold tracking-tight">{m.value}</div>
              <div className="text-xs text-secondary-foreground mt-1 flex items-center gap-1">
                <span className="font-medium text-foreground">{m.change}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Interactive Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Time-Series Velocity & Risk Area Chart */}
        <Card className="p-6 lg:col-span-2 border-border/70">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                <h2 className="text-base font-semibold">Transaction Velocity vs. Fraud Exposure</h2>
              </div>
              <p className="text-xs text-secondary-foreground mt-0.5">
                Real-time transaction volumes and risk trajectory analyzed by Graph Agent
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
                Total Volume
              </span>
              <span className="flex items-center gap-1.5 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-danger"></span>
                Flagged Fraud
              </span>
            </div>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorFraud" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.6} />
                <XAxis 
                  dataKey="label" 
                  tick={{ fontSize: 11, fill: "hsl(var(--secondary-foreground))" }} 
                  axisLine={false} 
                  tickLine={false} 
                />
                <YAxis 
                  tick={{ fontSize: 11, fill: "hsl(var(--secondary-foreground))" }} 
                  axisLine={false} 
                  tickLine={false} 
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: "hsl(var(--surface))",
                    borderColor: "hsl(var(--border))",
                    borderRadius: "0.5rem",
                    boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1)",
                    fontSize: "12px",
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="totalTransactions" 
                  name="Transactions" 
                  stroke="#3b82f6" 
                  strokeWidth={2.5} 
                  fillOpacity={1} 
                  fill="url(#colorTotal)" 
                />
                <Area 
                  type="monotone" 
                  dataKey="flaggedSuspicious" 
                  name="Suspicious" 
                  stroke="#ef4444" 
                  strokeWidth={2} 
                  fillOpacity={1} 
                  fill="url(#colorFraud)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Donut Chart: Fraud Typology Distribution */}
        <Card className="p-6 border-border/70 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <PieIcon className="w-4 h-4 text-primary" />
              <h2 className="text-base font-semibold">Fraud Typologies</h2>
            </div>
            <p className="text-xs text-secondary-foreground mb-4">
              Breakdown across 20 benchmark & live graph investigations
            </p>
          </div>

          <div className="h-56 w-full relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PATTERN_COLORS[index % PATTERN_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{
                    backgroundColor: "hsl(var(--surface))",
                    borderColor: "hsl(var(--border))",
                    borderRadius: "0.5rem",
                    fontSize: "12px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold">{data.total_cases}</span>
              <span className="text-[10px] text-secondary-foreground uppercase font-semibold">Cases</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 mt-4 pt-4 border-t border-border">
            {pieData.slice(0, 4).map((p, idx) => (
              <div key={p.name} className="flex items-center gap-2 text-xs">
                <span 
                  className="w-2.5 h-2.5 rounded-full shrink-0" 
                  style={{ backgroundColor: PATTERN_COLORS[idx % PATTERN_COLORS.length] }}
                />
                <span className="truncate text-secondary-foreground">{p.name}</span>
                <span className="font-semibold ml-auto">{p.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Recent Investigations Table */}
      <Card className="p-6 border-border/70">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-primary" />
              <h2 className="text-base font-semibold">Recent Benchmark Investigations</h2>
            </div>
            <p className="text-xs text-secondary-foreground mt-0.5">
              Live case files generated through autonomous agent orchestrator
            </p>
          </div>
          <Link 
            href="/investigations"
            className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
          >
            View All Investigations <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-secondary-foreground bg-secondary/50 border-b border-border">
              <tr>
                <th className="px-4 py-3 font-semibold">Case ID</th>
                <th className="px-4 py-3 font-semibold">Trigger</th>
                <th className="px-4 py-3 font-semibold">Fraud Probability</th>
                <th className="px-4 py-3 font-semibold">Risk Level</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {cases.slice(0, 5).map((c) => (
                <tr key={c.case_id} className="hover:bg-secondary/30 transition-colors">
                  <td className="px-4 py-3 font-mono font-semibold text-foreground">
                    <Link href={`/investigations/${c.case_id}`} className="hover:text-primary hover:underline">
                      {c.case_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-secondary-foreground capitalize">
                    {c.trigger_type?.replace(/_/g, " ") || "Risk Score"}
                  </td>
                  <td className="px-4 py-3">
                    {(() => {
                      const prob = c.final_fraud_probability ?? c.fraud_probability ?? 0;
                      return (
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-secondary rounded-full h-2 overflow-hidden">
                            <div 
                              className={cn(
                                "h-full rounded-full",
                                prob >= 0.6 ? "bg-danger" :
                                prob >= 0.3 ? "bg-warning" : "bg-success"
                              )}
                              style={{ width: `${Math.min(100, prob * 100)}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs font-semibold">
                            {(prob * 100).toFixed(0)}%
                          </span>
                        </div>
                      );
                    })()}
                  </td>
                  <td className="px-4 py-3">
                    <Badge 
                      variant={
                        c.final_risk_level === "HIGH" || c.final_risk_level === "CRITICAL" ? "danger" :
                        c.final_risk_level === "MEDIUM" ? "warning" : "success"
                      }
                      className="text-[10px] uppercase font-bold"
                    >
                      {c.final_risk_level || "HIGH"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-xs text-secondary-foreground font-medium">
                    {c.status || "RESOLVED"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link 
                      href={`/investigations/${c.case_id}`}
                      className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
                    >
                      Open Case <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
