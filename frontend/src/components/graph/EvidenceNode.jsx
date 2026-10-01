import { Handle, Position } from '@xyflow/react'

export default function EvidenceNode({ data, selected }) {
  return (
    <div className={`evidence-node ${data.state} ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="kicker">{data.kicker}</div>
      <div className="title">{data.title}</div>
      <div className="meta">{data.meta}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}
