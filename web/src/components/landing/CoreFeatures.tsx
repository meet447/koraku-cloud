import { cn } from "@/lib/cn";

const NETWORK_IMG =
  "https://pub-f170a2592d2c4a1485466404c36807be.r2.dev/viktor/network.svg";
const FOLDER_IMG =
  "https://pub-f170a2592d2c4a1485466404c36807be.r2.dev/viktor/library%20icon.svg";

function Highlight({ children }: { children: React.ReactNode }) {
  return (
    <span className="bg-landing-highlight bg-clip-text font-semibold text-transparent">
      {children}
    </span>
  );
}

export function CoreFeatures() {
  return (
    <section
      className="bg-white px-5 py-12 font-landing-body text-landing-body md:px-6 md:py-16"
      aria-labelledby="core-features-title"
    >
      <div className="mx-auto w-full max-w-[1100px] text-center">
        <header>
          <p className="mb-4 inline-block bg-landing-badge bg-clip-text text-xs font-semibold uppercase tracking-widest text-transparent">
            Core Features
          </p>
          <h2
            id="core-features-title"
            className="mb-3 text-[2.25rem] font-medium tracking-tight text-slate-900 sm:text-[2.75rem]"
          >
            Built for Memory &amp; Momentum
          </h2>
          <p className="mx-auto mb-[50px] max-w-lg text-lg leading-relaxed text-slate-500">
            Everything you need to go
            <br />
            from chat to lasting memory
          </p>
        </header>

        <div className="grid grid-cols-1 gap-6 min-[600px]:grid-cols-2 min-[900px]:grid-cols-3">
          <article
            className={cn(
              "relative flex h-[340px] flex-col justify-end overflow-hidden rounded-[20px] bg-landing-card text-left shadow-landing-card",
              "bg-landing-card-1",
            )}
          >
            <div className="absolute left-6 right-6 top-[30px] z-[2] rounded-xl bg-white p-4 text-left text-[0.8rem] leading-relaxed text-slate-600 shadow-[0_8px_20px_rgba(0,0,0,0.04)]">
              A companion that learns <Highlight>how you like to work</Highlight>, remembers{" "}
              <Highlight>context from past chats</Highlight>, and{" "}
              <Highlight>suggests helpful next steps</Highlight> without overwriting your voice
            </div>
            <div className="absolute left-10 top-[180px] z-[2] flex items-center gap-1.5 rounded-full border border-black bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-800 shadow-[0_4px_15px_rgba(0,0,0,0.08)]">
              <span className="text-base text-violet-500" aria-hidden>
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
            <h3 className="relative z-[2] p-6 text-[1.05rem] font-semibold text-slate-800">
              Smart Memory Suggestions
            </h3>
          </article>

          <article
            className={cn(
              "relative flex h-[340px] flex-col justify-end overflow-hidden rounded-[20px] text-left shadow-landing-card",
              "bg-landing-card-2",
            )}
          >
            <div className="absolute inset-x-0 bottom-[70px] top-0 flex items-center justify-center px-6">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={NETWORK_IMG}
                alt=""
                width={280}
                height={180}
                className="mt-5 h-[180px] w-full object-contain"
              />
            </div>
            <h3 className="relative z-[2] p-6 text-[1.05rem] font-semibold text-slate-800">
              Connected Apps
            </h3>
          </article>

          <article
            className={cn(
              "relative flex h-[340px] flex-col justify-end overflow-hidden rounded-[20px] text-left shadow-landing-card",
              "bg-landing-card-3",
            )}
          >
            <div
              className="landing-mesh-overlay pointer-events-none absolute inset-0"
              aria-hidden
            />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={FOLDER_IMG}
              alt=""
              width={170}
              height={140}
              className="absolute left-1/2 top-[50px] w-[170px] -translate-x-1/2 drop-shadow-[0_15px_25px_rgba(0,0,0,0.08)]"
            />
            <div className="absolute left-1/2 top-[220px] z-[2] flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full border border-black bg-white px-[18px] py-1.5 text-xs font-medium text-slate-800 shadow-[0_8px_20px_rgba(0,0,0,0.06)]">
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
              Search in workspace
            </div>
            <h3 className="relative z-[2] p-6 text-[1.05rem] font-semibold text-slate-800">
              Workspace Library
            </h3>
          </article>
        </div>
      </div>
    </section>
  );
}
