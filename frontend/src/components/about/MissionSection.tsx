import { Puzzle, Target } from 'lucide-react';
import styles from './AboutSections.module.css';

const MissionSection = () => {
  return (
    <section className={`${styles.section} ${styles.problemMissionSection}`}>
      <div className={styles.container}>
        <div className={styles.contentWrapper}>
          <div className={styles.textContent}>
            <span className={`${styles.iconChip} ${styles.chipNavy}`}>
              <Puzzle size={26} aria-hidden />
            </span>
            <p className={styles.preTitle}>The Problem We're Solving</p>
            <h2>Bridging the Educational Divide</h2>
            <p>
              Over 80% of students in India's smaller cities lack access to quality math education.
              We're here to change that through interactive, contextual, and immersive learning models.
            </p>
          </div>
          <div className={styles.textContent}>
            <span className={styles.iconChip}>
              <Target size={26} aria-hidden />
            </span>
            <p className={styles.preTitle}>Our Mission</p>
            <h2>Accessible, Engaging Education</h2>
            <p>
              To make quality math and science education engaging, accessible, and effective by leveraging
              immersive technologies and hybrid tutoring, empowering learners regardless of geography.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default MissionSection;
