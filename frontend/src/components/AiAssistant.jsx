export default function AiAssistant({ recommendation, loading }) {
  if (loading) {
    return (
      <section className="iq-panel glass ai">
        <div className="iq-panel-head">
          <h2>AI Network Analysis</h2>
        </div>
        <p className="iq-empty">Generating analysis…</p>
      </section>
    );
  }

  if (!recommendation) {
    return (
      <section className="iq-panel glass ai">
        <div className="iq-panel-head">
          <h2>AI Network Analysis</h2>
        </div>
        <p className="iq-empty">Run a test to unlock AI guidance.</p>
      </section>
    );
  }

  return (
    <section className="iq-panel glass ai">
      <div className="iq-panel-head">
        <h2>AI Network Analysis</h2>
        <p>{recommendation.model_provider}</p>
      </div>

      <div className="ai-block">
        <h3>Analysis</h3>
        <p>{recommendation.analysis}</p>
      </div>

      <div className="ai-grid">
        <div className="ai-block">
          <h3>Possible reasons</h3>
          <ul>
            {(recommendation.possible_reasons || []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className="ai-block">
          <h3>Recommended actions</h3>
          <ul>
            {(recommendation.recommended_actions || []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
