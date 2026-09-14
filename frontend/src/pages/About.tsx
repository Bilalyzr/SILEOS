import PageTitleSection from '@/components/about/PageTitleSection';
import WhoWeAreSection from '@/components/about/WhoWeAreSection';
import StatsSection from '@/components/about/StatsSection';
import CoreOfferingsSection from '@/components/about/CoreOfferingsSection';
import MissionSection from '@/components/about/MissionSection';
import MentorsSection from '@/components/about/MentorsSection';
import CTASection from '@/components/about/CTASection';
import styles from '@/components/about/AboutSections.module.css';

export function AboutPage() {
  return (
    <div className={styles.about} style={{ position: 'relative', zIndex: 1, backgroundColor: '#fff' }}>
      <PageTitleSection />
      <WhoWeAreSection />
      <StatsSection />
      <CoreOfferingsSection />
      <MissionSection />
      <MentorsSection />
      <CTASection />
    </div>
  );
}
