import { Boxes, Building2, Rocket, ArrowUpRight } from 'lucide-react';
import styles from './AboutSections.module.css';

const offerings = [
  {
    icon: Boxes,
    chip: styles.chipCyan,
    accent: styles.accentCyan,
    title: 'Metaverse Learning Platform',
    text: 'A unified AR/VR learning ecosystem with interactive 3D models, simulations, and virtual classrooms.',
    tag: 'AR / VR',
  },
  {
    icon: Building2,
    chip: styles.chipNavy,
    accent: styles.accentNavy,
    title: 'Hybrid Tutoring Centers',
    text: 'Physical + digital centers offering structured academic support with real-world applications.',
    tag: 'Phygital',
  },
  {
    icon: Rocket,
    chip: '',
    accent: styles.accentOrange,
    title: 'Skill Development Courses',
    text: 'On-demand learning for future-ready skills in collaboration with industry experts.',
    tag: 'Future-ready',
  },
];

const CoreOfferingsSection = () => {
  return (
    <section className={`${styles.section} ${styles.offeringsSection}`}>
      <span className={styles.shapeDots} aria-hidden />
      <div className={styles.container}>
        <div className={styles.sectionTitle}>
          <p className={styles.preTitle}>What We Do</p>
          <h2>Our Core Offerings</h2>
        </div>
        <div className={styles.featuresGrid}>
          {offerings.map((item, i) => {
            const Icon = item.icon;
            return (
              <article key={item.title} className={`${styles.featureItem} ${item.accent}`}>
                <span className={styles.featureNumber} aria-hidden>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div className={styles.featureHead}>
                  <span className={`${styles.iconChip} ${item.chip}`}>
                    <Icon size={26} aria-hidden />
                  </span>
                  <span className={styles.featureTag}>{item.tag}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
                <span className={styles.featureArrow} aria-hidden>
                  <ArrowUpRight size={18} />
                </span>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default CoreOfferingsSection;
