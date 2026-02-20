import { cn } from "@/lib/utils";

export function SectionHeading({
  eyebrow,
  title,
  description,
  className
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      {eyebrow ? <p className="text-xs uppercase tracking-[0.25em] text-cyan-200/70">{eyebrow}</p> : null}
      <h1 className="text-2xl font-semibold md:text-4xl">{title}</h1>
      {description ? <p className="max-w-2xl text-sm text-cyan-50/70 md:text-base">{description}</p> : null}
    </div>
  );
}
