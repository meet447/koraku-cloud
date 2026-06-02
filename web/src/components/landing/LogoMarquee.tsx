import { cn } from "@/lib/cn";
import styles from "@/components/landing/LogoMarquee.module.css";

type LogoItem = {
  alt: string;
  src: string;
  gradient: string;
};

const LOGOS: LogoItem[] = [
  {
    alt: "Procure",
    src: "https://svgl.app/library/procure.svg",
    gradient: "linear-gradient(135deg, #60a5fa 0%, #2563eb 100%)",
  },
  {
    alt: "Shopify",
    src: "https://svgl.app/library/shopify.svg",
    gradient: "linear-gradient(135deg, #fde047 0%, #ca8a04 100%)",
  },
  {
    alt: "Blender",
    src: "https://svgl.app/library/blender.svg",
    gradient: "linear-gradient(135deg, #93c5fd 0%, #1d4ed8 100%)",
  },
  {
    alt: "Figma",
    src: "https://svgl.app/library/figma.svg",
    gradient: "linear-gradient(135deg, #c084fc 0%, #7e22ce 100%)",
  },
  {
    alt: "Spotify",
    src: "https://svgl.app/library/spotify.svg",
    gradient: "linear-gradient(135deg, #f472b6 0%, #dc2626 100%)",
  },
  {
    alt: "Lottielab",
    src: "https://svgl.app/library/lottielab.svg",
    gradient: "linear-gradient(135deg, #fde047 0%, #22c55e 100%)",
  },
  {
    alt: "Google Cloud",
    src: "https://svgl.app/library/google-cloud.svg",
    gradient: "linear-gradient(135deg, #bae6fd 0%, #0284c7 100%)",
  },
  {
    alt: "Bing",
    src: "https://svgl.app/library/bing.svg",
    gradient: "linear-gradient(135deg, #67e8f9 0%, #0d9488 100%)",
  },
];

function LogoCard({ logo }: { logo: LogoItem }) {
  return (
    <div className="group relative flex h-24 w-40 shrink-0 items-center justify-center overflow-hidden rounded-full border border-slate-200/60 bg-white shadow-sm transition-all hover:border-slate-300">
      <div
        className="absolute inset-0 scale-150 opacity-0 transition-all duration-300 group-hover:scale-100 group-hover:opacity-100"
        style={{ background: logo.gradient }}
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
    <div className={cn("mt-10", styles.mask)}>
      <div className={styles.track} aria-hidden>
        {loop.map((logo, index) => (
          <LogoCard key={`${logo.alt}-${index}`} logo={logo} />
        ))}
      </div>
    </div>
  );
}
