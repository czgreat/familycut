export function StatCard(props: {
  label: string;
  value: string;
  hint?: string;
  tone?: "warm" | "light";
}) {
  return (
    <article className={props.tone === "light" ? "stat-card stat-card-light" : "stat-card"}>
      <p className="stat-label">{props.label}</p>
      <p className="stat-value">{props.value}</p>
      {props.hint ? <p className="stat-hint">{props.hint}</p> : null}
    </article>
  );
}
