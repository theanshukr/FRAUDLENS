"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  Files,
  Network,
  BrainCircuit,
  Database,
  ShieldAlert,
  Settings,
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navigation = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Investigations", href: "/investigations", icon: Search },
  { name: "Evidence Explorer", href: "/evidence", icon: Files },
  { name: "Knowledge Graph", href: "/graph", icon: Network },
  { name: "AI Decisions", href: "/decisions", icon: BrainCircuit },
  { name: "Case Memory", href: "/memory", icon: Database },
  { name: "Policies", href: "/policies", icon: ShieldAlert },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col w-64 bg-surface border-r border-border h-full">
      <div className="flex items-center h-16 px-6 border-b border-border">
        <div className="flex items-center gap-2 text-primary">
          <ShieldAlert className="w-6 h-6" />
          <span className="font-semibold tracking-wide text-foreground">FRAUDLENS</span>
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname?.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                isActive
                  ? "bg-primary-light/50 text-primary"
                  : "text-secondary-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <item.icon
                className={cn(
                  "w-5 h-5",
                  isActive ? "text-primary" : "text-secondary-foreground"
                )}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
            pathname === "/settings"
              ? "bg-primary-light/50 text-primary"
              : "text-secondary-foreground hover:bg-secondary hover:text-foreground"
          )}
        >
          <Settings className={cn(
            "w-5 h-5",
            pathname === "/settings" ? "text-primary" : "text-secondary-foreground"
          )} />
          Settings
        </Link>
      </div>
    </div>
  );
}
