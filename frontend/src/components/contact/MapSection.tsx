import { ExternalLink } from 'lucide-react';
import styles from './MapSection.module.css';

// One address, used for the pin, the caption and the "open in Maps" link, so
// the three can never drift apart.
const ADDRESS = 'Ward 1, Uthayapuri Colony, Narasothipatti, Salem, Tamil Nadu 636004';
const PLACE_QUERY = `Sashainfinity, ${ADDRESS}`;

// `maps.google.com/maps?q=…&output=embed` looks like the obvious embed URL, but
// it answers with a 301 to the address below and that redirect carries
// `X-Frame-Options: SAMEORIGIN`. Chrome runs the frame-ancestors check on every
// hop of a redirect chain, not just the final document, so the iframe is killed
// before the map ever loads — a blank panel with no console error the user would
// think to look for. Pointing straight at the endpoint the redirect names skips
// the blocked hop: 200, no XFO, marker intact.
//
// The `pb` payload here is not the opaque place-ID blob this used to carry. It
// is `!2m1!1s<query>` — the address above, still readable in source, geocoded by
// Google on each load — plus zoom (`!6i16`) and language (`!3m1!1sen`).
const mapSrc = `https://www.google.com/maps/embed?origin=mfe&pb=!1m3!2m1!1s${encodeURIComponent(PLACE_QUERY)}!6i16!3m1!1sen!5m1!1sen`;
const mapLink = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(PLACE_QUERY)}`;

const MapSection = () => {
  return (
    <section className={styles.mapSection}>
      <div className="container">
        <h2 className={styles.title}>Find Us</h2>
        <p className={styles.subtitle}>{ADDRESS}</p>

        <div className={styles.mapCard}>
          <iframe
            src={mapSrc}
            className={styles.mapFrame}
            allowFullScreen
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            title={`Sashainfinity — ${ADDRESS}`}
          ></iframe>
        </div>

        <a
          className={styles.mapLink}
          href={mapLink}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open in Google Maps
          <ExternalLink aria-hidden="true" />
        </a>
      </div>
    </section>
  );
};

export default MapSection;
