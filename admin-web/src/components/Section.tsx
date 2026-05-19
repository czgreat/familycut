import { PropsWithChildren } from "react";

type SectionProps = PropsWithChildren<{
  title: string;
  description: string;
}>;

export function Section({ title, description, children }: SectionProps) {
  return (
    <section className="section">
      <div className="section-header">
        <div>
          <p className="eyebrow">{title}</p>
          <h2>{description}</h2>
        </div>
      </div>
      <div className="section-body">{children}</div>
    </section>
  );
}
