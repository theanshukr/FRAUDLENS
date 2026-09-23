/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/no-unescaped-entities */
/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { getCases, getGraph, expandGraph, CaseSummary } from "@/lib/api";
import { Card, Badge, cn } from "@/components/ui";
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
  Share2, 
  Sparkles, 
  RefreshCw,
  Filter,
  CheckCircle2,
  AlertTriangle,
  FileText
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
  dagreGraph.setGraph({ rankdir: direction, nodesep: 110, ranksep: 130 });

  const nodeMap = new Set(nodes.map((n) => n.id));

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 240, height: 95 });
  });

  const validEdges = edges.filter((edge) => nodeMap.has(edge.source) && nodeMap.has(edge.target));

  validEdges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  try {
    dagre.layout(dagreGraph);
  } catch (err) {
    console.warn("Dagre layout calculation warning:", err);
  }

  const layoutedNodes = nodes.map((node, idx) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const x = nodeWithPosition ? nodeWithPosition.x - 240 / 2 : (idx % 3) * 270 + 50;
    const y = nodeWithPosition ? nodeWithPosition.y - 95 / 2 : Math.floor(idx / 3) * 150 + 50;

    return {
      ...node,
      targetPosition: direction === 'TB' ? Position.Top : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
      position: { x, y },
    };
  });

  return { nodes: layoutedNodes, edges: validEdges };
};

