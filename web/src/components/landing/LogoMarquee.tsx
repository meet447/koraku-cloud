import { cn } from "@/lib/cn";

type LogoItem = {
  alt: string;
  src: string;
  gradient: string;
};

const LOGOS: LogoItem[] = [
  { alt: "Procure", src: "https://svgl.app/library/procure.svg", gradient: "from-blue-400 to-blue-600" },
  { alt: "Shopify", src: "https://svgl.app/library/shopify.svg", gradient: "from-yellow-300 to-yellow-600" },
  { alt: "Blender", src: "https://svgl.app/library/blender.svg", gradient: "from-blue-300 to-blue-700" },
  { alt: "Figma", src: "https://svgl.app/library/figma.svg", gradient: "from-purple-400 to-purple-700" },
  { alt: "Spotify", src: "https://svgl.app/library/spotify.svg", gradient: "from-pink-400 to-red-600" },
  { alt: "Lottielab", src: "https://svgl.app/library/lottielab.svg", gradient: "from-yellow-300 to-green-500" },
  { alt: "Google Cloud", src: "https://svgl.app/library/google-cloud.svg", gradient: "from-sky-200 to-sky-600" },
  { alt: "Bing", src: "https://svgl.app/library/bing.svg", gradient: "from-cyan-300 to-teal-600" },
];

function LogoCard({ logo }: { logo: LogoItem }) {
  return (
    <div className="group relative flex h-24 w-40 shrink-0 items-center justify-center overflow-hidden rounded-full border border-slate-200/60 bg-white shadow-sm transition-all hover:border-slate-300">
      <div
        className={cn(
          "absolute inset-0 scale-150 bg-gradient-to-br opacity-0 transition-all duration-300 group-hover:scale-100 group-hover:opacity-100",
          logo.gradient,
        )}
        aria-hidden
      />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={logo.src}
        alt={logo.alt}
        className="relative z-10 h-8 w-auto max-w-[70%] object-contain transition-all group-hover:brightness-0 group-hover:invert"
        loading="lazy"
        decoding="async"
      />
    </div>
  );
}

export function LogoMarquee() {
  const loop = [...LOGOS, ...LOGOS];

  return (
    <div
      className={cn(
        "group/marquee mt-10 overflow-hidden",
        "[mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]",
      )}
    >
      <div
        className="flex w-max gap-4 animate-marquee group-hover/marquee:[animation-play-state:paused]"
        aria-hidden
      >
        {loop.map((logo, index) => (
          <LogoCard key={`${logo.alt}-${index}`} logo={logo} />
        ))}
      </div>
    </div>
  );
}
