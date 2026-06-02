import { cn } from "@/lib/cn";

export function PixelEdge({ position = "bottom" }: { position?: "top" | "bottom" }) {
  return (
    <div
      className={cn(
        "pointer-events-none absolute left-0 right-0 z-20 h-10 bg-repeat-x",
        position === "bottom" ? "bottom-0" : "top-0 rotate-180",
      )}
      style={{
        backgroundImage:
          "linear-gradient(90deg, transparent 0 10px, #f7f7f0 10px 18px, transparent 18px 26px, #f7f7f0 26px 44px, transparent 44px 58px, #f7f7f0 58px 72px)",
        backgroundSize: "72px 40px",
      }}
      aria-hidden
    />
  );
}

export function PixelCloud({ className }: { className?: string }) {
  return (
    <div className={cn("absolute grid grid-cols-6 opacity-85", className)} aria-hidden>
      {Array.from({ length: 18 }).map((_, index) => (
        <span
          key={index}
          className={cn(
            "h-5 w-5 bg-white/80",
            [0, 1, 4, 5, 12, 17].includes(index) && "opacity-0",
            [2, 3, 8, 9, 10, 14, 15, 16].includes(index) && "bg-white",
          )}
        />
      ))}
    </div>
  );
}

export function PixelWorld() {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden>
      <div className="absolute inset-0 bg-gradient-to-b from-[#4b4fd7] via-[#f08a5d] via-[58%] to-[#ffd08a]" />
      <div className="absolute left-[18%] top-28 h-24 w-24 bg-[#ffd36e] shadow-[0_0_80px_rgba(255,193,94,0.75)]" />
      <PixelCloud className="left-[10%] top-36 scale-150 opacity-70" />
      <PixelCloud className="right-[20%] top-24 scale-125 opacity-60" />
      <PixelCloud className="left-[43%] top-56 scale-[2.2] opacity-35" />

      <div className="absolute bottom-0 left-0 right-0 h-[210px] bg-[#4b7b36]" />
      <div className="absolute bottom-[154px] left-0 right-0 h-12 bg-[#7fb64f]" />
      <div
        className="absolute bottom-[206px] left-0 right-0 h-10 bg-repeat-x"
        style={{
          backgroundImage:
            "linear-gradient(90deg, #7fb64f 0 18px, transparent 18px 26px, #7fb64f 26px 42px, transparent 42px 48px)",
          backgroundSize: "48px 40px",
        }}
      />

      <div className="absolute bottom-[150px] left-[8%] hidden sm:block">
        <div className="h-12 w-12 bg-[#315f36]" />
        <div className="ml-4 h-16 w-5 bg-[#5c3828]" />
        <div className="-ml-5 -mt-28 grid grid-cols-5">
          {Array.from({ length: 25 }).map((_, index) => (
            <span
              key={index}
              className={cn(
                "h-6 w-6 bg-[#244f2c]",
                [0, 4, 20, 24].includes(index) && "opacity-0",
                [6, 7, 8, 11, 12, 13, 16, 17, 18].includes(index) && "bg-[#3f7d3e]",
              )}
            />
          ))}
        </div>
      </div>

      <div className="absolute bottom-[118px] right-[8%] hidden h-[170px] w-[260px] md:block">
        <div className="absolute bottom-0 left-8 h-8 w-44 bg-[#6d5542]" />
        <div className="absolute bottom-8 left-0 h-20 w-56 bg-[#2d3136] p-3 shadow-[8px_8px_0_rgba(0,0,0,0.25)]">
          <div className="h-full w-full border-4 border-[#47515c] bg-[#fb9d6c]">
            <div className="mt-6 h-5 w-24 bg-[#ffe4a8]/70" />
            <div className="ml-14 mt-2 h-4 w-20 bg-[#4b4fd7]/35" />
          </div>
        </div>
        <div className="absolute bottom-0 right-0 h-14 w-24 bg-[#8c6a3f] shadow-[6px_6px_0_rgba(0,0,0,0.15)]" />
      </div>

      <div className="absolute right-[30%] top-[190px] hidden space-y-2 lg:block">
        {["Agent desktop ready", "Model: Advanced", "Approval waiting"].map((item) => (
          <div
            key={item}
            className="rounded-md border border-white/20 bg-slate-900/55 px-4 py-2 text-xs font-semibold text-white shadow-[4px_4px_0_rgba(0,0,0,0.2)] backdrop-blur-sm"
          >
            <span className="mr-2 inline-block h-2 w-2 bg-lime-300" />
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
