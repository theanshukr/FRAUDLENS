/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useEffect, useState } from "react";
import { getPolicies, PolicyResponse } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { RefreshCw, ShieldX } from "lucide-react";

type LoadState = "loading" | "success" | "error";

export default function PoliciesPage() {
  const [data, setData] = useState<PolicyResponse | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMsg, setErrorMsg] = useState("");

  const load = () => {
    setState("loading");
    setErrorMsg("");
    getPolicies()
      .then((res) => { setData(res); setState("success"); })
      .catch((err) => { setErrorMsg(err.message); setState("error"); });
  };

  useEffect(() => { load(); }, []);

  if (state === "loading") {
    return (
      <div className="p-8 animate-pulse space-y-4">
        <div className="h-8 bg-secondary rounded w-1/4"></div>
        {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-secondary rounded-lg"></div>)}
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <Card className="p-8 max-w-md text-center">
          <ShieldX className="w-12 h-12 text-danger mx-auto mb-4" />
          <h2 className="text-lg font-semibold mb-2">Unable to load policies</h2>
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
    <div className="p-8 space-y-8 max-w-[1200px] mx-auto">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Fraud Policies</h1>
        <p className="text-sm text-secondary-foreground mt-1">
          {data.total_rules} active policy rules governing fraud detection and response
        </p>
      </div>

      {/* Policy Rules */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium">Detection Rules</h2>
        {data.rules.map((rule) => (
          <Card key={rule.rule_id} className="p-5">
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 bg-primary/10 rounded-lg flex items-center justify-center shrink-0">
                <span className="text-primary font-semibold text-sm">{rule.rule_id}</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">{rule.description}</p>
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  {rule.threshold && (
                    <span className="text-xs font-mono bg-secondary text-secondary-foreground px-2 py-1 rounded border border-border">
                      {rule.threshold}
                    </span>
                  )}
                  {rule.actions.map((a) => (
                    <Badge key={a} variant={a.includes("BLOCK") ? "danger" : a.includes("MONITOR") ? "warning" : "default"}>
                      {a.replace(/_/g, " ")}
                    </Badge>
                  ))}
                  <Badge variant={rule.approval_route === "auto" ? "success" : rule.approval_route === "L1" ? "warning" : "danger"}>
                    {rule.approval_route === "auto" ? "Auto" : rule.approval_route}
                  </Badge>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Action Catalog */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium">Action Catalog</h2>
        <Card className="overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase">Action</th>
                <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase">Approval Route</th>
                <th className="px-6 py-3 text-xs font-medium text-secondary-foreground uppercase">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.actions.map((a) => (
                <tr key={a.action} className="hover:bg-secondary/30 transition-colors">
                  <td className="px-6 py-3 text-sm font-mono font-medium">{a.action}</td>
                  <td className="px-6 py-3">
                    <Badge variant={a.route === "auto" ? "success" : a.route === "L1" ? "warning" : "danger"}>
                      {a.route}
                    </Badge>
                  </td>
                  <td className="px-6 py-3 text-sm text-secondary-foreground">{a.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
