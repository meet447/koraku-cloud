import { cn } from "@/lib/cn";

type LogoItem = {
  alt: string;
  src: string;
};

const LOGOS: LogoItem[] = [
  { alt: "Procure", src: "https://svgl.app/library/procure.svg" },
  { alt: "Shopify", src: "https://svgl.app/library/shopify.svg" },
  { alt: "Blender", src: "https://svgl.app/library/blender.svg" },
  { alt: "Figma", src: "https://svgl.app/library/figma.svg" },
  { alt: "Spotify", src: "https://svgl.app/library/spotify.svg" },
  { alt: "Lottielab", src: "https://svgl.app/library/lottielab.svg" },
  { alt: "Google Cloud", src: "https://svgl.app/library/google-cloud.svg" },
  { alt: "Bing", src: "https://svgl.app/library/bing.svg" },
];

function LogoCard({ logo }: { logo: LogoItem }) {
  return (
    <div className="group relative flex h-24 w-40 shrink-0 items-center justify-center overflow-hidden rounded-full border border-black/5 bg-white shadow-sm transition-colors hover:bg-landing-ink">
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
    <div className="mt-14">
      <p className="mb-8 text-center text-xs font-semibold uppercase tracking-[0.2em] text-landing-soft">
        Connect the tools you already use
      </p>
      <div
        className={cn(
          "group/marquee overflow-hidden",
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
    </div>
  );
}
