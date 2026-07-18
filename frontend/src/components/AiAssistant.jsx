import { Sparkles } from "lucide-react";
import GlassCard from "./ui/GlassCard";
import LoadingPulse from "./ui/LoadingPulse";
import PanelHeader from "./ui/PanelHeader";

export default function AiAssistant({ recommendation, loading }) {
  if (loading) {
    return (
      <GlassCard className="iq-panel ai" delay={0.15}>
        <PanelHeader
          title="AI Network Analysis"
          subtitle="Generating insights from your latest measurements"
          action={<Sparkles size={18} color="var(--accent)" />}
        />
        <LoadingPulse label="Analysing connection quality…" compact />
      </GlassCard>
    );
  }

  if (!recommendation) {
    return (
      <GlassCard className="iq-panel ai" delay={0.15}>
        <PanelHeader
          title="AI Network Analysis"
          subtitle="Run a test to unlock AI guidance"
          action={<Sparkles size={18} color="var(--muted)" />}
        />
        <p className="iq-empty">No analysis yet. Complete a speed test to receive recommendations.</p>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="iq-panel ai" delay={0.15}>
      <PanelHeader
        title="AI Network Analysis"
        subtitle={recommendation.model_provider}
        action={<Sparkles size={18} color="var(--accent)" />}
      />

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
    </GlassCard>
  );
}
