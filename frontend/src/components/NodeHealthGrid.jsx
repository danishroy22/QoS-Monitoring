import NodeCard from "./NodeCard";

export default function NodeHealthGrid({ metrics, selectedNode, onSelect }) {
  const rows = Array.isArray(metrics) ? metrics : [];

  if (rows.length === 0) {
    return (
      <section className="panel">
        <div className="panel-head">
          <h2>Access nodes</h2>
        </div>
        <p className="empty-copy">
          No measurements yet. Start the simulator with{" "}
          <code>--publish-api</code> to feed live data.
        </p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Access nodes</h2>
        <p>Select a node to inspect historical QoS trends</p>
      </div>
      <div className="node-grid">
        {rows.map((node) => (
          <NodeCard
            key={node.node_code}
            node={node}
            selected={selectedNode === node.node_code}
            onSelect={onSelect}
          />
        ))}
      </div>
    </section>
  );
}
