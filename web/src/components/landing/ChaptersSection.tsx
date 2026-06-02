export function ChaptersSection() {
  return (
    <section id="how-to" className="border-y border-black/10 bg-[#f8f8f7] px-5 py-16 font-landing-sans sm:px-8 lg:py-20">
      <div className="mx-auto w-full max-w-[1120px]">
        <p className="mb-4 inline-block rounded bg-white px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 shadow-sm">
          Core Features
        </p>
        <h2 className="landing-pixel-headline max-w-4xl font-landing-serif text-[3.2rem] font-semibold leading-[0.95] tracking-[-0.055em] text-[#282522] sm:text-[4.8rem]">
          Built for agent work that feels native
        </h2>
        <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-stone-500 sm:text-[17px]">
          Everything your agents need to go from personal context to finished workspace output.
        </p>

        <div className="mt-10 grid grid-cols-1 gap-5 min-[600px]:grid-cols-2 min-[900px]:grid-cols-3">
          <article className="relative flex h-[400px] flex-col justify-end overflow-hidden rounded-lg border border-black/10 bg-white text-left shadow-[10px_10px_0_rgba(0,0,0,0.03)]">
            <div
              className="absolute inset-0 opacity-35"
              style={{
                backgroundImage:
                  "linear-gradient(#ebe8e3 1px, transparent 1px), linear-gradient(90deg, #ebe8e3 1px, transparent 1px)",
                backgroundSize: "28px 28px",
              }}
            />
            <div className="absolute left-6 right-6 top-[30px] z-[2] rounded-md border border-black/10 bg-white p-4 text-[0.8rem] leading-relaxed text-slate-600 shadow-[6px_6px_0_rgba(0,0,0,0.04)]">
              When an email is a <StrongText>bug report</StrongText>, create a{" "}
              <StrongText>workspace issue</StrongText>, summarize context, and{" "}
              <StrongText>ask before sending</StrongText> to Slack.
            </div>
            <div className="absolute left-10 top-[180px] z-[2] flex items-center gap-1.5 rounded-md border border-black bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-800 shadow-[4px_4px_0_rgba(0,0,0,0.12)]">
              <span className="text-base text-orange-700" aria-hidden>
                ✦
              </span>
              Add more context
            </div>
            <svg
              className="absolute left-[110px] top-[205px] z-10 h-6 w-6 drop-shadow-[0_4px_6px_rgba(0,0,0,0.2)]"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="#0f172a"
              stroke="#ffffff"
              strokeWidth="1"
              aria-hidden
            >
              <path d="M4 2L20 11L11 13L9 22L4 2Z" />
            </svg>
            <h3 className="relative z-[2] border-t border-black/10 bg-white/60 p-6 text-[1.05rem] font-semibold text-slate-800 backdrop-blur-sm">
              Smart Agent Instructions
            </h3>
          </article>

          <article className="relative flex h-[400px] flex-col justify-end overflow-hidden rounded-lg border border-black/10 bg-white text-left shadow-[10px_10px_0_rgba(0,0,0,0.03)]">
            <div
              className="absolute inset-x-0 bottom-[70px] top-0 bg-[#f3f2ef] px-6 py-7"
              style={{
                backgroundImage:
                  "linear-gradient(#e8e4dd 1px, transparent 1px), linear-gradient(90deg, #e8e4dd 1px, transparent 1px)",
                backgroundSize: "32px 32px",
              }}
            >
              <div className="mx-auto grid max-w-[230px] grid-cols-3 gap-3">
                {[
                  ["Gmail", "https://cdn.simpleicons.org/gmail/EA4335"],
                  ["Drive", "https://cdn.simpleicons.org/googledrive/4285F4"],
                  ["Docs", "https://cdn.simpleicons.org/googledocs/4285F4"],
                  ["Slack", "https://cdn.simpleicons.org/slack"],
                  ["Notion", "https://cdn.simpleicons.org/notion/000000"],
                  ["iMessage", "https://cdn.simpleicons.org/imessage/34C759"],
                ].map(([name, src]) => (
                  <div
                    key={name}
                    className="flex h-[58px] flex-col items-center justify-center rounded-md border border-black/10 bg-white shadow-[4px_4px_0_rgba(0,0,0,0.04)]"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={src} alt="" width={22} height={22} className="h-[22px] w-[22px] object-contain" />
                    <span className="mt-1 font-mono text-[9px] uppercase tracking-tight text-stone-500">
                      {name}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mx-auto mt-4 flex max-w-[230px] items-center justify-between rounded-md border border-black/10 bg-white px-3 py-2 shadow-[4px_4px_0_rgba(0,0,0,0.05)]">
                <span className="text-[11px] font-semibold text-stone-600">Connected context</span>
                <span className="rounded bg-lime-100 px-2 py-1 font-mono text-[9px] text-lime-800">
                  live
                </span>
              </div>
            </div>
            <h3 className="relative z-[2] border-t border-black/10 bg-white/60 p-6 text-[1.05rem] font-semibold text-slate-800 backdrop-blur-sm">
              Connected Apps
            </h3>
          </article>

          <article className="relative flex h-[400px] flex-col justify-end overflow-hidden rounded-lg border border-black/10 bg-white text-left shadow-[10px_10px_0_rgba(0,0,0,0.03)]">
            <div className="landing-mesh-overlay pointer-events-none absolute inset-0" aria-hidden />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="https://pub-f170a2592d2c4a1485466404c36807be.r2.dev/viktor/library%20icon.svg"
              alt=""
              width={170}
              height={140}
              className="absolute left-1/2 top-[50px] w-[170px] -translate-x-1/2 opacity-80 grayscale drop-shadow-[0_15px_25px_rgba(0,0,0,0.08)]"
            />
            <div className="absolute left-1/2 top-[220px] z-[2] flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-md border border-black bg-white px-[18px] py-1.5 text-xs font-medium text-slate-800 shadow-[4px_4px_0_rgba(0,0,0,0.1)]">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="11" cy="11" r="8" stroke="#64748b" strokeWidth="2" />
                <line
                  x1="21"
                  y1="21"
                  x2="16.65"
                  y2="16.65"
                  stroke="#64748b"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Search workspace
            </div>
            <h3 className="relative z-[2] border-t border-black/10 bg-white/60 p-6 text-[1.05rem] font-semibold text-slate-800 backdrop-blur-sm">
              Agent Workspace Library
            </h3>
          </article>

          <article className="relative flex h-[400px] flex-col justify-end overflow-hidden rounded-lg border border-black/10 bg-white text-left shadow-[10px_10px_0_rgba(0,0,0,0.03)]">
            <div
              className="absolute inset-0 opacity-35"
              style={{
                backgroundImage:
                  "linear-gradient(#ebe8e3 1px, transparent 1px), linear-gradient(90deg, #ebe8e3 1px, transparent 1px)",
                backgroundSize: "28px 28px",
              }}
            />
            <div className="absolute left-1/2 top-8 z-[2] h-[190px] w-[230px] -translate-x-1/2 rounded-md border border-black/10 bg-white p-4 shadow-[6px_6px_0_rgba(0,0,0,0.04)]">
              <div className="relative h-full">
                {[
                  ["left-2 top-4", "Name"],
                  ["right-4 top-2", "Tone"],
                  ["left-14 top-20", "Decisions"],
                  ["right-2 bottom-5", "Files"],
                  ["left-4 bottom-4", "Prefs"],
                ].map(([position, label]) => (
                  <div
                    key={label}
                    className={`absolute ${position} rounded-md border border-black/10 bg-[#f5f4f2] px-2 py-1 font-mono text-[10px] font-semibold text-stone-600`}
                  >
                    {label}
                  </div>
                ))}
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 230 160" fill="none" aria-hidden>
                  <path d="M42 34L115 80M62 95L115 80M62 95L170 126M62 95L184 38M42 130L62 95M154 28L115 80" stroke="#ddd6cb" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <div className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-orange-400 shadow-[0_0_0_4px_rgba(251,146,60,0.25)]" />
              </div>
            </div>
            <div className="absolute bottom-[84px] left-6 right-6 z-[2] flex items-center justify-between rounded-md border border-black/10 bg-white px-3 py-2 shadow-[4px_4px_0_rgba(0,0,0,0.05)]">
              <span className="text-[11px] font-semibold text-stone-600">Learns automatically</span>
              <span className="rounded bg-orange-100 px-2 py-1 font-mono text-[9px] text-orange-800">
                memory
              </span>
            </div>
            <h3 className="relative z-[2] border-t border-black/10 bg-white/60 p-6 text-[1.05rem] font-semibold text-slate-800 backdrop-blur-sm">
              Learned Memory
            </h3>
          </article>

          <article className="relative flex h-[400px] flex-col justify-end overflow-hidden rounded-lg border border-black/10 bg-white text-left shadow-[10px_10px_0_rgba(0,0,0,0.03)]">
            <div className="absolute inset-x-0 bottom-[70px] top-0 bg-[#f3f2ef] px-6 py-5">
              <div className="mx-auto max-w-[210px] overflow-hidden rounded-[32px] border-[5px] border-stone-900 bg-stone-900 shadow-[8px_8px_0_rgba(0,0,0,0.1)]">
                {/* Status bar */}
                <div className="flex items-center justify-between bg-white px-4 pb-1 pt-2">
                  <span className="text-[9px] font-semibold text-stone-900">9:41</span>
                  <div className="mx-auto h-[18px] w-[72px] rounded-full bg-stone-900" />
                  <div className="flex items-center gap-0.5">
                    <span className="h-2 w-3 rounded-sm bg-stone-900" />
                    <span className="h-2.5 w-4 rounded-sm border border-stone-900" />
                  </div>
                </div>
                {/* iMessage header */}
                <div className="flex items-center gap-2 border-b border-stone-200 bg-white px-3 py-2">
                  <span className="text-[11px] text-[#007AFF]">‹ Messages</span>
                  <div className="mx-auto flex flex-col items-center">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-b from-orange-400 to-orange-600 text-[10px] font-bold text-white">
                      K
                    </div>
                    <span className="mt-0.5 text-[10px] font-semibold text-stone-900">Koraku</span>
                  </div>
                  <span className="w-12" />
                </div>
                {/* Chat area */}
                <div className="space-y-2 bg-white px-3 py-3">
                  <p className="text-center text-[8px] font-medium text-stone-400">Today 9:12 AM</p>
                  <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-[#E9E9EB] px-3 py-2 text-[10px] leading-4 text-stone-900">
                    Text Koraku a voice note from the train.
                  </div>
                  <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-[#007AFF] px-3 py-2 text-[10px] leading-4 text-white">
                    Summarized and opened in chat.
                  </div>
                  <div className="ml-auto flex max-w-[70%] items-center gap-2 rounded-2xl rounded-br-sm bg-[#007AFF] px-3 py-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/25 text-[8px] text-white">
                      ▶
                    </span>
                    <div className="flex flex-1 items-center gap-0.5">
                      {Array.from({ length: 14 }).map((_, index) => (
                        <span
                          key={index}
                          className="w-0.5 rounded-full bg-white/80"
                          style={{ height: `${4 + (index % 4) * 3}px` }}
                        />
                      ))}
                    </div>
                    <span className="text-[8px] text-white/80">0:08</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute bottom-[84px] left-6 right-6 z-[2] flex items-center justify-between rounded-md border border-black/10 bg-white px-3 py-2 shadow-[4px_4px_0_rgba(0,0,0,0.05)]">
              <span className="text-[11px] font-semibold text-stone-600">iMessage / SMS / voice</span>
              <span className="rounded bg-lime-100 px-2 py-1 font-mono text-[9px] text-lime-800">
                linked
              </span>
            </div>
            <h3 className="relative z-[2] border-t border-black/10 bg-white/60 p-6 text-[1.05rem] font-semibold text-slate-800 backdrop-blur-sm">
              iMessage and Voice Notes
            </h3>
          </article>

          <article className="relative flex h-[400px] flex-col justify-end overflow-hidden rounded-lg border border-black/10 bg-white text-left shadow-[10px_10px_0_rgba(0,0,0,0.03)]">
            <div
              className="absolute inset-0 opacity-35"
              style={{
                backgroundImage:
                  "linear-gradient(#ebe8e3 1px, transparent 1px), linear-gradient(90deg, #ebe8e3 1px, transparent 1px)",
                backgroundSize: "28px 28px",
              }}
            />
            <div className="absolute left-6 right-6 top-8 z-[2] rounded-md border border-black/10 bg-white p-4 shadow-[6px_6px_0_rgba(0,0,0,0.04)]">
              <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-stone-400">
                Agent profile
              </p>
              <div className="space-y-2">
                {[
                  ["Name", "Koraku"],
                  ["Preferences", "Concise + next steps"],
                  ["Persona", "Warm mentor, no fluff"],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-md bg-[#f5f4f2] px-3 py-2">
                    <p className="font-mono text-[9px] uppercase text-stone-400">{label}</p>
                    <p className="mt-1 text-xs font-semibold text-stone-700">{value}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="absolute bottom-[84px] left-6 right-6 z-[2] rounded-md border border-black/10 bg-white px-3 py-2 shadow-[4px_4px_0_rgba(0,0,0,0.05)]">
              <p className="text-[11px] font-semibold leading-5 text-stone-600">
                Profile text is injected into every chat so agents keep your stable context.
              </p>
            </div>
            <h3 className="relative z-[2] border-t border-black/10 bg-white/60 p-6 text-[1.05rem] font-semibold text-slate-800 backdrop-blur-sm">
              Personalization Layer
            </h3>
          </article>
        </div>
      </div>
    </section>
  );
}

function StrongText({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-semibold text-orange-800">
      {children}
    </span>
  );
}
