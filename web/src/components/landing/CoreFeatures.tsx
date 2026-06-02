import { Inter } from "next/font/google";
import styles from "@/components/landing/CoreFeatures.module.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const NETWORK_IMG =
  "https://pub-f170a2592d2c4a1485466404c36807be.r2.dev/viktor/network.svg";
const FOLDER_IMG =
  "https://pub-f170a2592d2c4a1485466404c36807be.r2.dev/viktor/library%20icon.svg";

export function CoreFeatures() {
  return (
    <section className={`${styles.section} ${inter.className}`} aria-labelledby="core-features-title">
      <div className={styles.container}>
        <header>
          <p className={styles.badge}>Core Features</p>
          <h2 id="core-features-title" className={styles.title}>
            Built for Memory &amp; Momentum
          </h2>
          <p className={styles.subtitle}>
            Everything you need to go
            <br />
            from chat to lasting memory
          </p>
        </header>

        <div className={styles.grid}>
          <article className={`${styles.card} ${styles.card1}`}>
            <div className={styles.promptBox}>
              A companion that learns{" "}
              <span className={styles.blurText}>how you like to work</span>, remembers{" "}
              <span className={styles.blurText}>context from past chats</span>, and{" "}
              <span className={styles.blurText}>suggests helpful next steps</span> without
              overwriting your voice
            </div>
            <div className={styles.detailsPill}>
              <span className={styles.spark} aria-hidden>
                ✦
              </span>
              Add more context
            </div>
            <svg
              className={styles.cursor}
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
            <h3>Smart Memory Suggestions</h3>
          </article>

          <article className={`${styles.card} ${styles.card2}`}>
            <div className={styles.apiVisual}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                className={styles.networkImg}
                src={NETWORK_IMG}
                alt=""
                width={280}
                height={180}
              />
            </div>
            <h3>Connected Apps</h3>
          </article>

          <article className={`${styles.card} ${styles.card3}`}>
            <div className={styles.mesh} aria-hidden />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className={styles.folder} src={FOLDER_IMG} alt="" width={170} height={140} />
            <div className={styles.searchPill}>
              <svg
                className={styles.searchIcon}
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
              >
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
            <h3>Workspace Library</h3>
          </article>
        </div>
      </div>
    </section>
  );
}
