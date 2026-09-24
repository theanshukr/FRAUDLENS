/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/no-unescaped-entities */
/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { getCases, getGraph, expandGraph, CaseSummary, GraphResponse, GraphNode, GraphEdge } from "@/lib/api";
import { Badge, cn } from "@/components/ui";
import { 
  Search, 
  Network, 
  AlertCircle, 
  Smartphone, 
  Activity, 
  User, 
  CreditCard, 
  Box, 
  Info, 
  MapPin,
  Mail, 
  Sparkles, 
  RefreshCw,
  Filter,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Layers,
  ZoomIn,
  Target,
  RotateCcw,
  Zap,
  Radio,
  ExternalLink,
  ShieldAlert,
  Server,
  Maximize2,
  Minimize2,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import ReactFlow, { 
  Background, 
  Controls, 
  useNodesState, 
  useEdgesState,
  MarkerType,
  Handle,
  Position,
  Panel,
  useReactFlow,
  ReactFlowProvider
} from "reactflow";
import "reactflow/dist/style.css";
import dagre from "dagre";

// --- Dagre Layout ---
const getLayoutedElements = (nodes: any[], edges: any[], direction = 'TB') => {
  if (!nodes || nodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 120, ranksep: 140 });

  const nodeMap = new Set(nodes.map((n) => n.id));

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 250, height: 100 });
  });

  const validEdges = edges.filter((edge) => nodeMap.has(edge.source) && nodeMap.has(edge.target));

  validEdges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  try {
    dagre.layout(dagreGraph);
  } catch (err) {
    console.warn("Dagre layout warning:", err);
  }

  const layoutedNodes = nodes.map((node, idx) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const x = nodeWithPosition ? nodeWithPosition.x - 250 / 2 : (idx % 3) * 280 + 50;
    const y = nodeWithPosition ? nodeWithPosition.y - 100 / 2 : Math.floor(idx / 3) * 160 + 50;

    return {
      ...node,
      targetPosition: direction === 'TB' ? Position.Top : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
      position: { x, y },
    };
  });

  return { nodes: layoutedNodes, edges: validEdges };
};

