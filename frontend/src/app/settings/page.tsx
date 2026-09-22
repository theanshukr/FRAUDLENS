/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/no-unescaped-entities */
"use client";

import { useState } from "react";
import { useTheme } from "@/components/ThemeProvider";
import { Card, Button, cn } from "@/components/ui";
import { Settings2, Monitor, Moon, Sun, Shield, Bell, Key } from "lucide-react";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  
  // Dummy state for display settings since we are just persisting in frontend
  const [density, setDensity] = useState("comfortable");
  const [autoRefresh, setAutoRefresh] = useState(false);

  return (
    <div className="flex h-full bg-background max-w-[1200px] mx-auto">
      {/* Sidebar Navigation */}
      <div className="w-64 border-r border-border p-6 space-y-6 shrink-0">
        <div>
          <h2 className="text-xs font-semibold text-secondary-foreground uppercase tracking-wider mb-4">Settings</h2>
          <nav className="space-y-1">
            <button className="w-full flex items-center gap-3 px-3 py-2 rounded-md bg-secondary text-foreground text-sm font-medium">
              <Monitor className="w-4 h-4" /> Appearance
            </button>
            <button className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-secondary-foreground hover:bg-secondary/50 text-sm font-medium transition-colors">
              <Shield className="w-4 h-4" /> Application
            </button>
            <button className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-secondary-foreground hover:bg-secondary/50 text-sm font-medium transition-colors">
              <Bell className="w-4 h-4" /> Notifications
            </button>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-10 overflow-y-auto">
        <div className="max-w-2xl space-y-10">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight mb-2">Appearance & Display</h1>
            <p className="text-sm text-secondary-foreground">Manage how FRAUDLENS looks and feels on your device.</p>
          </div>

          <div className="space-y-6">
            {/* Theme Settings */}
            <Card className="p-6">
              <h2 className="text-base font-semibold mb-4">Theme Preference</h2>
              <div className="grid grid-cols-3 gap-4">
                <button
                  onClick={() => setTheme("light")}
                  className={cn(
                    "flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-all",
                    theme === "light" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                  )}
                >
                  <Sun className={cn("w-6 h-6", theme === "light" ? "text-primary" : "text-secondary-foreground")} />
                  <span className="text-sm font-medium">Light</span>
                </button>
                <button
                  onClick={() => setTheme("dark")}
                  className={cn(
                    "flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-all",
                    theme === "dark" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                  )}
                >
                  <Moon className={cn("w-6 h-6", theme === "dark" ? "text-primary" : "text-secondary-foreground")} />
                  <span className="text-sm font-medium">Dark</span>
                </button>
                <button
                  onClick={() => setTheme("system")}
                  className={cn(
                    "flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-all",
                    theme === "system" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                  )}
                >
                  <Monitor className={cn("w-6 h-6", theme === "system" ? "text-primary" : "text-secondary-foreground")} />
                  <span className="text-sm font-medium">System</span>
                </button>
              </div>
            </Card>

            {/* Display Settings */}
            <Card className="p-6">
              <h2 className="text-base font-semibold mb-4">Workspace Display</h2>
              
              <div className="space-y-6">
                <div>
                  <label className="text-sm font-medium mb-3 block">Timeline Density</label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="radio" 
                        name="density" 
                        checked={density === "compact"} 
                        onChange={() => setDensity("compact")} 
                        className="text-primary focus:ring-primary h-4 w-4"
                      />
                      <span className="text-sm">Compact</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="radio" 
                        name="density" 
                        checked={density === "comfortable"} 
                        onChange={() => setDensity("comfortable")} 
                        className="text-primary focus:ring-primary h-4 w-4"
                      />
                      <span className="text-sm">Comfortable</span>
                    </label>
                  </div>
                </div>
                
                <div className="pt-4 border-t border-border">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div>
                      <div className="text-sm font-medium">Auto-refresh Active Investigations</div>
                      <div className="text-xs text-secondary-foreground mt-1">Automatically refresh workspace when AI agent adds new timeline events.</div>
                    </div>
                    <div className={cn(
                      "w-10 h-6 rounded-full transition-colors relative",
                      autoRefresh ? "bg-primary" : "bg-secondary"
                    )} onClick={() => setAutoRefresh(!autoRefresh)}>
                      <div className={cn(
                        "w-4 h-4 bg-white rounded-full absolute top-1 transition-transform",
                        autoRefresh ? "translate-x-5" : "translate-x-1"
                      )} />
                    </div>
                  </label>
                </div>
              </div>
            </Card>

            {/* Connection Info */}
            <Card className="p-6">
              <h2 className="text-base font-semibold mb-4">Application</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-secondary-foreground">Backend API URL</span>
                  <span className="text-sm font-mono bg-secondary px-2 py-1 rounded">
                    {process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-secondary-foreground">Frontend Version</span>
                  <span className="text-sm font-mono">v0.1.0-beta</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-secondary-foreground">Analyst Role</span>
                  <span className="text-sm font-medium bg-primary/10 text-primary px-2 py-1 rounded">Level 2 Investigator</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
