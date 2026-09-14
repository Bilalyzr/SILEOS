import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import styles from './AboutSections.module.css';

const WhoWeAreSection = () => {
  return (
    <section className={`${styles.section} ${styles.whoWeAreHero}`}>
      <div className={styles.container}>
        <div className={styles.contentWrapper}>
          <div className={styles.textContent}>
            <p className={styles.preTitle}>Who We Are</p>
            <h2>
              The Leading Global <span className={styles.highlightOrange}>Marketplace</span> For Learning And <span className={styles.highlightBlue}>Instruction</span>
            </h2>
            <p>
              SashaInfinity is an edtech reimagining the future of learning through immersive AR/VR experiences,
              hybrid tutoring centers, and data-driven personalized education for K12 and college students across India.
            </p>
            <Link to="/courses" className={styles.btn}>
              Explore Courses
              <ArrowRight size={18} aria-hidden />
            </Link>
          </div>
          <div className={styles.imageContent}>
            <span className={styles.shapeDots} aria-hidden />
            <span className={styles.shapeRing} aria-hidden />
            <img
              src="/assets/images/Untitled_design__2__1_-removebg-preview-1.png"
              onError={(e) => { const target = e.target as HTMLImageElement; target.src = 'https://sashainfinity.com/wp-content/uploads/2025/06/Copy_of_sasha_SISF_PITCH-removebg-preview-e1751282895734.png' }}
              alt="Children happily learning with VR headsets"
            />
          </div>
        </div>
      </div>
    </section>
  );
};

export default WhoWeAreSection;
