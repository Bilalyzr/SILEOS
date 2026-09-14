import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import styles from './AboutSections.module.css';

const CTASection = () => {
  return (
    <section className={`${styles.section} ${styles.ctaSection}`}>
      <div className={styles.container}>
        <p className={styles.preTitle}>Join Us In Transforming Education</p>
        <h2>Become Part of the Movement</h2>
        <p>
          SashaInfinity isn't just building a platform—we're building a movement to reshape how the
          next generation learns. If you're a parent, student, educator, or partner who believes in the
          power of immersive learning, we welcome you to join us on this journey.
        </p>
        <Link to="/courses" className={styles.btn}>
          Explore. Engage. Excel.
          <ArrowRight size={18} aria-hidden />
        </Link>
      </div>
    </section>
  );
};

export default CTASection;
