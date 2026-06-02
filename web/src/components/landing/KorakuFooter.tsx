"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef } from "react";
import { APP_BASE } from "@/lib/app-path";
import styles from "@/components/landing/KorakuFooter.module.css";

const FOOTER_VIDEO_SRC =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260503_104800_bc43ae09-f494-43e3-97d7-2f8c1692cfd7.mp4";

function SocialIcon({ href, label, children }: { href: string; label: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className={styles.socialIcon}
      aria-label={label}
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  );
}

export function KorakuFooter() {
  const watermarkSvgRef = useRef<SVGSVGElement>(null);
  const watermarkTextRef = useRef<SVGTextElement>(null);

  const fitWatermark = useCallback(() => {
    const svg = watermarkSvgRef.current;
    const text = watermarkTextRef.current;
    if (!svg || !text) return;
    try {
      const bbox = text.getBBox();
      svg.setAttribute("viewBox", `${bbox.x} ${bbox.y} ${bbox.width} ${bbox.height}`);
    } catch {
      /* getBBox may fail before paint */
    }
  }, []);

  useEffect(() => {
    if (document.fonts?.ready) {
      void document.fonts.ready.then(fitWatermark);
    } else {
      window.addEventListener("load", fitWatermark);
      return () => window.removeEventListener("load", fitWatermark);
    }
  }, [fitWatermark]);

  useEffect(() => {
    window.addEventListener("resize", fitWatermark);
    return () => window.removeEventListener("resize", fitWatermark);
  }, [fitWatermark]);

  return (
    <section className={styles.section} aria-labelledby="koraku-footer-heading">
      <h2 id="koraku-footer-heading" className="sr-only">
        Koraku footer
      </h2>

      <div className={styles.wrapper}>
        <div className={styles.footerLeft}>
          <video
            className={styles.footerLeftVideo}
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            aria-hidden
          >
            <source src={FOOTER_VIDEO_SRC} type="video/mp4" />
          </video>

          <div className={styles.footerLogo}>
            <div className={styles.footerLogoMark} aria-hidden>
              K
            </div>
            <span className={styles.footerLogoName}>Koraku</span>
          </div>

          <div className={styles.footerTaglineContainer}>
            <p className={styles.footerTagline}>
              Smarter memory and automation,
              <br />
              <span>powered by AI.</span>
            </p>
          </div>

          <div className={styles.footerSocialRow}>
            <span className={styles.footerSocialLabel}>Stay in touch!</span>
            <div className={styles.footerSocialIcons}>
              <SocialIcon href="https://discord.com" label="Discord">
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
              </SocialIcon>
              <SocialIcon href="https://x.com" label="X">
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </SocialIcon>
              <SocialIcon href="https://linkedin.com" label="LinkedIn">
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                </svg>
              </SocialIcon>
              <SocialIcon href="https://github.com/meet447/koraku-cloud" label="GitHub">
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                </svg>
              </SocialIcon>
            </div>
          </div>
        </div>

        <div className={styles.footerRight}>
          <div className={styles.footerLuckyGraphic} aria-hidden>
            <div className={styles.luckyCube}>
              <span className={styles.luckyCubeMark}>K</span>
            </div>
            <div className={styles.luckyTextRow}>
              <svg className={styles.luckyArrow} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 20 C 6 14, 10 9, 18 5" />
                <path d="M18 5 L 12 5" />
                <path d="M18 5 L 18 11" />
              </svg>
              <span className={styles.luckyText}>Feeling lucky?</span>
            </div>
          </div>

          <div className={styles.footerRightTop}>
            <div className={styles.footerNavCols}>
              <div className={styles.footerCol}>
                <p className={styles.footerColTitle}>Navigation</p>
                <Link href={APP_BASE}>How it works</Link>
                <Link href={`${APP_BASE}/memory`}>Memory</Link>
                <Link href={`${APP_BASE}/connections`}>Connections</Link>
                <Link href={`${APP_BASE}/automations`}>Automations</Link>
                <Link href={`${APP_BASE}/settings`}>Settings</Link>
              </div>
              <div className={styles.footerCol}>
                <p className={styles.footerColTitle}>Company</p>
                <Link href="https://github.com/meet447/koraku-cloud#readme" target="_blank" rel="noopener noreferrer">
                  Docs
                </Link>
                <Link href="/">About</Link>
                <Link href="/terms">Terms and Condition</Link>
                <Link href="/privacy">Privacy Policy</Link>
              </div>
            </div>
          </div>

          <div className={styles.footerBottom}>
            <p className={styles.footerCopyright}>© 2025 Koraku. All rights reserved.</p>
            <div className={styles.footerCtaMini}>
              <h4>
                AI moves fast.
                <br />
                <strong>Stay ahead with Koraku.</strong>
              </h4>
              <form
                className={styles.footerSubscribeRow}
                onSubmit={(e) => {
                  e.preventDefault();
                }}
              >
                <input type="email" name="email" placeholder="Enter email address" aria-label="Email address" />
                <button type="submit">Subscribe</button>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.footerWatermark} aria-hidden>
        <svg
          ref={watermarkSvgRef}
          viewBox="62 95 876 175"
          preserveAspectRatio="xMidYMid meet"
          xmlns="http://www.w3.org/2000/svg"
        >
          <text ref={watermarkTextRef} x="500" y="240" textAnchor="middle" fontSize="320">
            Koraku
          </text>
        </svg>
      </div>
    </section>
  );
}
