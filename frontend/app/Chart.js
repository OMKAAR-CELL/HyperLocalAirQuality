"use client";

// Small dependency-free SVG line chart.
// series: [{ name, color, points: [{ t: ms, v: number }] }]
// threshold: optional { value, label }
export default function Chart({ series, threshold, unit }) {
  const W = 600, H = 200, PL = 42, PR = 10, PT = 10, PB = 24;
  const all = series.flatMap((s) => s.points);
  if (all.length < 2) {
    return <div className="sub" style={{ padding: "40px 0" }}>Not enough data yet.</div>;
  }
  const tMin = Math.min(...all.map((p) => p.t));
  const tMax = Math.max(...all.map((p) => p.t));
  let vMax = Math.max(...all.map((p) => p.v), threshold ? threshold.value : 0) * 1.1;
  const vMin = 0;
  if (vMax <= vMin) vMax = 1;

  const x = (t) => PL + ((t - tMin) / Math.max(1, tMax - tMin)) * (W - PL - PR);
  const y = (v) => PT + (1 - (v - vMin) / (vMax - vMin)) * (H - PT - PB);

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => vMin + f * (vMax - vMin));
  const fmtTime = (t) =>
    new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${unit} over time`}>
      {ticks.map((v, i) => (
        <g key={i}>
          <line x1={PL} x2={W - PR} y1={y(v)} y2={y(v)} stroke="var(--line)" strokeWidth="1" />
          <text x={PL - 6} y={y(v) + 4} fontSize="10" textAnchor="end" fill="var(--muted)">
            {Math.round(v)}
          </text>
        </g>
      ))}
      {threshold && (
        <g>
          <line x1={PL} x2={W - PR} y1={y(threshold.value)} y2={y(threshold.value)}
            stroke="var(--red)" strokeWidth="1.2" strokeDasharray="5 4" />
          <text x={W - PR} y={y(threshold.value) - 4} fontSize="10" textAnchor="end" fill="var(--red)">
            {threshold.label}
          </text>
        </g>
      )}
      {series.map((s) => (
        <polyline key={s.name} fill="none" stroke={s.color} strokeWidth="2"
          strokeLinejoin="round" strokeLinecap="round"
          points={s.points.map((p) => `${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ")} />
      ))}
      <text x={PL} y={H - 6} fontSize="10" fill="var(--muted)">{fmtTime(tMin)}</text>
      <text x={W - PR} y={H - 6} fontSize="10" textAnchor="end" fill="var(--muted)">{fmtTime(tMax)}</text>
    </svg>
  );
}
