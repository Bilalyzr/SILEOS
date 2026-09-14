import { useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { api } from '@/api/axios';
import styles from './AboutSections.module.css';

interface Instructor {
  id: number;
  name: string;
  email: string;
  profile_photo: string;
  description: string;
  expertise: string | null;
  course_count: number;
  rating: number;
}

const MentorsSection = () => {
  const [instructors, setInstructors] = useState<Instructor[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTopInstructors = async () => {
      try {
        setIsLoading(true);
        const response = await api.get('/users/instructors/top?limit=5');
        // Only ever show real instructors from the API. No fabricated fallback.
        setInstructors(Array.isArray(response.data) ? response.data : []);
      } catch (error) {
        console.error('Failed to fetch top instructors:', error);
        setInstructors([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTopInstructors();
  }, []);

  if (isLoading) {
    return (
      <section className={`${styles.section} ${styles.mentorSection}`}>
        <div className={styles.container}>
          <div className={styles.sectionTitle}>
            <p className={styles.preTitle}>OUR QUALIFIED PEOPLE MATTER</p>
            <h2>Top Class Mentors</h2>
          </div>
          <div className={styles.mentorGrid}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className={`${styles.mentorCard} ${styles.loading}`}>
                <div className={styles.profileImgSkeleton}></div>
                <div className={styles.nameSkeleton}></div>
                <div className={styles.ratingSkeleton}></div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  // No real instructors to show — hide the section rather than fake it.
  if (instructors.length === 0) {
    return null;
  }

  return (
    <section className={`${styles.section} ${styles.mentorSection}`}>
      <div className={styles.container}>
        <div className={styles.sectionTitle}>
          <p className={styles.preTitle}>OUR QUALIFIED PEOPLE MATTER</p>
          <h2>Top Class Mentors</h2>
        </div>
        <div className={styles.mentorGrid}>
          {instructors.map((instructor) => (
            <div key={instructor.id} className={styles.mentorCard}>
              <img
                src={instructor.profile_photo}
                alt={`Profile of ${instructor.name}`}
                className={styles.profileImg}
                onError={(e) => {
                  // Fallback to avatar if image fails to load
                  (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${instructor.name.replace(' ', '+')}&background=6366f1&color=fff&size=200`;
                }}
              />
              <h3>{instructor.name}</h3>
              <p className={styles.expertise}>{instructor.expertise || instructor.description}</p>
              <div className={styles.rating}>
                <Star size={15} aria-hidden />
                {instructor.rating.toFixed(1)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default MentorsSection;
