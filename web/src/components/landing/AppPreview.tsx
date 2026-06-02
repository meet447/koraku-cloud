import { Check, Cpu, FolderOpen, PlugZap, Workflow } from "lucide-react";

export function AppPreview({ className = "mt-14" }: { className?: string }) {
  return (
    <div className={`mx-auto max-w-5xl rounded-xl border border-black/10 bg-white/80 p-2 shadow-[0_24px_80px_-55px_rgba(0,0,0,0.55)] ${className}`}>
      <div className="rounded-lg border border-black/10 bg-[#f5f4f2] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 bg-red-400" />
            <span className="h-3 w-3 bg-yellow-400" />
            <span className="h-3 w-3 bg-green-400" />
          </div>
          <div className="hidden text-xs font-semibold text-slate-400 sm:block">
            Agent desktop / workspace / integrations / models
          </div>
        </div>
        <div className="grid min-h-[390px] gap-3 md:grid-cols-[220px_1fr_300px]">
          <aside className="hidden rounded-md border border-black/10 bg-[#efe8df] p-3 md:block">
            <div className="mb-4 rounded-md bg-white p-3">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
                Desktop
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-800">Research agent</p>
            </div>
            {[
              [FolderOpen, "Files"],
              [PlugZap, "Apps"],
              [Cpu, "Models"],
              [Workflow, "Runs"],
            ].map(([Icon, label]) => {
              const LucideIcon = Icon as typeof FolderOpen;
              return (
                <div key={label as string} className="mb-2 flex items-center gap-2 rounded-md bg-white/70 px-3 py-2 text-sm font-semibold text-slate-700">
                  <LucideIcon className="h-4 w-4 text-orange-700" />
                  {label as string}
                </div>
              );
            })}
          </aside>

          <div className="rounded-md border border-black/10 bg-white p-5">
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-slate-400">
              Agent workspace
            </p>
            <div className="rounded-lg bg-[#fff1d6] p-4 text-sm text-slate-700">
              Compare pricing notes, draft a follow-up, create a workspace summary, then wait
              for approval before sending.
            </div>
            <div className="mt-5 grid gap-3">
              {["Memory matched", "Gmail + Drive context loaded", "summary.md created", "Approval required"].map((item) => (
                <div key={item} className="flex items-center gap-3 rounded-lg border border-black/10 p-3">
                  <Check className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-semibold text-slate-800">{item}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-md border border-black/10 bg-slate-950 p-4 text-white">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/40">Control panel</p>
            <div className="mt-5 space-y-3">
              {["Model: Advanced", "Automation: Daily brief", "Apps: Gmail, Drive", "Safety check"].map((item, index) => (
                <div key={item} className="flex items-center justify-between rounded-lg bg-white/10 p-3">
                  <span className="text-sm">{item}</span>
                  <span className="text-xs text-lime-300">{index === 3 ? "wait" : "ready"}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
