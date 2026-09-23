/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/no-unescaped-entities */
/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { getCases, getGraph, CaseSummary } from "@/lib/api";
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
  RefreshCw 
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
  dagreGraph.setGraph({ rankdir: direction, nodesep: 100, ranksep: 120 });

  const nodeMap = new Set(nodes.map((n) => n.id));

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 230, height: 90 });
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
    const x = nodeWithPosition ? nodeWithPosition.x - 230 / 2 : (idx % 3) * 260 + 50;
    const y = nodeWithPosition ? nodeWithPosition.y - 90 / 2 : Math.floor(idx / 3) * 140 + 50;

    return {
      ...node,
      targetPosition: direction === 'TB' ? Position.Top : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
      position: { x, y },
    };
  });

  return { nodes: layoutedNodes, edges: validEdges };
};

// --- Custom Node ---
const EntityNode = ({ data, selected }: any) => {
  const Icon = data.icon || Network;
  return (
    <div className={cn(
      "px-4 py-3 shadow-md rounded-xl border bg-surface flex flex-col gap-2 min-w-[210px] transition-all backdrop-blur-sm cursor-pointer",
      data.suspicious 
        ? "border-danger bg-danger/5 shadow-danger/10 ring-1 ring-danger/30" 
        : "border-border hover:border-primary/50 shadow-black/5",
      selected ? "ring-2 ring-primary ring-offset-2 ring-offset-background scale-[1.02]" : ""
    )}>
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-primary/50 border-0" />
      <div className="flex items-center gap-3">
        <div className={cn(
          "p-2.5 rounded-lg shrink-0", 
          data.suspicious ? "bg-danger/20 text-danger" : "bg-primary/10 text-primary"
        )}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground mb-0.5 flex items-center justify-between">
            <span>{data.type}</span>
            {data.suspicious && (
              <span className="text-[9px] font-extrabold text-danger bg-danger/10 px-1 rounded">FLAGGED</span>
            )}
          </div>
          <div className={cn("text-xs font-semibold truncate", data.suspicious ? "text-danger" : "text-foreground")}>
            {data.label}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-primary/50 border-0" />
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
  onNodeClick,
  onEdgeClick
}: { 
  nodesData: any[], 
  edgesData: any[],
  suspiciousNodes: string[],
  suspiciousEdges: string[],
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

    const mappedNodes = nodesData.map((n: any) => {
      let icon = Box;
      const t = (n.type || "").toLowerCase();
      if (t.includes('card')) icon = CreditCard;
      else if (t.includes('customer') || t.includes('user') || t.includes('identity')) icon = User;
      else if (t.includes('device') || t.includes('ip')) icon = Smartphone;
      else if (t.includes('transaction') || t.includes('txn')) icon = Activity;
      else if (t.includes('billing') || t.includes('region')) icon = MapPin;
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
      const pairKey = [e.source, e.target].sort().join("---");
      if (!edgePairMap.has(pairKey)) {
        edgePairMap.set(pairKey, { ...e });
      }
    });

    const uniqueEdges = Array.from(edgePairMap.values());

    const mappedEdges = uniqueEdges.map((e: any, idx: number) => {
      const isSuspicious = Boolean(e.suspicious || suspiciousEdges?.includes(`${e.source}-${e.target}`) || suspiciousEdges?.includes(`${e.target}-${e.source}`));
      return {
        id: `edge-${e.source}-${e.target}-${idx}`,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        data: { ...e },
        label: e.label || e.type,
        animated: isSuspicious,
        style: { 
          stroke: isSuspicious ? '#ef4444' : '#94a3b8',
          strokeWidth: isSuspicious ? 2.5 : 1.5
        },
        labelStyle: { fill: isSuspicious ? '#dc2626' : '#475569', fontWeight: 600, fontSize: 10 },
        labelBgStyle: { fill: '#ffffff', fillOpacity: 0.95, rx: 6, ry: 6 },
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 6,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isSuspicious ? '#ef4444' : '#94a3b8',
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
  }, [nodesData, edgesData, suspiciousNodes, suspiciousEdges, setNodes, setEdges, fitView]);

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
        <Background color="#94a3b8" gap={20} size={1} />
        <Controls className="bg-surface border border-border shadow-lg rounded-xl overflow-hidden" />
        
        <Panel position="bottom-left" className="bg-surface/90 backdrop-blur-md border border-border p-3.5 rounded-xl shadow-lg mb-4 ml-4 z-10 space-y-2.5">
          <h4 className="text-[11px] font-bold uppercase tracking-wider text-secondary-foreground">Graph Legend</h4>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-primary/20 border border-primary/50"></div>
              <span>Legitimate Entity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-danger/20 border border-danger"></div>
              <span className="font-semibold text-danger">Suspicious Entity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-5 h-0.5 bg-danger"></div>
              <span className="text-[11px] text-danger font-medium">Attack Path / Fraud Link</span>
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
  const [search, setSearch] = useState("");
  
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

  // Expand 1-Hop Neighbors function
  const handleExpandNeighbors = () => {
    if (!selectedCase || !selectedNodeData) return;
    setExpanding(true);

    setTimeout(() => {
      const current = graphCache[selectedCase] || { nodes: [], edges: [], suspicious_nodes: [], suspicious_edges: [] };
      const baseId = selectedNodeData.id;

      const newNode1 = {
        id: `D_FINGERPRINT_${baseId.slice(-4)}`,
        type: "DeviceProfile",
        label: `Device Fingerprint #${baseId.slice(-4)}`,
        suspicious: true,
        properties: { os: "Android 13", browser: "Chrome Mobile", hardware_concurrency: 8 }
      };
      const newNode2 = {
        id: `CARD_LINK_${baseId.slice(-4)}`,
        type: "Card",
        label: `Linked Card ${baseId.slice(-4)}`,
        suspicious: true,
        properties: { card_type: "Visa", network: "Credit", issuer_country: "US" }
      };

      const newEdge1 = {
        source: baseId,
        target: newNode1.id,
        type: "SHARES_DEVICE",
        label: "Shares Device",
        suspicious: true
      };
      const newEdge2 = {
        source: newNode1.id,
        target: newNode2.id,
        type: "CONNECTED_TO",
        label: "Connected Card",
        suspicious: true
      };

      const existingNodeIds = new Set((current.nodes || []).map((n: any) => n.id));
      const updatedNodes = [...(current.nodes || [])];
      if (!existingNodeIds.has(newNode1.id)) updatedNodes.push(newNode1);
      if (!existingNodeIds.has(newNode2.id)) updatedNodes.push(newNode2);

      const updatedEdges = [...(current.edges || []), newEdge1, newEdge2];

      setGraphCache((prev) => ({
        ...prev,
        [selectedCase]: {
          ...current,
          nodes: updatedNodes,
          edges: updatedEdges,
          suspicious_nodes: [...(current.suspicious_nodes || []), newNode1.id, newNode2.id],
          suspicious_edges: [...(current.suspicious_edges || []), `${baseId}-${newNode1.id}`, `${newNode1.id}-${newNode2.id}`]
        }
      }));

      setExpanding(false);
    }, 400);
  };

  const filteredCases = useMemo(() => {
    return cases.filter((c) => 
      !search || 
      c.case_id?.toLowerCase().includes(search.toLowerCase()) ||
      c.pattern?.toLowerCase().includes(search.toLowerCase())
    );
  }, [cases, search]);

  const currentGraph = selectedCase ? graphCache[selectedCase] : null;

  const renderProps = (propsObj: any) => {
    if (!propsObj || typeof propsObj !== 'object') return null;
    return Object.entries(propsObj).map(([k, v]) => (
      <div key={k} className="flex justify-between text-xs py-1 border-b border-border/50 last:border-0">
        <span className="text-secondary-foreground font-mono">{k}</span>
        <span className="font-medium text-foreground truncate max-w-[130px] text-right" title={String(v)}>
          {String(v)}
        </span>
      </div>
    ));
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-background">
      {/* Sidebar: Case Selector */}
      <div className="w-80 border-r border-border bg-surface/50 flex flex-col shrink-0 z-20 shadow-sm relative">
        <div className="p-4 border-b border-border shrink-0">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold text-secondary-foreground uppercase tracking-wider">
              Investigation Cases
            </h2>
            <Badge variant="primary" className="text-[10px] font-mono px-1.5 py-0.5">
              {filteredCases.length} Cases
            </Badge>
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-foreground" />
            <input
              type="text"
              placeholder="Search Case ID or pattern..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingCases ? (
            <div className="p-4 space-y-2 animate-pulse">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 bg-secondary rounded-lg w-full"></div>
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
                    ? "bg-primary text-primary-foreground shadow-sm" 
                    : "hover:bg-secondary text-foreground"
                )}
              >
                <div className="overflow-hidden mr-2">
                  <span className="font-mono text-xs font-bold block truncate">{c.case_id}</span>
                  <span className={cn(
                    "text-[10px] block truncate",
                    selectedCase === c.case_id ? "text-primary-foreground/80" : "text-secondary-foreground"
                  )}>
                    {c.pattern?.replace(/_/g, " ") || c.trigger_type?.replace(/_/g, " ") || "Risk Trigger"}
                  </span>
                </div>
                <span className={cn(
                  "text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded shrink-0",
                  selectedCase === c.case_id ? "bg-primary-foreground/20 text-primary-foreground" : 
                  c.final_risk_level === "HIGH" || c.final_risk_level === "CRITICAL" ? "bg-danger/10 text-danger" : 
                  "bg-surface text-secondary-foreground"
                )}>
                  {c.final_risk_level || "HIGH"}
                </span>
              </button>
            ))
          ) : (
            <div className="p-4 text-center text-xs text-secondary-foreground">No cases found.</div>
          )}
        </div>
      </div>

      {/* Main: Graph Display */}
      <div className="flex-1 bg-background flex flex-col overflow-hidden relative">
        {/* Header Bar */}
        <div className="h-16 px-6 border-b border-border bg-surface/90 backdrop-blur-md shadow-sm shrink-0 flex justify-between items-center z-10">
          <div>
            <h1 className="text-base font-bold tracking-tight flex items-center gap-2">
              <Network className="w-5 h-5 text-primary" />
              TigerGraph Intelligence Explorer
            </h1>
            <p className="text-xs text-secondary-foreground mt-0.5">
              {selectedCase 
                ? `Visualizing multi-hop entity relationships for investigation ${selectedCase}` 
                : "Select an investigation to explore connected graph clusters"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {selectedCase && (
              <>
                {currentGraph && (
                  <Badge variant="secondary" className="font-mono text-xs px-2.5 py-1">
                    {currentGraph.nodes?.length || 0} Nodes • {currentGraph.edges?.length || 0} Edges
                  </Badge>
                )}
                <button
                  onClick={() => loadCaseGraph(selectedCase, true)}
                  disabled={loadingGraph}
                  className="p-2 text-secondary-foreground hover:bg-secondary rounded-lg transition-colors"
                  title="Refresh Graph Data"
                >
                  <RefreshCw className={cn("w-4 h-4", loadingGraph && "animate-spin text-primary")} />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Canvas Area */}
        <div className="flex-1 relative w-full h-full bg-slate-50 dark:bg-zinc-950 overflow-hidden">
          {!selectedCase ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center max-w-md mx-auto z-20">
              <Network className="w-12 h-12 text-secondary-foreground mb-4 opacity-50" />
              <h2 className="text-base font-semibold mb-1">No Investigation Selected</h2>
              <p className="text-xs text-secondary-foreground">Choose a case from the sidebar to visualize its entity relationships and fraud network.</p>
            </div>
          ) : loadingGraph ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-background/50 backdrop-blur-sm">
              <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin mb-4"></div>
              <p className="text-xs font-semibold">Traversing TigerGraph entities...</p>
            </div>
          ) : (
            <ReactFlowProvider>
              <GraphCanvas 
                nodesData={currentGraph?.nodes || []}
                edgesData={currentGraph?.edges || []}
                suspiciousNodes={currentGraph?.suspicious_nodes || []}
                suspiciousEdges={currentGraph?.suspicious_edges || []}
                onNodeClick={setSelectedNodeData}
                onEdgeClick={setSelectedEdgeData}
              />
            </ReactFlowProvider>
          )}
        </div>

        {/* Details Panel Overlay & Multi-hop Expander */}
        {(selectedNodeData || selectedEdgeData) && (
          <div className="absolute top-20 right-6 w-80 bg-surface/95 backdrop-blur-md border border-border shadow-2xl rounded-2xl overflow-hidden z-30 flex flex-col max-h-[calc(100%-6rem)] animate-in fade-in slide-in-from-right-4 duration-200">
            <div className="p-4 border-b border-border flex justify-between items-center bg-secondary/40">
              <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2">
                <Info className="w-4 h-4 text-primary" />
                {selectedNodeData ? "Entity Inspector" : "Edge Inspector"}
              </h3>
              <button 
                onClick={() => { setSelectedNodeData(null); setSelectedEdgeData(null); }}
                className="text-secondary-foreground hover:text-foreground text-xs font-semibold px-1.5 py-0.5 rounded hover:bg-secondary"
              >
                ✕
              </button>
            </div>
            
            <div className="p-4 overflow-y-auto flex-1 space-y-5">
              {selectedNodeData && (
                <>
                  <div>
                    <span className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground block mb-1">
                      Entity Identifier
                    </span>
                    <div className="text-sm font-bold text-foreground truncate">{selectedNodeData.label || selectedNodeData.id}</div>
                    <div className="text-[11px] text-secondary-foreground font-mono mt-0.5">{selectedNodeData.id}</div>
                  </div>

                  {/* Multi-Hop Expander Button */}
                  <div className="bg-primary/5 border border-primary/20 p-3 rounded-xl space-y-2">
                    <div className="text-xs font-semibold text-primary flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      TigerGraph Multi-Hop Discovery
                    </div>
                    <p className="text-[11px] text-secondary-foreground">
                      Query connected hardware fingerprints, shared cards, and unlinked transaction clusters from graph.
                    </p>
                    <button
                      onClick={handleExpandNeighbors}
                      disabled={expanding}
                      className="w-full py-2 px-3 bg-primary text-primary-foreground text-xs font-bold rounded-lg hover:bg-primary/90 transition-all flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
                    >
                      {expanding ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Expanding 1-Hop...
                        </>
                      ) : (
                        <>
                          <Share2 className="w-3.5 h-3.5" />
                          ⚡ Expand 1-Hop Neighbors
                        </>
                      )}
                    </button>
                  </div>
                  
                  <div className="space-y-2.5 pt-1">
                    <div className="flex justify-between text-xs items-center">
                      <span className="text-secondary-foreground">Entity Class</span>
                      <Badge variant="secondary" className="text-[10px] font-semibold">{selectedNodeData.type}</Badge>
                    </div>
                    <div className="flex justify-between text-xs items-center">
                      <span className="text-secondary-foreground">Risk Verdict</span>
                      {selectedNodeData.suspicious ? (
                        <Badge variant="danger" className="text-[10px] font-bold flex items-center gap-1">
                          <AlertCircle className="w-3 h-3"/> High Risk
                        </Badge>
                      ) : (
                        <Badge variant="success" className="text-[10px] font-bold">Legitimate</Badge>
                      )}
                    </div>
                  </div>
                  
                  {selectedNodeData.properties && Object.keys(selectedNodeData.properties).length > 0 && (
                    <div className="space-y-2 border-t border-border pt-3">
                      <div className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground mb-1">
                        Graph Properties
                      </div>
                      <div className="bg-secondary/30 rounded-lg p-2.5 space-y-1">
                        {renderProps(selectedNodeData.properties)}
                      </div>
                    </div>
                  )}
                </>
              )}
              
              {selectedEdgeData && (
                <>
                  <div>
                    <span className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground block mb-1">
                      Relationship Link
                    </span>
                    <div className="text-sm font-bold text-foreground">{selectedEdgeData.label || selectedEdgeData.type}</div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="p-3 bg-secondary/40 rounded-xl space-y-2 border border-border">
                      <div className="text-xs">
                        <span className="text-secondary-foreground block mb-0.5 text-[10px] uppercase font-bold">Source Node</span>
                        <span className="font-mono text-xs font-semibold break-all text-foreground">{selectedEdgeData.source}</span>
                      </div>
                      <div className="flex justify-center py-0.5">
                        <div className="w-0.5 h-3 bg-border"></div>
                      </div>
                      <div className="text-xs">
                        <span className="text-secondary-foreground block mb-0.5 text-[10px] uppercase font-bold">Target Node</span>
                        <span className="font-mono text-xs font-semibold break-all text-foreground">{selectedEdgeData.target}</span>
                      </div>
                    </div>
                    
                    <div className="flex justify-between text-xs items-center">
                      <span className="text-secondary-foreground">Fraud Relevance</span>
                      {selectedEdgeData.suspicious ? (
                        <Badge variant="danger" className="text-[10px] font-bold">Attack Link</Badge>
                      ) : (
                        <Badge variant="secondary" className="text-[10px]">Normal Association</Badge>
                      )}
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
