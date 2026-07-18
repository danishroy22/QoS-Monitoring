/** Consistent panel title + muted subtitle. */
export default function PanelHeader({ title, subtitle, action = null }) {
  return (
    <div className="panel-head">
      <div>
        <h2 className="panel-title">{title}</h2>
        {subtitle && <p className="panel-subtitle">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
