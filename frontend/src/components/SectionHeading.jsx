/**
 * SectionHeading — editorial section header: a small index, a short accent rule,
 * the title, and a one-line subtitle. Gives the page a considered, magazine-like
 * rhythm without decoration for its own sake.
 */
export default function SectionHeading({ index, title, subtitle }) {
  return (
    <div className="mb-5">
      <div className="flex items-center gap-2.5 mb-2">
        <span className="font-display text-xs font-bold text-clay tabular-nums">{index}</span>
        <span className="h-px w-8 accent-rule" />
      </div>
      <h2 className="font-display text-2xl md:text-3xl font-bold text-ink">{title}</h2>
      {subtitle && <p className="text-ink-soft text-sm mt-1.5">{subtitle}</p>}
    </div>
  );
}