// --- Custom Entity Node (Clean Light Theme) ---
const EntityNode = ({ data, selected }: any) => {
  const Icon = data.icon || Network;
  const isFlaggedTxn = data.type === "Transaction" && data.suspicious;
  const isSuspicious = Boolean(data.suspicious);
  const badgeText = data.status_badge || (isFlaggedTxn ? "FLAGGED TXN" : isSuspicious ? "SUSPICIOUS" : "VALID");

  return (
    <div className={cn(
      "px-4 py-3 rounded-xl border flex flex-col gap-2 min-w-[230px] transition-all cursor-pointer backdrop-blur-md shadow-sm",
      isFlaggedTxn
        ? "border-rose-500 bg-rose-50 text-rose-950 ring-2 ring-rose-500/30 shadow-rose-200 shadow-md"
        : isSuspicious 
        ? "border-amber-400 bg-amber-50/90 text-amber-950 ring-2 ring-amber-400/20 shadow-amber-100 shadow-md" 
        : "border-slate-200 bg-white text-slate-800 hover:border-blue-400 hover:shadow-md shadow-slate-100",
      selected ? "ring-2 ring-blue-500 ring-offset-2 ring-offset-white scale-[1.03]" : ""
    )}>
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5 !bg-blue-500 !border-2 !border-white" />
      <div className="flex items-center gap-3">
        <div className={cn(
          "p-2.5 rounded-lg shrink-0", 
          isFlaggedTxn ? "bg-rose-100 text-rose-600" :
          isSuspicious ? "bg-amber-100 text-amber-700" : "bg-blue-50 text-blue-600"
        )}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-500 mb-0.5 flex items-center justify-between">
            <span className="truncate">{data.type}</span>
            <span className={cn(
              "text-[9px] font-extrabold px-1.5 py-0.5 rounded border shrink-0",
              isFlaggedTxn 
                ? "text-rose-700 bg-rose-100 border-rose-300 animate-pulse" 
                : isSuspicious 
                ? "text-amber-800 bg-amber-100 border-amber-300" 
                : "text-emerald-700 bg-emerald-50 border-emerald-200"
            )}>
              {badgeText}
            </span>
          </div>
          <div className={cn("text-xs font-mono font-bold truncate", isFlaggedTxn ? "text-rose-900" : isSuspicious ? "text-amber-950" : "text-slate-900")}>
            {data.label}
          </div>
          {data.properties?.amount && (
            <div className="text-[10px] font-mono text-slate-600 mt-0.5">
              Amt: <span className="font-semibold text-rose-600">{data.properties.amount}</span>
            </div>
          )}
          {data.properties?.risk_score && data.properties.risk_score !== "—" && (
            <div className="text-[10px] font-mono text-slate-600">
              Risk: <span className="font-semibold text-amber-600">{data.properties.risk_score}</span>
            </div>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5 !bg-blue-500 !border-2 !border-white" />
    </div>
  );
};

const nodeTypes = {
  entity: EntityNode,
};

// --- Graph Canvas Inner Component (Light Theme) ---
const GraphCanvas = ({ 
  nodesData, 
  edgesData, 
  suspiciousNodes, 
  suspiciousEdges,
  highlightedPaths,
  filterType,
  relFilters,
  onNodeClick,
  onEdgeClick
}: { 
  nodesData: any[], 
  edgesData: any[],
  suspiciousNodes: string[],
  suspiciousEdges: string[],
  highlightedPaths: string[][],
  filterType: string,
  relFilters: Set<string>,
  onNodeClick: (node: any) => void,
  onEdgeClick: (edge: any) => void
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView } = useReactFlow();

  useEffect(() => {
    if (!nodesData || nodesData.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    // Apply entity filter
    const filteredNodesData = nodesData.filter((n: any) => {
      if (filterType === "ALL") return true;
      const t = (n.type || "").toLowerCase();
      if (filterType === "CUSTOMERS") return t.includes("customer") || t.includes("user");
      if (filterType === "CARDS") return t.includes("card");
      if (filterType === "TRANSACTIONS") return t.includes("transaction") || t.includes("txn");
      if (filterType === "DEVICES") return t.includes("device") || t.includes("profile");
      if (filterType === "CASES") return t.includes("case") || t.includes("closedcase");
      if (filterType === "CONNECTIONS") return n.suspicious || suspiciousNodes?.includes(n.id);
      return true;
    });

    const activeNodeIds = new Set(filteredNodesData.map((n: any) => n.id));

    const mappedNodes = filteredNodesData.map((n: any) => {
      let icon = Box;
      const t = (n.type || "").toLowerCase();
      if (t.includes('card')) icon = CreditCard;
      else if (t.includes('customer') || t.includes('user') || t.includes('identity')) icon = User;
      else if (t.includes('device') || t.includes('profile')) icon = Smartphone;
      else if (t.includes('transaction') || t.includes('txn')) icon = Activity;
      else if (t.includes('billing') || t.includes('region')) icon = MapPin;
      else if (t.includes('case') || t.includes('closedcase')) icon = FileText;
      else if (t.includes('email') || t.includes('domain')) icon = Mail;

      return {
        id: n.id,
        type: 'entity',
        data: { 
          ...n,
          label: n.label || n.id, 
          type: n.type, 
          suspicious: Boolean(n.suspicious || suspiciousNodes?.includes(n.id)),
          status_badge: n.status_badge,
          icon
        },
        position: { x: 0, y: 0 }
      };
    });
    
    // Filter and deduplicate edges
    const edgePairMap = new Map<string, any>();
    (edgesData || []).forEach((e: any) => {
      if (!e.source || !e.target || e.source === e.target) return;
      if (!activeNodeIds.has(e.source) || !activeNodeIds.has(e.target)) return;
      if (relFilters.size > 0 && !relFilters.has(e.type?.toUpperCase())) return;
      const pairKey = [e.source, e.target, e.type].join("---");
      if (!edgePairMap.has(pairKey)) {
        edgePairMap.set(pairKey, { ...e });
      }
    });

    const uniqueEdges = Array.from(edgePairMap.values());

    const mappedEdges = uniqueEdges.map((e: any, idx: number) => {
      const isSuspicious = Boolean(
        e.suspicious || 
        suspiciousEdges?.includes(`${e.source}-${e.target}`) || 
        suspiciousEdges?.includes(`${e.target}-${e.source}`) ||
        (suspiciousNodes?.includes(e.source) && suspiciousNodes?.includes(e.target))
      );

      return {
        id: `edge-${e.source}-${e.target}-${e.type || idx}`,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        data: { ...e },
        label: e.label || e.type,
        animated: isSuspicious,
        style: { 
          stroke: isSuspicious ? '#e11d48' : '#94a3b8',
          strokeWidth: isSuspicious ? 2.5 : 1.5,
          strokeDasharray: isSuspicious ? '5,5' : undefined,
        },
        labelStyle: { fill: isSuspicious ? '#be123c' : '#475569', fontWeight: 700, fontSize: 10, fontFamily: 'monospace' },
        labelBgStyle: { fill: isSuspicious ? '#fff1f2' : '#ffffff', fillOpacity: 0.95, rx: 4, ry: 4, stroke: isSuspicious ? '#fecdd3' : '#e2e8f0', strokeWidth: 1 },
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 4,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isSuspicious ? '#e11d48' : '#94a3b8',
        }
      };
    });

    const layouted = getLayoutedElements(mappedNodes, mappedEdges);
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    
    const timer = setTimeout(() => {
      try {
        fitView({ padding: 0.2, duration: 500 });
      } catch (e) {
        console.warn("fitView warning:", e);
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [nodesData, edgesData, suspiciousNodes, suspiciousEdges, filterType, relFilters, setNodes, setEdges, fitView]);

  return (
    <div className="w-full h-full relative bg-slate-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick(node.data)}
        onEdgeClick={(_, edge) => onEdgeClick(edge.data)}
        onPaneClick={() => { onNodeClick(null); onEdgeClick(null); }}
        nodeTypes={nodeTypes}
        minZoom={0.1}
        maxZoom={3}
        fitView
        className="w-full h-full"
      >
        <Background color="#cbd5e1" gap={24} size={1} />
        <Controls className="bg-white border border-slate-200 shadow-md rounded-xl overflow-hidden text-slate-700 fill-slate-700" />
        
        {/* Graph Legend (Light Theme) */}
        <Panel position="bottom-left" className="bg-white/95 backdrop-blur-md border border-slate-200 p-3.5 rounded-xl shadow-lg mb-4 ml-4 z-10 space-y-2 min-w-[210px]">
          <h4 className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500">TIGERGRAPH LEGEND</h4>
          <div className="space-y-1.5 text-[11px] font-mono">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full border border-blue-500 bg-blue-100"></div>
              <span className="text-slate-700">Legitimate Vertex</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full border border-amber-500 bg-amber-100"></div>
              <span className="text-amber-800 font-semibold">Suspicious / Shared</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full border border-rose-500 bg-rose-500"></div>
              <span className="text-rose-700 font-bold">Flagged Transaction</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-slate-400"></div>
              <span className="text-slate-600">Direct TigerGraph Edge</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 border-t-2 border-dashed border-rose-500"></div>
              <span className="text-rose-600 font-bold">Attack / Risk Path</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

// --- Main Page Component (Light Theme) ---
export default function GraphPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [expanding, setExpanding] = useState(false);
  const [expansionMsg, setExpansionMsg] = useState<{ type: "success" | "info" | "error"; text: string } | null>(null);
  const [search, setSearch] = useState("");
  const [hops, setHops] = useState<number>(1);
  const [filterType, setFilterType] = useState<string>("ALL");
  const [activeRelFilters, setActiveRelFilters] = useState<Set<string>>(new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [hideSidebar, setHideSidebar] = useState(false);
  const graphContainerRef = useRef<HTMLDivElement>(null);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      if (graphContainerRef.current?.requestFullscreen) {
        graphContainerRef.current.requestFullscreen().catch(() => {});
      }
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);
  
  // Cache to store graph data per case + hop level
  const [graphCache, setGraphCache] = useState<Record<string, GraphResponse>>({});
  
  // Selection state
  const [selectedNodeData, setSelectedNodeData] = useState<any | null>(null);
  const [selectedEdgeData, setSelectedEdgeData] = useState<any | null>(null);

  useEffect(() => {
    setLoadingCases(true);
    getCases()
      .then((res) => {
        const cList = res.cases || [];
        setCases(cList);
        if (cList.length > 0 && !selectedCase) {
          setSelectedCase(cList[0].case_id);
        }
      })
      .catch((err) => console.error("Failed to load cases list", err))
      .finally(() => setLoadingCases(false));
  }, []);

  const loadCaseGraph = useCallback((caseId: string, hopDepth = 1, force = false) => {
    if (!caseId) return;
    setSelectedNodeData(null);
    setSelectedEdgeData(null);
    setExpansionMsg(null);

    const cacheKey = `${caseId}_h${hopDepth}`;
    if (!force && graphCache[cacheKey]) {
      return;
    }

    setLoadingGraph(true);
    getGraph(caseId, hopDepth)
      .then((res: GraphResponse) => {
        setGraphCache((prev) => ({
          ...prev,
          [cacheKey]: res,
          [caseId]: res
        }));
      })
      .catch((err) => console.error("Failed to load graph", err))
      .finally(() => setLoadingGraph(false));
  }, [graphCache]);

  useEffect(() => {
    if (selectedCase) {
      loadCaseGraph(selectedCase, hops);
    }
  }, [selectedCase, hops]);

  // Handle Hop Change
  const handleHopChange = (newHops: number) => {
    setHops(newHops);
    if (selectedCase) {
      loadCaseGraph(selectedCase, newHops, true);
    }
  };

  // Real Multi-Hop TigerGraph Expansion (Zero Synthetic Data)
  const handleExpandNeighbors = async (expandHops: number = 1) => {
    if (!selectedCase || !selectedNodeData) return;
    setExpanding(true);
    setExpansionMsg(null);

    try {
      const res = await expandGraph(
        selectedCase, 
        selectedNodeData.id, 
        selectedNodeData.type || "Transaction", 
        expandHops
      );
      const newNodes = res.nodes || [];
      const newEdges = res.edges || [];

      if (newNodes.length === 0 && newEdges.length === 0) {
        setExpansionMsg({ type: "info", text: "No additional live TigerGraph neighbors found." });
        return;
      }

      const cacheKey = `${selectedCase}_h${hops}`;
      const current = graphCache[cacheKey] || graphCache[selectedCase] || { 
        nodes: [], 
        edges: [], 
        suspicious_nodes: [], 
        suspicious_edges: [],
        highlighted_paths: [],
        hops,
        access_mode: "DIRECT",
        mcp_calls: 0,
        tg_status: "CONNECTED"
      };

      const existingNodeIds = new Set(current.nodes.map((n: any) => n.id));
      const mergedNodes = [...current.nodes];
      let addedNodesCount = 0;

      newNodes.forEach((node: any) => {
        if (!existingNodeIds.has(node.id)) {
          mergedNodes.push(node);
          existingNodeIds.add(node.id);
          addedNodesCount++;
        }
      });

      const existingEdgeKeys = new Set(current.edges.map((e: any) => `${e.source}-${e.target}-${e.type}`));
      const mergedEdges = [...current.edges];
      let addedEdgesCount = 0;

      newEdges.forEach((edge: any) => {
        const k1 = `${edge.source}-${edge.target}-${edge.type}`;
        const k2 = `${edge.target}-${edge.source}-${edge.type}`;
        if (!existingEdgeKeys.has(k1) && !existingEdgeKeys.has(k2)) {
          mergedEdges.push(edge);
          existingEdgeKeys.add(k1);
          addedEdgesCount++;
        }
      });

      const updatedGraph: GraphResponse = {
        ...current,
        nodes: mergedNodes,
        edges: mergedEdges,
        suspicious_nodes: Array.from(new Set([...(current.suspicious_nodes || [])])),
        suspicious_edges: Array.from(new Set([...(current.suspicious_edges || [])])),
      };

      setGraphCache((prev) => ({
        ...prev,
        [cacheKey]: updatedGraph,
        [selectedCase]: updatedGraph
      }));

      setExpansionMsg({
        type: "success",
        text: `+${addedNodesCount} entities, +${addedEdgesCount} relationships expanded from TigerGraph`
      });
    } catch (err: any) {
      console.error("Expansion error:", err);
      setExpansionMsg({ type: "error", text: "Unable to expand this node. TigerGraph query failed." });
    } finally {
      setExpanding(false);
    }
  };

  const filteredCases = useMemo(() => {
    return cases.filter((c) => 
      !search || 
      c.case_id?.toLowerCase().includes(search.toLowerCase()) ||
      c.pattern?.toLowerCase().includes(search.toLowerCase()) ||
      (c.customer_id && c.customer_id.toLowerCase().includes(search.toLowerCase())) ||
      (c.card_id && c.card_id.toLowerCase().includes(search.toLowerCase()))
    );
  }, [cases, search]);

  const cacheKey = selectedCase ? `${selectedCase}_h${hops}` : "";
  const currentGraph = selectedCase ? (graphCache[cacheKey] || graphCache[selectedCase]) : null;

  // Available relationship types in active graph
  const availableRelTypes = useMemo(() => {
    if (!currentGraph?.edges) return [];
    const types = new Set<string>();
    currentGraph.edges.forEach((e) => {
      if (e.type) types.add(e.type.toUpperCase());
    });
    return Array.from(types);
  }, [currentGraph]);

  const toggleRelFilter = (relType: string) => {
    setActiveRelFilters((prev) => {
      const next = new Set(prev);
      if (next.has(relType)) {
        next.delete(relType);
      } else {
        next.add(relType);
      }
      return next;
    });
  };

  const nodeCount = currentGraph?.nodes?.length || 0;
  const edgeCount = currentGraph?.edges?.length || 0;
  const accessMode = currentGraph?.access_mode || "DIRECT";
  const mcpCalls = currentGraph?.mcp_calls || 0;
  const isTgConnected = currentGraph?.tg_status === "CONNECTED";

  // Dynamic Graph Insight
  const graphInsight = useMemo(() => {
    if (!currentGraph || !currentGraph.nodes || currentGraph.nodes.length === 0) return null;
    const nodes = currentGraph.nodes;
    const edges = currentGraph.edges || [];
    
    const cardNodes = nodes.filter((n: any) => (n.type || "").toLowerCase().includes("card"));
    const devNodes = nodes.filter((n: any) => (n.type || "").toLowerCase().includes("device") || (n.type || "").toLowerCase().includes("profile"));
    const suspiciousCount = nodes.filter((n: any) => n.suspicious).length;

    const insights: string[] = [];
    if (nodes.length <= 2) {
      return {
        isSparse: true,
        text: "Limited 1-hop view. Click [+1 Hop] or select an entity and click [Expand Selected] to traverse deeper TigerGraph connections."
      };
    }

    insights.push(`${nodes.length} entities and ${edges.length} multi-hop relationships retrieved across ${hops} hop(s).`);
    if (devNodes.length > 0 && cardNodes.length > 1) {
      insights.push(`Shared device fingerprint connects ${cardNodes.length} customer cards in fraud network.`);
    }
    if (suspiciousCount > 0) {
      insights.push(`${suspiciousCount} entities flagged along the active attack path.`);
    }

    return {
      isSparse: false,
      text: insights.join(" ")
    };
  }, [currentGraph, hops]);

  const renderProps = (propsObj: any) => {
    if (!propsObj || typeof propsObj !== 'object') return null;
    return Object.entries(propsObj).map(([k, v]) => {
      if (k === "source" || v === null || v === undefined || strVal(v) === "" || strVal(v).toLowerCase() === "nan") return null;
      return (
        <div key={k} className="flex justify-between text-xs py-1.5 border-b border-slate-100 last:border-0 items-start">
          <span className="text-slate-500 font-mono text-[11px] shrink-0 mr-2">{k}</span>
          <span className="font-mono text-slate-800 text-right text-[11px] break-all font-medium" title={String(v)}>
            {String(v)}
          </span>
        </div>
      );
    });
  };

  function strVal(v: any): string {
    return typeof v === "object" ? JSON.stringify(v) : String(v);
  }

  return (
    <div 
      ref={graphContainerRef} 
      className={cn(
        "flex w-full overflow-hidden bg-slate-50 text-slate-900 transition-all",
        isFullscreen ? "fixed inset-0 z-50 h-screen w-screen" : "h-[calc(100vh-4rem)]"
      )}
    >
      {/* Sidebar: Case Selector (Light Theme) */}
      {!hideSidebar ? (
        <div className="w-80 border-r border-slate-200 bg-white flex flex-col shrink-0 z-20 shadow-sm relative transition-all">
          <div className="p-4 border-b border-slate-200 shrink-0">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-mono font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Network className="w-3.5 h-3.5 text-blue-600" />
                Investigation Cases
              </h2>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-mono px-2 py-0.5 bg-blue-50 text-blue-700 font-bold border border-blue-200 rounded-full">
                  {filteredCases.length}
                </span>
                <button
                  onClick={() => setHideSidebar(true)}
                  className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors"
                  title="Collapse Cases Panel"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search Case ID, card, customer..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {loadingCases ? (
              <div className="p-4 space-y-2 animate-pulse">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-12 bg-slate-100 rounded-lg w-full"></div>
                ))}
              </div>
            ) : filteredCases.length > 0 ? (
              filteredCases.map((c) => (
                <button
                  key={c.case_id}
                  onClick={() => setSelectedCase(c.case_id)}
                  className={cn(
                    "w-full text-left p-3 rounded-lg transition-all flex items-center justify-between group",
                    selectedCase === c.case_id 
                      ? "bg-blue-50 border border-blue-300 text-blue-900 shadow-sm" 
                      : "hover:bg-slate-50 text-slate-700 border border-transparent"
                  )}
                >
                  <div className="overflow-hidden mr-2">
                    <span className="font-mono text-xs font-bold block truncate">{c.case_id}</span>
                    <span className="text-[10px] font-mono text-slate-500 block truncate mt-0.5">
                      {c.pattern?.replace(/_/g, " ") || c.trigger_type?.replace(/_/g, " ") || "Risk Trigger"}
                    </span>
                  </div>
                  <span className={cn(
                    "text-[9px] font-mono uppercase font-bold tracking-wider px-2 py-0.5 rounded shrink-0",
                    c.final_risk_level === "HIGH" || c.final_risk_level === "CRITICAL" ? "bg-rose-100 text-rose-700 border border-rose-200" : 
                    "bg-slate-100 text-slate-600 border border-slate-200"
                  )}>
                    {c.final_risk_level || "HIGH"}
                  </span>
                </button>
              ))
            ) : (
              <div className="p-4 text-center text-xs text-slate-500 font-mono">No cases found.</div>
            )}
          </div>
        </div>
      ) : (
        <button
          onClick={() => setHideSidebar(false)}
          className="w-8 border-r border-slate-200 bg-white hover:bg-blue-50 flex flex-col items-center justify-center gap-2 text-slate-500 hover:text-blue-600 transition-colors z-20 shadow-sm"
          title="Expand Cases Panel"
        >
          <ChevronRight className="w-4 h-4" />
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider [writing-mode:vertical-lr] rotate-180">
            Cases ({filteredCases.length})
          </span>
        </button>
      )}

      {/* Main: Graph Display */}
      <div className="flex-1 bg-slate-50 flex flex-col overflow-hidden relative">
        {/* Dynamic Header Bar (Clean Light Theme) */}
        <div className="h-16 px-6 border-b border-slate-200 bg-white/95 backdrop-blur-md shadow-sm shrink-0 flex justify-between items-center z-10">
          <div>
            <div className="flex items-center gap-2.5">
              <Network className="w-5 h-5 text-blue-600" />
              <h1 className="text-base font-bold tracking-tight text-slate-900">
                TigerGraph Intelligence Explorer
              </h1>
              <span className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border",
                isTgConnected 
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-slate-100 text-slate-600 border-slate-200"
              )}>
                <span className={cn("w-1.5 h-1.5 rounded-full", isTgConnected ? "bg-emerald-500 animate-pulse" : "bg-slate-400")}></span>
                {isTgConnected ? "TIGERGRAPH LIVE" : "OFFLINE CACHE"}
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">
                <Server className="w-3 h-3 text-blue-600" />
                {accessMode === "MCP" ? "ACCESS: MCP" : "ACCESS: DIRECT TIGERGRAPH"}
              </span>
              {mcpCalls > 0 && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  <Zap className="w-3 h-3 text-indigo-600" />
                  {mcpCalls} MCP Calls
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5 font-mono">
              Live multi-hop graph traversal • Case: <span className="font-semibold text-slate-800">{selectedCase || "None"}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            {selectedCase && currentGraph && (
              <div className="font-mono text-xs px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 flex items-center gap-2 shadow-sm">
                <span className="font-bold text-blue-600">{nodeCount}</span> {nodeCount === 1 ? "Entity" : "Entities"}
                <span className="text-slate-300">•</span>
                <span className="font-bold text-blue-600">{edgeCount}</span> {edgeCount === 1 ? "Relationship" : "Relationships"}
                <span className="text-slate-300">•</span>
                <span className="font-bold text-amber-600">{hops}</span> {hops === 1 ? "Hop" : "Hops"}
              </div>
            )}
            
            {selectedCase && (
              <button
                onClick={() => loadCaseGraph(selectedCase, hops, true)}
                disabled={loadingGraph}
                className="p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200 bg-white shadow-sm"
                title="Refresh Live TigerGraph Subgraph"
              >
                <RefreshCw className={cn("w-4 h-4", loadingGraph && "animate-spin text-blue-600")} />
              </button>
            )}

            {/* Fullscreen Toggle Button */}
            <button
              onClick={toggleFullscreen}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all flex items-center gap-1.5 border shadow-sm",
                isFullscreen
                  ? "bg-rose-50 text-rose-700 border-rose-300 hover:bg-rose-100"
                  : "bg-white text-slate-700 hover:text-blue-600 hover:bg-slate-50 border-slate-200"
              )}
              title={isFullscreen ? "Exit Fullscreen (Esc)" : "Expand Graph to Fullscreen"}
            >
              {isFullscreen ? (
                <>
                  <Minimize2 className="w-3.5 h-3.5 text-rose-600" />
                  Exit Fullscreen
                </>
              ) : (
                <>
                  <Maximize2 className="w-3.5 h-3.5 text-blue-600" />
                  Full Screen
                </>
              )}
            </button>
          </div>
        </div>

        {/* Controls & Hop Depth Bar (Light Theme) */}
        <div className="px-6 py-2 border-b border-slate-200 bg-white flex items-center justify-between z-10 flex-wrap gap-2">
          {/* Hop Controls */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono uppercase font-bold text-slate-500 flex items-center gap-1 mr-1">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              Hop Depth:
            </span>
            {[1, 2, 3].map((h) => (
              <button
                key={h}
                onClick={() => handleHopChange(h)}
                className={cn(
                  "px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all flex items-center gap-1",
                  hops === h
                    ? "bg-blue-600 text-white shadow-sm"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200"
                )}
              >
                {h} {h === 1 ? "Hop" : "Hops"}
              </button>
            ))}

            <div className="h-4 w-px bg-slate-200 mx-1"></div>

            {/* Expand Selected Button */}
            <button
              onClick={() => handleExpandNeighbors(1)}
              disabled={!selectedNodeData || expanding}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all flex items-center gap-1.5 border shadow-sm",
                selectedNodeData
                  ? "bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100"
                  : "bg-slate-50 text-slate-400 border-slate-200 cursor-not-allowed"
              )}
              title={selectedNodeData ? `Query live TigerGraph neighbors for ${selectedNodeData.label}` : "Select a node to expand"}
            >
              <Sparkles className={cn("w-3.5 h-3.5 text-emerald-600", expanding && "animate-spin")} />
              {expanding ? "Expanding..." : "Expand Selected (+1 Hop)"}
            </button>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setFilterType("ALL");
                setActiveRelFilters(new Set());
              }}
              className="px-2.5 py-1 rounded text-[11px] font-mono font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-200 flex items-center gap-1 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset Filters
            </button>
          </div>
        </div>

        {/* Entity & Relationship Filters Bar (Light Theme) */}
        <div className="px-6 py-2 border-b border-slate-200 bg-slate-50/80 flex items-center justify-between z-10 overflow-x-auto gap-4">
          {/* Entity Filters */}
          <div className="flex items-center gap-1.5 shrink-0">
            <Filter className="w-3.5 h-3.5 text-slate-400 mr-1" />
            <span className="text-[10px] font-mono uppercase font-bold text-slate-500 mr-1">Entities:</span>
            {[
              { id: "ALL", label: "All" },
              { id: "CUSTOMERS", label: "Customers" },
              { id: "CARDS", label: "Cards" },
              { id: "TRANSACTIONS", label: "Transactions" },
              { id: "DEVICES", label: "Devices" },
              { id: "CASES", label: "Historical Cases" },
              { id: "CONNECTIONS", label: "Suspicious" }
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterType(f.id)}
                className={cn(
                  "px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-colors shadow-xs",
                  filterType === f.id 
                    ? "bg-blue-600 text-white" 
                    : "bg-white text-slate-600 hover:text-slate-900 border border-slate-200 hover:bg-slate-100"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Relationship Type Filters */}
          {availableRelTypes.length > 0 && (
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-[10px] font-mono uppercase font-bold text-slate-500 mr-1">Edges:</span>
              {availableRelTypes.map((rel) => {
                const isActive = activeRelFilters.size === 0 || activeRelFilters.has(rel);
                return (
                  <button
                    key={rel}
                    onClick={() => toggleRelFilter(rel)}
                    className={cn(
                      "px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase transition-colors border",
                      isActive
                        ? "bg-indigo-50 text-indigo-700 border-indigo-300 font-bold"
                        : "bg-slate-100 text-slate-400 border-slate-200 opacity-60"
                    )}
                  >
                    {rel}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Dynamic Graph Insight Bar (Light Theme) */}
        {graphInsight && (
          <div className={cn(
            "px-6 py-2 text-xs font-mono border-b flex items-center justify-between z-10",
            graphInsight.isSparse 
              ? "bg-amber-50 border-amber-200 text-amber-900"
              : "bg-blue-50/80 border-blue-200 text-blue-950"
          )}>
            <div className="flex items-center gap-2 truncate">
              {graphInsight.isSparse ? (
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              ) : (
                <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
              )}
              <span className="font-bold uppercase text-[10px] tracking-wider shrink-0 text-slate-600">GRAPH INSIGHT:</span>
              <span className="truncate font-medium">{graphInsight.text}</span>
            </div>

            {expansionMsg && (
              <div className={cn(
                "px-2.5 py-0.5 rounded text-[11px] font-mono border shrink-0 ml-4 font-semibold",
                expansionMsg.type === "success" ? "bg-emerald-100 border-emerald-300 text-emerald-800" :
                expansionMsg.type === "info" ? "bg-blue-100 border-blue-300 text-blue-800" :
                "bg-rose-100 border-rose-300 text-rose-800"
              )}>
                {expansionMsg.text}
              </div>
            )}
          </div>
        )}

        {/* Canvas Area (Light Theme) */}
        <div className="flex-1 relative w-full h-full bg-slate-50 overflow-hidden">
          {!selectedCase ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center max-w-md mx-auto z-20">
              <Network className="w-12 h-12 text-slate-300 mb-4" />
              <h2 className="text-base font-semibold mb-1 text-slate-800">No Investigation Selected</h2>
              <p className="text-xs text-slate-500 font-mono">Choose a case from the sidebar to visualize its entity relationships and multi-hop fraud network.</p>
            </div>
          ) : loadingGraph ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-white/80 backdrop-blur-xs">
              <div className="w-10 h-10 rounded-full border-3 border-blue-600 border-t-transparent animate-spin mb-4"></div>
              <p className="text-xs font-mono text-slate-800 font-bold">Traversing TigerGraph {hops}-Hop Subgraph...</p>
              <p className="text-[11px] font-mono text-slate-500 mt-1">Executing live installed GSQL queries against cloud database</p>
            </div>
          ) : (
            <ReactFlowProvider>
              <GraphCanvas 
                nodesData={currentGraph?.nodes || []}
                edgesData={currentGraph?.edges || []}
                suspiciousNodes={currentGraph?.suspicious_nodes || []}
                suspiciousEdges={currentGraph?.suspicious_edges || []}
                highlightedPaths={currentGraph?.highlighted_paths || []}
                filterType={filterType}
                relFilters={activeRelFilters}
                onNodeClick={setSelectedNodeData}
                onEdgeClick={setSelectedEdgeData}
              />
            </ReactFlowProvider>
          )}
        </div>

        {/* Details Panel Overlay & Multi-hop Expander (Light Theme) */}
        {(selectedNodeData || selectedEdgeData) && (
          <div className="absolute top-28 right-6 w-96 bg-white/95 backdrop-blur-md border border-slate-200 shadow-2xl rounded-2xl overflow-hidden z-30 flex flex-col max-h-[calc(100%-8.5rem)] animate-in fade-in slide-in-from-right-4 duration-200">
            <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/80">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-2 text-slate-800">
                <Info className="w-4 h-4 text-blue-600" />
                {selectedNodeData ? `${selectedNodeData.type} Inspector` : "Relationship Inspector"}
              </h3>
              <button 
                onClick={() => { setSelectedNodeData(null); setSelectedEdgeData(null); setExpansionMsg(null); }}
                className="text-slate-400 hover:text-slate-800 text-xs font-semibold px-2 py-1 rounded hover:bg-slate-200"
              >
                ✕
              </button>
            </div>
            
            <div className="p-4 overflow-y-auto flex-1 space-y-4">
              {selectedNodeData && (
                <>
                  <div>
                    <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-500 block mb-1">
                      Entity Identifier
                    </span>
                    <div className="text-sm font-mono font-bold text-slate-900 truncate">{selectedNodeData.label || selectedNodeData.id}</div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5 break-all">{selectedNodeData.id}</div>
                  </div>

                  {/* Real Multi-Hop Expander Button */}
                  <div className="bg-blue-50/60 border border-blue-200 p-3.5 rounded-xl space-y-2">
                    <div className="text-xs font-bold text-blue-900 flex items-center justify-between font-mono">
                      <span className="flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                        Live TigerGraph Expansion
                      </span>
                      <span className="text-[10px] font-semibold text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">GSQL</span>
                    </div>
                    <p className="text-[11px] text-slate-600 font-mono leading-relaxed">
                      Query connected transactions, hardware fingerprints, and customer cards directly from TigerGraph.
                    </p>
                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <button
                        onClick={() => handleExpandNeighbors(1)}
                        disabled={expanding}
                        className="py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold font-mono rounded-lg transition-all flex items-center justify-center gap-1 shadow-sm disabled:opacity-50"
                      >
                        {expanding ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ExternalLink className="w-3.5 h-3.5" />}
                        +1 Hop
                      </button>
                      <button
                        onClick={() => handleExpandNeighbors(2)}
                        disabled={expanding}
                        className="py-2 px-3 bg-white hover:bg-slate-100 text-blue-700 border border-blue-300 text-xs font-bold font-mono rounded-lg transition-all flex items-center justify-center gap-1 disabled:opacity-50 shadow-sm"
                      >
                        {expanding ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Layers className="w-3.5 h-3.5" />}
                        +2 Hops
                      </button>
                    </div>

                    {expansionMsg && (
                      <div className={cn(
                        "p-2 rounded text-[11px] font-mono border font-semibold",
                        expansionMsg.type === "success" ? "bg-emerald-50 border-emerald-300 text-emerald-800" :
                        expansionMsg.type === "info" ? "bg-blue-50 border-blue-300 text-blue-800" :
                        "bg-rose-50 border-rose-300 text-rose-800"
                      )}>
                        {expansionMsg.text}
                      </div>
                    )}
                  </div>
                  
                  {/* Entity Core Attributes */}
                  <div className="space-y-2 pt-1 border-t border-slate-200">
                    <div className="flex justify-between text-xs items-center font-mono">
                      <span className="text-slate-500">Vertex Type</span>
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-800 rounded text-[10px] font-bold border border-slate-200">{selectedNodeData.type}</span>
                    </div>
                    <div className="flex justify-between text-xs items-center font-mono">
                      <span className="text-slate-500">Classification</span>
                      <span className={cn(
                        "px-2 py-0.5 rounded text-[10px] font-bold border",
                        selectedNodeData.suspicious 
                          ? "bg-rose-100 text-rose-800 border-rose-300"
                          : "bg-emerald-100 text-emerald-800 border-emerald-300"
                      )}>
                        {selectedNodeData.status_badge || (selectedNodeData.suspicious ? "SUSPICIOUS" : "LEGITIMATE")}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs items-center font-mono">
                      <span className="text-slate-500">Database Source</span>
                      <span className="text-blue-700 text-[11px] font-semibold">TigerGraph Cloud</span>
                    </div>
                  </div>

                  {/* Risk / Context Alert */}
                  {selectedNodeData.suspicious && (
                    <div className="bg-rose-50 border border-rose-200 p-3 rounded-xl space-y-1">
                      <div className="text-[10px] font-mono font-bold text-rose-700 uppercase flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                        Fraud Investigation Signal
                      </div>
                      <p className="text-[11px] font-mono text-rose-900 leading-relaxed">
                        {selectedNodeData.type === "Transaction" 
                          ? "Trigger transaction flagged with anomalous velocity and elevated risk score."
                          : selectedNodeData.type === "Card"
                          ? "Card identity connected to multi-account device sharing ring or rapid burst sequence."
                          : selectedNodeData.type === "DeviceProfile"
                          ? "Hardware profile shared across distinct customer card identities."
                          : "Entity flagged as high-relevance attack node in graph traversal."}
                      </p>
                    </div>
                  )}
                  
                  {/* Detailed Graph Attributes */}
                  {selectedNodeData.properties && Object.keys(selectedNodeData.properties).length > 0 && (
                    <div className="space-y-2 border-t border-slate-200 pt-3">
                      <div className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-500 mb-1">
                        Vertex Attributes & Metadata
                      </div>
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 space-y-1">
                        {renderProps(selectedNodeData.properties)}
                      </div>
                    </div>
                  )}
                </>
              )}
              
              {selectedEdgeData && (
                <>
                  <div>
                    <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-500 block mb-1">
                      Relationship Type
                    </span>
                    <div className="text-sm font-mono font-bold text-slate-900 flex items-center gap-2">
                      <span className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-xs font-mono font-bold">
                        {selectedEdgeData.type || selectedEdgeData.label}
                      </span>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="p-3 bg-slate-50 rounded-xl space-y-2 border border-slate-200">
                      <div className="text-xs font-mono">
                        <span className="text-slate-500 block mb-0.5 text-[10px] uppercase font-bold">Source Vertex</span>
                        <span className="font-mono text-xs font-semibold break-all text-slate-800">{selectedEdgeData.source}</span>
                      </div>
                      <div className="flex items-center justify-center py-0.5">
                        <div className="px-2 py-0.5 bg-slate-200 text-slate-700 rounded text-[9px] font-mono font-bold">
                          ─── {selectedEdgeData.type} ───►
                        </div>
                      </div>
                      <div className="text-xs font-mono">
                        <span className="text-slate-500 block mb-0.5 text-[10px] uppercase font-bold">Target Vertex</span>
                        <span className="font-mono text-xs font-semibold break-all text-slate-800">{selectedEdgeData.target}</span>
                      </div>
                    </div>
                    
                    <div className="space-y-2 pt-1 border-t border-slate-200">
                      <div className="flex justify-between text-xs items-center font-mono">
                        <span className="text-slate-500">Relationship Classification</span>
                        {selectedEdgeData.suspicious ? (
                          <span className="px-2 py-0.5 bg-rose-100 text-rose-800 border border-rose-300 rounded text-[10px] font-bold">
                            Attack Link
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-slate-100 text-slate-700 border border-slate-200 rounded text-[10px]">
                            Schema Association
                          </span>
                        )}
                      </div>
                      <div className="flex justify-between text-xs items-center font-mono">
                        <span className="text-slate-500">Graph Schema Edge</span>
                        <span className="text-blue-700 text-[11px] font-mono font-semibold">{selectedEdgeData.type}</span>
                      </div>
                      <div className="flex justify-between text-xs items-center font-mono">
                        <span className="text-slate-500">Data Source</span>
                        <span className="text-slate-700 text-[11px]">TigerGraph Live</span>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
