import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Background, Controls, ReactFlow, useEdgesState, useNodesState } from '@xyflow/react'
import { useTheme } from '../../theme'
import EvidenceNode from './EvidenceNode'

const nodeTypes = { evidence: memo(EvidenceNode) }

const STATUS = {
  verified: 'VERIFIED',
  partial: 'PARTIAL',
  mismatch: 'MISMATCH',
}

const EDGE_COLOR = {
  verified: 'var(--success)',
  partial: 'var(--warning)',
  mismatch: 'var(--error)',
}

function decorateEdges(rawEdges, rawNodes) {
  const byId = Object.fromEntries(rawNodes.map((node) => [node.id, node]))
  return rawEdges.map((edge) => {
    const state = byId[edge.target]?.data?.state
    return {
      ...edge,
      animated: state === 'partial' || state === 'mismatch',
      style: {
        stroke: EDGE_COLOR[state] || 'var(--muted)',
        strokeWidth: state === 'mismatch' ? 2 : 1.5,
      },
    }
  })
}

function EvidenceGraph({ nodes: initialNodes, edges: initialEdges }) {
  const { theme } = useTheme()
  const toastTimerRef = useRef(0)
  const seededNodes = useMemo(
    () => initialNodes.map((node) => ({ ...node, draggable: true, selectable: true })),
    [initialNodes],
  )
  const seededEdges = useMemo(
    () => decorateEdges(initialEdges, initialNodes),
    [initialEdges, initialNodes],
  )
  const [nodes, , onNodesChange] = useNodesState(seededNodes)
  const [edges, , onEdgesChange] = useEdgesState(seededEdges)
  const [toast, setToast] = useState(null)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (!toast) return undefined
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current)
    toastTimerRef.current = window.setTimeout(() => setToast(null), 2200)
    return () => {
      if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current)
    }
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
          <div className={`inspect-status ${selected.data.state}`}>
            {STATUS[selected.data.state] || String(selected.data.state || 'UNKNOWN').toUpperCase()}
          </div>
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
        colorMode={theme}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--graph-grid)" gap={22} />
        <Controls position="bottom-right" showInteractive={false} />
      </ReactFlow>
    </div>
  )
}

export default memo(EvidenceGraph)