// --- Custom Entity Node ---
const EntityNode = ({ data, selected }: any) => {
  const Icon = data.icon || Network;
  const isFlaggedTxn = data.type === "Transaction" && data.suspicious;

  return (
    <div className={cn(
      "px-4 py-3 shadow-md rounded-xl border flex flex-col gap-2 min-w-[220px] transition-all cursor-pointer backdrop-blur-md",
      isFlaggedTxn
        ? "border-rose-500 bg-rose-950/30 text-rose-100 ring-2 ring-rose-500/50 shadow-rose-950/40"
        : data.suspicious 
        ? "border-amber-500/80 bg-amber-950/20 text-amber-100 ring-1 ring-amber-500/40 shadow-amber-950/20" 
        : "border-slate-800 bg-slate-900/90 text-slate-200 hover:border-sky-500/60 shadow-black/40",
      selected ? "ring-2 ring-sky-400 ring-offset-2 ring-offset-slate-950 scale-[1.03]" : ""
    )}>
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-sky-400/80 !border-0" />
      <div className="flex items-center gap-3">
        <div className={cn(
          "p-2.5 rounded-lg shrink-0", 
          isFlaggedTxn ? "bg-rose-500/20 text-rose-400" :
          data.suspicious ? "bg-amber-500/20 text-amber-400" : "bg-sky-500/15 text-sky-400"
        )}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-0.5 flex items-center justify-between">
            <span>{data.type}</span>
            {isFlaggedTxn ? (
              <span className="text-[9px] font-extrabold text-rose-300 bg-rose-500/20 px-1.5 py-0.5 rounded border border-rose-500/40">FLAGGED TXN</span>
            ) : data.suspicious ? (
              <span className="text-[9px] font-extrabold text-amber-300 bg-amber-500/20 px-1.5 py-0.5 rounded border border-amber-500/40">SUSPICIOUS</span>
            ) : (
              <span className="text-[9px] font-medium text-emerald-400 bg-emerald-500/10 px-1 rounded">VALID</span>
            )}
          </div>
          <div className={cn("text-xs font-mono font-bold truncate", isFlaggedTxn ? "text-rose-200" : data.suspicious ? "text-amber-200" : "text-slate-100")}>
            {data.label}
          </div>
          {data.properties?.amount && (
            <div className="text-[10px] font-mono text-slate-400 mt-0.5">
              Amt: <span className="font-semibold text-rose-300">{data.properties.amount}</span>
            </div>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-sky-400/80 !border-0" />
    </div>
  );
};

const nodeTypes = {
  entity: EntityNode,
};

// --- Graph Canvas Inner Component ---
const GraphCanvas = ({ 
  nodesData, 
  edgesData, 
  suspiciousNodes, 
  suspiciousEdges,
  filterType,
  onNodeClick,
  onEdgeClick
}: { 
  nodesData: any[], 
  edgesData: any[],
  suspiciousNodes: string[],
  suspiciousEdges: string[],
  filterType: string,
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

    // Apply filter
    const filteredNodesData = nodesData.filter((n: any) => {
      if (filterType === "ALL") return true;
      const t = (n.type || "").toLowerCase();
      if (filterType === "CUSTOMERS") return t.includes("customer") || t.includes("user");
      if (filterType === "CARDS") return t.includes("card");
      if (filterType === "TRANSACTIONS") return t.includes("transaction") || t.includes("txn");
      if (filterType === "DEVICES") return t.includes("device") || t.includes("profile");
      if (filterType === "CONNECTIONS") return n.suspicious || suspiciousNodes.includes(n.id);
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
          icon
        },
        position: { x: 0, y: 0 }
      };
    });
    
    // Strict edge deduplication on frontend to physically prevent duplicate parallel edges
    const edgePairMap = new Map<string, any>();
    (edgesData || []).forEach((e: any) => {
      if (!e.source || !e.target || e.source === e.target) return;
      if (!activeNodeIds.has(e.source) || !activeNodeIds.has(e.target)) return;
      const pairKey = [e.source, e.target].sort().join("---");
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
        id: `edge-${e.source}-${e.target}-${idx}`,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        data: { ...e },
        label: e.label || e.type,
        animated: isSuspicious,
        style: { 
          stroke: isSuspicious ? '#f43f5e' : '#475569',
          strokeWidth: isSuspicious ? 2.5 : 1.5,
          strokeDasharray: isSuspicious ? '5,5' : undefined,
        },
        labelStyle: { fill: isSuspicious ? '#fda4af' : '#94a3b8', fontWeight: 600, fontSize: 10, fontFamily: 'monospace' },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.9, rx: 4, ry: 4 },
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 4,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isSuspicious ? '#f43f5e' : '#475569',
        }
      };
    });

    const layouted = getLayoutedElements(mappedNodes, mappedEdges);
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    
    const timer = setTimeout(() => {
      try {
        fitView({ padding: 0.25, duration: 600 });
      } catch (e) {
        console.warn("fitView error", e);
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [nodesData, edgesData, suspiciousNodes, suspiciousEdges, filterType, setNodes, setEdges, fitView]);

  return (
    <div className="w-full h-full relative">
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
        <Background color="#334155" gap={24} size={1} />
        <Controls className="bg-slate-900 border border-slate-800 shadow-xl rounded-xl overflow-hidden text-slate-200 fill-slate-200" />
        
        {/* Graph Legend */}
        <Panel position="bottom-left" className="bg-slate-950/90 backdrop-blur-md border border-slate-800 p-3.5 rounded-xl shadow-xl mb-4 ml-4 z-10 space-y-2.5 min-w-[200px]">
          <h4 className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">GRAPH LEGEND</h4>
          <div className="space-y-1.5 text-[11px] font-mono">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full border border-sky-400/80 bg-sky-500/20"></div>
              <span className="text-slate-300">○ Legitimate Entity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full border border-amber-400 bg-amber-500/30"></div>
              <span className="text-amber-300 font-semibold">◉ Suspicious Entity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full border border-rose-500 bg-rose-500"></div>
              <span className="text-rose-400 font-bold">● Flagged Transaction</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-slate-500"></div>
              <span className="text-slate-400">━━ Normal Relationship</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 border-t border-dashed border-rose-500"></div>
              <span className="text-rose-400 font-medium">┅┅ Fraud / Attack Link</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

// --- Main Page Component ---
export default function GraphPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [expanding, setExpanding] = useState(false);
  const [expansionMsg, setExpansionMsg] = useState<{ type: "success" | "info" | "error"; text: string } | null>(null);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<string>("ALL");
  
  // Cache to store graph data per case
  const [graphCache, setGraphCache] = useState<Record<string, any>>({});
  
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

  const loadCaseGraph = useCallback((caseId: string, force = false) => {
    if (!caseId) return;
    setSelectedNodeData(null);
    setSelectedEdgeData(null);
    setExpansionMsg(null);

    if (!force && graphCache[caseId]) {
      return;
    }

    setLoadingGraph(true);
    getGraph(caseId)
      .then((res) => {
        setGraphCache((prev) => ({
          ...prev,
          [caseId]: res
        }));
      })
      .catch((err) => console.error("Failed to load graph", err))
      .finally(() => setLoadingGraph(false));
  }, [graphCache]);

  useEffect(() => {
    if (selectedCase) {
      loadCaseGraph(selectedCase);
    }
  }, [selectedCase]);

  // Real Multi-Hop TigerGraph Expansion (Zero Synthetic Data)
  const handleExpandNeighbors = async () => {
    if (!selectedCase || !selectedNodeData) return;
    setExpanding(true);
    setExpansionMsg(null);

    try {
      const res = await expandGraph(selectedCase, selectedNodeData.id, selectedNodeData.type || "Transaction");
      const newNodes = res.nodes || [];
      const newEdges = res.edges || [];

      if (newNodes.length === 0 && newEdges.length === 0) {
        setExpansionMsg({ type: "info", text: "No additional 1-hop neighbors found in TigerGraph." });
        return;
      }

      const current = graphCache[selectedCase] || { nodes: [], edges: [], suspicious_nodes: [], suspicious_edges: [] };
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

      const existingEdgeKeys = new Set(current.edges.map((e: any) => `${e.source}-${e.target}`));
      const mergedEdges = [...current.edges];
      let addedEdgesCount = 0;

      newEdges.forEach((edge: any) => {
        const k1 = `${edge.source}-${edge.target}`;
        const k2 = `${edge.target}-${edge.source}`;
        if (!existingEdgeKeys.has(k1) && !existingEdgeKeys.has(k2)) {
          mergedEdges.push(edge);
          existingEdgeKeys.add(k1);
          addedEdgesCount++;
        }
      });

      setGraphCache((prev) => ({
        ...prev,
        [selectedCase]: {
          ...current,
          nodes: mergedNodes,
          edges: mergedEdges,
          suspicious_nodes: Array.from(new Set([...(current.suspicious_nodes || []), ...(res.suspicious_nodes || [])])),
          suspicious_edges: Array.from(new Set([...(current.suspicious_edges || []), ...(res.suspicious_edges || [])])),
        }
      }));

      setExpansionMsg({
        type: "success",
        text: `+${addedNodesCount} ${addedNodesCount === 1 ? "entity" : "entities"}, +${addedEdgesCount} ${addedEdgesCount === 1 ? "relationship" : "relationships"} expanded from TigerGraph`
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
      c.pattern?.toLowerCase().includes(search.toLowerCase())
    );
  }, [cases, search]);

  const currentGraph = selectedCase ? graphCache[selectedCase] : null;

  // Derive factual Graph Insight summary purely from real nodes/edges
  const graphInsight = useMemo(() => {
    if (!currentGraph || !currentGraph.nodes || currentGraph.nodes.length === 0) return null;
    const nodes = currentGraph.nodes;
    const edges = currentGraph.edges || [];
    
    const cardNodes = nodes.filter((n: any) => (n.type || "").toLowerCase().includes("card"));
    const devNodes = nodes.filter((n: any) => (n.type || "").toLowerCase().includes("device") || (n.type || "").toLowerCase().includes("profile"));
    const txNodes = nodes.filter((n: any) => (n.type || "").toLowerCase().includes("transaction") || (n.type || "").toLowerCase().includes("txn"));
    const suspiciousCount = nodes.filter((n: any) => n.suspicious).length;

    const insights: string[] = [];
    if (nodes.length <= 2) {
      return {
        isSparse: true,
        text: "Limited graph neighborhood available for this case. Use 'Expand Neighbors' on any entity to query additional live TigerGraph relationships."
      };
    }

    insights.push(`${nodes.length} entities and ${edges.length} relationships in active graph neighborhood.`);
    if (devNodes.length > 0 && cardNodes.length > 1) {
      insights.push(`Shared device relationship linked across ${cardNodes.length} customer cards.`);
    }
    if (suspiciousCount > 0) {
      insights.push(`${suspiciousCount} entities flagged as suspicious along the multi-hop fraud path.`);
    }

    return {
      isSparse: false,
      text: insights.join(" ")
    };
  }, [currentGraph]);

  const renderProps = (propsObj: any) => {
    if (!propsObj || typeof propsObj !== 'object') return null;
    return Object.entries(propsObj).map(([k, v]) => (
      <div key={k} className="flex justify-between text-xs py-1 border-b border-slate-800 last:border-0">
        <span className="text-slate-400 font-mono text-[11px]">{k}</span>
        <span className="font-mono text-slate-200 truncate max-w-[140px] text-right text-[11px]" title={String(v)}>
          {String(v)}
        </span>
      </div>
    ));
  };

  const nodeCount = currentGraph?.nodes?.length || 0;
  const edgeCount = currentGraph?.edges?.length || 0;

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-slate-950 text-slate-100">
      {/* Sidebar: Case Selector */}
      <div className="w-80 border-r border-slate-800 bg-slate-900/60 flex flex-col shrink-0 z-20 shadow-lg relative">
        <div className="p-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              Investigation Cases
            </h2>
            <Badge variant="primary" className="text-[10px] font-mono px-1.5 py-0.5 bg-sky-500/20 text-sky-300 border border-sky-500/30">
              {filteredCases.length} Cases
            </Badge>
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search Case ID or pattern..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingCases ? (
            <div className="p-4 space-y-2 animate-pulse">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 bg-slate-800/50 rounded-lg w-full"></div>
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
                    ? "bg-sky-500/20 border border-sky-500/50 text-white shadow-sm" 
                    : "hover:bg-slate-800/60 text-slate-300 border border-transparent"
                )}
              >
                <div className="overflow-hidden mr-2">
                  <span className="font-mono text-xs font-bold block truncate">{c.case_id}</span>
                  <span className="text-[10px] font-mono text-slate-400 block truncate mt-0.5">
                    {c.pattern?.replace(/_/g, " ") || c.trigger_type?.replace(/_/g, " ") || "Risk Trigger"}
                  </span>
                </div>
                <span className={cn(
                  "text-[9px] font-mono uppercase font-bold tracking-wider px-2 py-0.5 rounded shrink-0",
                  c.final_risk_level === "HIGH" || c.final_risk_level === "CRITICAL" ? "bg-rose-500/20 text-rose-400 border border-rose-500/30" : 
                  "bg-slate-800 text-slate-400 border border-slate-700"
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

      {/* Main: Graph Display */}
      <div className="flex-1 bg-slate-950 flex flex-col overflow-hidden relative">
        {/* Header Bar */}
        <div className="h-16 px-6 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md shadow-sm shrink-0 flex justify-between items-center z-10">
          <div>
            <div className="flex items-center gap-2.5">
              <Network className="w-5 h-5 text-sky-400" />
              <h1 className="text-base font-bold tracking-tight text-white">
                TigerGraph Intelligence Explorer
              </h1>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                TIGERGRAPH LIVE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Live TigerGraph investigation graph • Multi-hop traversal and entity neighbor discovery
            </p>
          </div>
          <div className="flex items-center gap-3">
            {selectedCase && (
              <>
                {currentGraph && (
                  <div className="font-mono text-xs px-3 py-1 bg-slate-800 border border-slate-700 rounded-lg text-slate-300">
                    {nodeCount} {nodeCount === 1 ? "Node" : "Nodes"} • {edgeCount} {edgeCount === 1 ? "Edge" : "Edges"}
                  </div>
                )}
                <button
                  onClick={() => loadCaseGraph(selectedCase, true)}
                  disabled={loadingGraph}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors border border-slate-800"
                  title="Refresh Graph Data"
                >
                  <RefreshCw className={cn("w-4 h-4", loadingGraph && "animate-spin text-sky-400")} />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Graph Filters Bar */}
        <div className="px-6 py-2 border-b border-slate-800 bg-slate-900/40 flex items-center justify-between z-10">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400 mr-1" />
            <span className="text-[10px] font-mono uppercase font-bold text-slate-400 mr-2">Filters:</span>
            {["ALL", "CUSTOMERS", "CARDS", "TRANSACTIONS", "DEVICES", "CONNECTIONS"].map((f) => (
              <button
                key={f}
                onClick={() => setFilterType(f)}
                className={cn(
                  "px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase transition-colors",
                  filterType === f 
                    ? "bg-sky-500/20 text-sky-300 border border-sky-500/40" 
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                )}
              >
                {f}
              </button>
            ))}
          </div>

          <div className="text-[11px] font-mono text-slate-400">
            Click any entity node to inspect properties & expand neighbors
          </div>
        </div>

        {/* Graph Insight Summary Bar */}
        {graphInsight && (
          <div className={cn(
            "px-6 py-2 text-xs font-mono border-b flex items-center gap-2 z-10",
            graphInsight.isSparse 
              ? "bg-amber-950/20 border-amber-500/30 text-amber-300"
              : "bg-sky-950/20 border-sky-500/20 text-sky-200"
          )}>
            {graphInsight.isSparse ? (
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            ) : (
              <Sparkles className="w-4 h-4 text-sky-400 shrink-0" />
            )}
            <span className="font-bold uppercase text-[10px] tracking-wider shrink-0">GRAPH INSIGHT:</span>
            <span className="truncate">{graphInsight.text}</span>
          </div>
        )}

        {/* Canvas Area */}
        <div className="flex-1 relative w-full h-full bg-slate-950 overflow-hidden">
          {!selectedCase ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center max-w-md mx-auto z-20">
              <Network className="w-12 h-12 text-slate-600 mb-4" />
              <h2 className="text-base font-semibold mb-1 text-slate-300">No Investigation Selected</h2>
              <p className="text-xs text-slate-500 font-mono">Choose a case from the sidebar to visualize its entity relationships and fraud network.</p>
            </div>
          ) : loadingGraph ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-slate-950/70 backdrop-blur-sm">
              <div className="w-8 h-8 rounded-full border-2 border-sky-400 border-t-transparent animate-spin mb-4"></div>
              <p className="text-xs font-mono text-slate-300">Traversing TigerGraph entities...</p>
            </div>
          ) : (
            <ReactFlowProvider>
              <GraphCanvas 
                nodesData={currentGraph?.nodes || []}
                edgesData={currentGraph?.edges || []}
                suspiciousNodes={currentGraph?.suspicious_nodes || []}
                suspiciousEdges={currentGraph?.suspicious_edges || []}
                filterType={filterType}
                onNodeClick={setSelectedNodeData}
                onEdgeClick={setSelectedEdgeData}
              />
            </ReactFlowProvider>
          )}
        </div>

        {/* Details Panel Overlay & Multi-hop Expander */}
        {(selectedNodeData || selectedEdgeData) && (
          <div className="absolute top-28 right-6 w-84 bg-slate-900/95 backdrop-blur-md border border-slate-800 shadow-2xl rounded-2xl overflow-hidden z-30 flex flex-col max-h-[calc(100%-8rem)] animate-in fade-in slide-in-from-right-4 duration-200">
            <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/60">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-2 text-slate-200">
                <Info className="w-4 h-4 text-sky-400" />
                {selectedNodeData ? "Entity Inspector" : "Relationship Inspector"}
              </h3>
              <button 
                onClick={() => { setSelectedNodeData(null); setSelectedEdgeData(null); setExpansionMsg(null); }}
                className="text-slate-400 hover:text-white text-xs font-semibold px-2 py-1 rounded hover:bg-slate-800"
              >
                ✕
              </button>
            </div>
            
            <div className="p-4 overflow-y-auto flex-1 space-y-4">
              {selectedNodeData && (
                <>
                  <div>
                    <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-400 block mb-1">
                      Entity Identifier
                    </span>
                    <div className="text-sm font-mono font-bold text-white truncate">{selectedNodeData.label || selectedNodeData.id}</div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">{selectedNodeData.id}</div>
                  </div>

                  {/* Real Multi-Hop Expander Button */}
                  <div className="bg-sky-950/20 border border-sky-500/30 p-3 rounded-xl space-y-2">
                    <div className="text-xs font-bold text-sky-300 flex items-center gap-1.5 font-mono">
                      <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                      Live TigerGraph Expansion
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      Query 1-hop connected cards, hardware fingerprints, and transactions from TigerGraph Cloud.
                    </p>
                    <button
                      onClick={handleExpandNeighbors}
                      disabled={expanding}
                      className="w-full py-2 px-3 bg-sky-500 hover:bg-sky-400 text-slate-950 text-xs font-bold font-mono rounded-lg transition-all flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
                    >
                      {expanding ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Querying TigerGraph...
                        </>
                      ) : (
                        <>
                          <Share2 className="w-3.5 h-3.5" />
                          Expand Neighbors (1-Hop)
                        </>
                      )}
                    </button>

                    {expansionMsg && (
                      <div className={cn(
                        "p-2 rounded text-[11px] font-mono border",
                        expansionMsg.type === "success" ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300" :
                        expansionMsg.type === "info" ? "bg-sky-950/40 border-sky-500/40 text-sky-300" :
                        "bg-rose-950/40 border-rose-500/40 text-rose-300"
                      )}>
                        {expansionMsg.text}
                      </div>
                    )}
                  </div>
                  
                  <div className="space-y-2 pt-1 border-t border-slate-800">
                    <div className="flex justify-between text-xs items-center font-mono">
                      <span className="text-slate-400">Entity Class</span>
                      <span className="px-2 py-0.5 bg-slate-800 text-slate-200 rounded text-[10px] font-bold">{selectedNodeData.type}</span>
                    </div>
                    <div className="flex justify-between text-xs items-center font-mono">
                      <span className="text-slate-400">Risk Verdict</span>
                      {selectedNodeData.suspicious ? (
                        <span className="px-2 py-0.5 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded text-[10px] font-bold flex items-center gap-1">
                          <AlertCircle className="w-3 h-3"/> FLAGGED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-bold">
                          Legitimate
                        </span>
                      )}
                    </div>
                    <div className="flex justify-between text-xs items-center font-mono">
                      <span className="text-slate-400">Source</span>
                      <span className="text-sky-300 text-[11px]">TigerGraph Cloud</span>
                    </div>
                  </div>

                  {/* Why this matters */}
                  {selectedNodeData.suspicious && (
                    <div className="bg-rose-950/20 border border-rose-500/30 p-2.5 rounded-lg space-y-1">
                      <div className="text-[10px] font-mono font-bold text-rose-400 uppercase">Why this matters</div>
                      <p className="text-[11px] font-mono text-rose-200/90 leading-relaxed">
                        {selectedNodeData.type === "Transaction" 
                          ? "Trigger transaction flagged with high fraud probability and velocity anomaly."
                          : selectedNodeData.type === "Card"
                          ? "Card connected to multiple rapid transactions or shared device fingerprint."
                          : "Device profile shared across multiple distinct customer accounts."}
                      </p>
                    </div>
                  )}
                  
                  {selectedNodeData.properties && Object.keys(selectedNodeData.properties).length > 0 && (
                    <div className="space-y-2 border-t border-slate-800 pt-3">
                      <div className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-400 mb-1">
                        Graph Attributes
                      </div>
                      <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-2.5 space-y-1">
                        {renderProps(selectedNodeData.properties)}
                      </div>
                    </div>
                  )}
                </>
              )}
              
              {selectedEdgeData && (
                <>
                  <div>
                    <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-400 block mb-1">
                      Relationship Link
                    </span>
                    <div className="text-sm font-mono font-bold text-white">{selectedEdgeData.label || selectedEdgeData.type}</div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="p-3 bg-slate-950/60 rounded-xl space-y-2 border border-slate-800">
                      <div className="text-xs font-mono">
                        <span className="text-slate-400 block mb-0.5 text-[10px] uppercase font-bold">Source Entity</span>
                        <span className="font-mono text-xs font-semibold break-all text-slate-200">{selectedEdgeData.source}</span>
                      </div>
                      <div className="flex justify-center py-0.5">
                        <div className="w-0.5 h-3 bg-slate-700"></div>
                      </div>
                      <div className="text-xs font-mono">
                        <span className="text-slate-400 block mb-0.5 text-[10px] uppercase font-bold">Target Entity</span>
                        <span className="font-mono text-xs font-semibold break-all text-slate-200">{selectedEdgeData.target}</span>
                      </div>
                    </div>
                    
                    <div className="space-y-2 pt-1 border-t border-slate-800">
                      <div className="flex justify-between text-xs items-center font-mono">
                        <span className="text-slate-400">Fraud Relevance</span>
                        {selectedEdgeData.suspicious ? (
                          <span className="px-2 py-0.5 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded text-[10px] font-bold">
                            Attack Link
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[10px]">
                            Normal Association
                          </span>
                        )}
                      </div>
                      <div className="flex justify-between text-xs items-center font-mono">
                        <span className="text-slate-400">Provenance</span>
                        <span className="text-sky-300 text-[11px]">TigerGraph Graph Query</span>
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
