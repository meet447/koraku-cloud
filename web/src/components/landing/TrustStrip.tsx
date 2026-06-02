import { Command, ShieldCheck, Zap } from "lucide-react";

const trustItems = [
  [ShieldCheck, "Human approval for risky actions"],
  [Command, "One command center for context"],
  [Zap, "Background runs with visible status"],
] as const;

export function TrustStrip() {
  return (
    <section id="safety" className="bg-[#f8f8f7] px-5 py-16 sm:px-8">
      <div className="mx-auto grid max-w-[980px] gap-3 sm:grid-cols-3">
        {trustItems.map(([Icon, text]) => (
          <div key={text} className="rounded-lg border border-black/10 bg-white p-4 shadow-[6px_6px_0_rgba(0,0,0,0.04)]">
            <Icon className="mb-4 h-5 w-5 text-sky-600" />
            <p className="text-sm font-semibold text-stone-700">{text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
