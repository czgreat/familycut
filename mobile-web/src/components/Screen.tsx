import type { ReactNode } from "react";

export function Screen(props: {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="screen">
      <header className="screen-header">
        <div>
          <p className="screen-eyebrow">{props.eyebrow ?? "FamilyCut Mobile"}</p>
          <h1>{props.title}</h1>
          {props.subtitle ? <p className="screen-subtitle">{props.subtitle}</p> : null}
        </div>
        {props.actions ? <div className="screen-actions">{props.actions}</div> : null}
      </header>
      <div className="screen-body">{props.children}</div>
    </section>
  );
}
