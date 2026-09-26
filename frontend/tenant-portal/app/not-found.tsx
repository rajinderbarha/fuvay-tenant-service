import Link from "next/link";
import styles from "./error-state.module.css";

export default function NotFound() {
  return <main className={styles.viewport}>
    <section className={styles.card} aria-labelledby="not-found-title">
      <span className={styles.code}>404</span>
      <h1 id="not-found-title">This page is not available</h1>
      <p>The link may be old or the record may have moved. Open your bookings workspace to continue safely.</p>
      <div className={styles.actions}>
        <Link className={styles.primary} href="/home-services/bookings-jobs">Open bookings &amp; jobs</Link>
        <Link className={styles.secondary} href="/dashboard">Back to dashboard</Link>
      </div>
    </section>
  </main>;
}
