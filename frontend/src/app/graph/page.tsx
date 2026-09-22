/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { getCases, getGraph, CaseSummary } from "@/lib/api";
import { Card, Badge, cn } from "@/components/ui";
import { Search, Network, Maximize, ZoomIn, ZoomOut, AlertCircle, Smartphone, Activity, User, CreditCard, Box, Info } from "lucide-react";
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap, 
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
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 220, height: 80 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: 'top',
      sourcePosition: 'bottom',
      position: {
        x: nodeWithPosition.x - 220 / 2,
        y: nodeWithPosition.y - 80 / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

// --- Custom Nodes ---

const EntityNode = ({ data, type, selected }: any) => {
  const Icon = data.icon || Network;
  return (
    <div className={cn(
      "px-4 py-3 shadow-sm rounded-lg border bg-surface flex flex-col gap-2 min-w-[200px] transition-all",
      data.suspicious ? "border-danger bg-danger/5" : "border-border",
      selected ? "ring-2 ring-primary ring-offset-2 ring-offset-background" : "hover:border-primary/50"
    )}>
      <div className="flex items-center gap-3">
        <div className={cn(
          "p-2 rounded-md", 
          data.suspicious ? "bg-danger/20 text-danger" : "bg-primary/10 text-primary"
        )}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground mb-0.5">{data.type}</div>
          <div className={cn("text-sm font-semibold truncate", data.suspicious ? "text-danger" : "text-foreground")}>{data.label}</div>
        </div>
      </div>
      
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  );
};

const nodeTypes = {
  entity: EntityNode,
};

// --- Graph Canvas Inner Component ---

const GraphCanvas = ({ 
  selectedCase, 
  nodesData, 
  edgesData, 
  suspiciousNodes, 
  suspiciousEdges,
  onNodeClick,
  onEdgeClick
}: { 
  selectedCase: string, 
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

      return {
        id: n.id,
        type: 'entity',
        data: { 
          ...n,
          label: n.label || n.id, 
          type: n.type, 
          suspicious: n.suspicious || suspiciousNodes?.includes(n.id),
          icon
        },
        position: { x: 0, y: 0 } // Replaced by dagre
      };
    });
    
    const mappedEdges = edgesData.map((e: any) => {
      const isSuspicious = e.suspicious || suspiciousEdges?.includes(`${e.source}-${e.target}`);
      return {
        id: `${e.source}-${e.target}-${e.type}`,
        source: e.source,
        target: e.target,
        data: { ...e },
        label: e.label || e.type,
        animated: isSuspicious,
        style: { 
          stroke: isSuspicious ? '#ef4444' : '#64748b',
          strokeWidth: isSuspicious ? 3 : 2
        },
        labelStyle: { fill: '#64748b', fontWeight: 600, fontSize: 11 },
        labelBgStyle: { fill: '#ffffff', fillOpacity: 0.8 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isSuspicious ? '#ef4444' : '#64748b',
        }
      };
    });

    const layouted = getLayoutedElements(mappedNodes, mappedEdges);
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    
    // Fit view after a tick to let React Flow render
    setTimeout(() => {
      fitView({ padding: 0.2, duration: 800 });
    }, 100);
  }, [nodesData, edgesData, suspiciousNodes, suspiciousEdges, setNodes, setEdges, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={(_, node) => onNodeClick(node.data)}
      onEdgeClick={(_, edge) => onEdgeClick(edge.data)}
      onPaneClick={() => { onNodeClick(null); onEdgeClick(null); }}
      nodeTypes={nodeTypes}
      minZoom={0.2}
      maxZoom={4}
      className="w-full h-full"
    >
      <Background color="#ccc" gap={16} />
      <Controls className="bg-surface border border-border shadow-md rounded-md" />
      
      <Panel position="bottom-left" className="bg-surface border border-border p-3 rounded-lg shadow-md mb-4 ml-4 z-10">
        <h4 className="text-xs font-semibold uppercase tracking-wider mb-2 text-secondary-foreground">Legend</h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-primary/10 border border-border"></div>
            <span className="text-xs">Normal Entity</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-danger/10 border border-danger"></div>
            <span className="text-xs">Suspicious Entity</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-danger"></div>
            <span className="text-xs">High Risk Path</span>
          </div>
        </div>
      </Panel>
    </ReactFlow>
  );
};

// --- Main Page Component ---

