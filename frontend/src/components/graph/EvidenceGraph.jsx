import { useCallback, useEffect, useMemo, useState } from 'react'
import { Background, Controls, ReactFlow, useEdgesState, useNodesState } from '@xyflow/react'
import EvidenceNode from './EvidenceNode'

const nodeTypes = { evidence: EvidenceNode }

const STATUS = {
  verified: 'VERIFIED',
  partial: 'PARTIAL',
  mismatch: 'MISMATCH',
}

const EDGE_COLOR = {
  verified: '#22c55e',
  partial: '#eab308',
  mismatch: '#ef4444',
}

function decorateEdges(rawEdges, rawNodes) {
  const byId = Object.fromEntries(rawNodes.map((node) => [node.id, node]))
  return rawEdges.map((edge) => {
    const state = byId[edge.target]?.data?.state
    return {
      ...edge,
      animated: state === 'partial' || state === 'mismatch',
      style: {
        stroke: EDGE_COLOR[state] || '#9ca3af',
        strokeWidth: state === 'mismatch' ? 2 : 1.5,
      },
    }
  })
}

export default function EvidenceGraph({ nodes: initialNodes, edges: initialEdges }) {
  const seededNodes = useMemo(
    () => initialNodes.map((node) => ({ ...node, draggable: true, selectable: true })),
    [initialNodes],
  )
  const seededEdges = useMemo(() => decorateEdges(initialEdges, initialNodes), [initialEdges, initialNodes])
  const [nodes, , onNodesChange] = useNodesState(seededNodes)
  const [edges, , onEdgesChange] = useEdgesState(seededEdges)
  const [toast, setToast] = useState(null)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    if (!toast) return undefined
    const timer = window.setTimeout(() => setToast(null), 3000)
    return () => window.clearTimeout(timer)
  }, [toast])

  const onNodeClick = useCallback((_, node) => {
    const status = STATUS[node.data.state] || String(node.data.state || 'UNKNOWN').toUpperCase()
    setSelected(node)
    setToast({
      id: `${node.id}-${Date.now()}`,
      text: `${node.data.title} — ${status}`,
    })
  }, [])

  const onPaneClick = useCallback(() => {
    setSelected(null)
  }, [])

  return (
    <div className="graph-wrap">
      {toast ? (
        <div className="graph-toast" key={toast.id} role="status">
          {toast.text}
        </div>
      ) : null}
      {selected ? (
        <aside className="graph-inspect">
          <div className="kicker">{selected.data.kicker}</div>
          <div className="title">{selected.data.title}</div>
          <div className="meta">{selected.data.meta}</div>
          <div className={`inspect-status ${selected.data.state}`}>{STATUS[selected.data.state]}</div>
        </aside>
      ) : null}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        panOnScroll
        zoomOnScroll
        panOnDrag
        fitView
        minZoom={0.5}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--graph-grid)" gap={22} />
        <Controls position="bottom-right" showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