export default function GraphPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [search, setSearch] = useState("");
  
  // Cache to prevent duplicate fetches
  const [graphCache, setGraphCache] = useState<Record<string, any>>({});
  
  // Selection state
  const [selectedNodeData, setSelectedNodeData] = useState<any | null>(null);
  const [selectedEdgeData, setSelectedEdgeData] = useState<any | null>(null);

  useEffect(() => {
    getCases()
      .then(res => setCases(res.cases || []))
      .catch(err => console.error(err))
      .finally(() => setLoadingCases(false));
  }, []);

  useEffect(() => {
    if (!selectedCase) return;
    
    // Clear selections when switching case
    setSelectedNodeData(null);
    setSelectedEdgeData(null);
    
    // Use cached if available
    if (graphCache[selectedCase]) {
      return;
    }
    
    setLoadingGraph(true);
    getGraph(selectedCase)
      .then(res => {
        setGraphCache(prev => ({
          ...prev,
          [selectedCase]: res
        }));
      })
      .catch(err => console.error("Failed to load graph", err))
      .finally(() => setLoadingGraph(false));
  }, [selectedCase, graphCache]);

  const filteredCases = cases.filter(c => 
    !search || c.case_id?.toLowerCase().includes(search.toLowerCase())
  );

  const currentGraph = selectedCase ? graphCache[selectedCase] : null;

  // Render properties safely
  const renderProps = (propsObj: any) => {
    if (!propsObj || typeof propsObj !== 'object') return null;
    return Object.entries(propsObj).map(([k, v]) => (
      <div key={k} className="flex justify-between text-xs">
        <span className="text-secondary-foreground">{k}</span>
        <span className="font-medium text-foreground truncate max-w-[120px] text-right" title={String(v)}>
          {String(v)}
        </span>
      </div>
    ));
  };

  return (
    <div className="flex h-full w-full mx-auto">
      {/* Sidebar: Case Selector */}
      <div className="w-80 border-r border-border bg-surface/50 flex flex-col shrink-0 z-20 shadow-sm relative">
        <div className="p-4 border-b border-border">
          <h2 className="text-xs font-semibold text-secondary-foreground uppercase tracking-wider mb-4">Select Investigation</h2>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-foreground" />
            <input
              type="text"
              placeholder="Search Case ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingCases ? (
            <div className="p-4 space-y-2 animate-pulse">
              {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-12 bg-secondary rounded w-full"></div>)}
            </div>
          ) : filteredCases.length > 0 ? (
            filteredCases.map(c => (
              <button
                key={c.case_id}
                onClick={() => setSelectedCase(c.case_id)}
                className={cn(
                  "w-full text-left p-3 rounded-md transition-colors flex items-center justify-between group",
                  selectedCase === c.case_id 
                    ? "bg-primary text-primary-foreground shadow-sm" 
                    : "hover:bg-secondary text-foreground"
                )}
              >
                <span className="font-mono text-sm font-medium">{c.case_id}</span>
                <span className={cn(
                  "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded",
                  selectedCase === c.case_id ? "bg-primary-foreground/20 text-primary-foreground" : 
                  c.final_risk_level === "HIGH" || c.final_risk_level === "CRITICAL" ? "bg-danger/10 text-danger" : 
                  "bg-surface text-secondary-foreground"
                )}>
                  {c.final_risk_level || "UNKNOWN"}
                </span>
              </button>
            ))
          ) : (
            <div className="p-4 text-center text-sm text-secondary-foreground">No cases found.</div>
          )}
        </div>
      </div>

      {/* Main: Graph Display */}
      <div className="flex-1 bg-background flex flex-col overflow-hidden relative">
        <div className="absolute top-0 left-0 right-0 z-10 px-6 py-4 border-b border-border bg-surface/80 backdrop-blur-sm shadow-sm pointer-events-auto flex justify-between items-center">
          <div>
            <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
              <Network className="w-5 h-5 text-primary" />
              Knowledge Graph
            </h1>
            <p className="text-sm text-secondary-foreground mt-0.5">
              {selectedCase 
                ? `Entity relationships for ${selectedCase}` 
                : "Select an investigation to visualize entities"}
            </p>
          </div>
        </div>

        <div className="flex-1 relative w-full h-full bg-slate-50 dark:bg-zinc-950 pt-16">
          {!selectedCase ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center max-w-md mx-auto z-20">
              <Network className="w-12 h-12 text-secondary-foreground mb-4" />
              <h2 className="text-lg font-medium mb-2">No Investigation Selected</h2>
              <p className="text-sm text-secondary-foreground">Choose a case from the sidebar to visualize its entity relationships and fraud network.</p>
            </div>
          ) : loadingGraph ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-background/50 backdrop-blur-sm">
              <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin mb-4"></div>
              <p className="text-sm font-medium">Building graph...</p>
            </div>
          ) : currentGraph && (!currentGraph.nodes || currentGraph.nodes.length <= 1) && (!currentGraph.edges || currentGraph.edges.length === 0) ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center max-w-md mx-auto z-20 px-4">
              <div className="w-16 h-16 rounded-full bg-secondary/50 flex items-center justify-center mb-6">
                <AlertCircle className="w-8 h-8 text-secondary-foreground" />
              </div>
              <h2 className="text-xl font-medium mb-3">No graph relationships available for this investigation.</h2>
              <p className="text-sm text-secondary-foreground leading-relaxed">
                Graph data may become available as additional evidence is collected or as new relationships are detected by the AI agent.
              </p>
            </div>
          ) : (
            <ReactFlowProvider>
              <GraphCanvas 
                selectedCase={selectedCase}
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

        {/* Details Panel Overlay */}
        {(selectedNodeData || selectedEdgeData) && (
          <div className="absolute top-20 right-6 w-80 bg-surface border border-border shadow-xl rounded-xl overflow-hidden z-30 flex flex-col max-h-[calc(100%-100px)]">
            <div className="p-4 border-b border-border flex justify-between items-center bg-secondary/30">
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Info className="w-4 h-4 text-primary" />
                {selectedNodeData ? "Entity Details" : "Relationship Details"}
              </h3>
              <button 
                onClick={() => { setSelectedNodeData(null); setSelectedEdgeData(null); }}
                className="text-secondary-foreground hover:text-foreground text-xs"
              >
                Close
              </button>
            </div>
            
            <div className="p-4 overflow-y-auto flex-1 space-y-6">
              {selectedNodeData && (
                <>
                  <div>
                    <div className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground mb-1">Entity</div>
                    <div className="text-sm font-semibold mb-1">{selectedNodeData.label || selectedNodeData.id}</div>
                    <div className="text-xs text-secondary-foreground font-mono">{selectedNodeData.id}</div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between text-xs">
                      <span className="text-secondary-foreground">Type</span>
                      <span className="font-medium bg-secondary px-1.5 py-0.5 rounded">{selectedNodeData.type}</span>
                    </div>
                    <div className="flex justify-between text-xs items-center">
                      <span className="text-secondary-foreground">Risk Relevance</span>
                      {selectedNodeData.suspicious ? (
                        <span className="font-medium text-danger flex items-center gap-1"><AlertCircle className="w-3 h-3"/> High</span>
                      ) : (
                        <span className="font-medium text-success">Normal</span>
                      )}
                    </div>
                    {currentGraph && (
                      <div className="flex justify-between text-xs items-center">
                        <span className="text-secondary-foreground">Connected Entities</span>
                        <span className="font-medium">
                          {currentGraph.edges.filter((e: any) => e.source === selectedNodeData.id || e.target === selectedNodeData.id).length}
                        </span>
                      </div>
                    )}
                  </div>
                  
                  {selectedNodeData.properties && Object.keys(selectedNodeData.properties).length > 0 && (
                    <div className="space-y-2 border-t border-border pt-4">
                      <div className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground mb-2">Properties</div>
                      {renderProps(selectedNodeData.properties)}
                    </div>
                  )}
                </>
              )}
              
              {selectedEdgeData && (
                <>
                  <div>
                    <div className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground mb-1">Relationship</div>
                    <div className="text-sm font-semibold mb-1">{selectedEdgeData.label || selectedEdgeData.type}</div>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="p-3 bg-secondary/30 rounded-lg space-y-2 border border-border">
                      <div className="text-xs">
                        <span className="text-secondary-foreground block mb-0.5 text-[10px] uppercase">Source</span>
                        <span className="font-mono break-all">{selectedEdgeData.source}</span>
                      </div>
                      <div className="flex justify-center py-1">
                        <div className="w-0.5 h-4 bg-border"></div>
                      </div>
                      <div className="text-xs">
                        <span className="text-secondary-foreground block mb-0.5 text-[10px] uppercase">Target</span>
                        <span className="font-mono break-all">{selectedEdgeData.target}</span>
                      </div>
                    </div>
                    
                    <div className="flex justify-between text-xs items-center">
                      <span className="text-secondary-foreground">Suspicious</span>
                      {selectedEdgeData.suspicious || (currentGraph?.suspicious_edges?.includes(`${selectedEdgeData.source}-${selectedEdgeData.target}`)) ? (
                        <span className="font-medium text-danger">Yes</span>
                      ) : (
                        <span className="font-medium text-secondary-foreground">No</span>
                      )}
                    </div>
                  </div>
                  
                  {selectedEdgeData.properties && Object.keys(selectedEdgeData.properties).length > 0 && (
                    <div className="space-y-2 border-t border-border pt-4">
                      <div className="text-[10px] uppercase font-bold tracking-wider text-secondary-foreground mb-2">Metadata</div>
                      {renderProps(selectedEdgeData.properties)}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
