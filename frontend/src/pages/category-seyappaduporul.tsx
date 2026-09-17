import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sun, BookOpen, Users, Star } from "lucide-react";
import { api } from "@/api/axios";
import { CourseCard } from "@/components/course/course-card";
import { Course } from "@/types";
import styles from "@/styles/category-page.module.css";

// Maps the backend /courses list item to the local Course shape. The backend
// returns `title`/`description`/`price`/`level`/`rating`/`instructor.name`/
// `category`/`stats` — NOT the post_*/course_*/average_rating/display_name/
// categories[]/lessons[] fields an older API used. Reading the old names left
// values undefined and `undefined.toLowerCase()` / `.map()` threw during
// mapping, blanking the whole page whenever the category had courses.
const convertAPICourseToLocal = (apiCourse: any): Course => {
  return {
    id: apiCourse.id,
    post_title: apiCourse.title,
    post_excerpt: apiCourse.description,
    post_content: apiCourse.description || "",
    course_price: apiCourse.price,
    course_sale_price: apiCourse.sale_price || 0,
    course_price_type: apiCourse.price > 0 ? "paid" : "free",
    course_level: apiCourse.level,
    course_duration: `${apiCourse.stats?.duration || 0} minutes`,
    course_thumbnail: apiCourse.featured_image || "",
    course_intro_video: "",
    average_rating: apiCourse.rating || 0,
    total_reviews: 0,
    total_enrollments: apiCourse.stats?.students || 0,
    is_enrolled: apiCourse.is_enrolled || false,
    instructor: {
      id: apiCourse.instructor?.id,
      display_name: apiCourse.instructor?.name || "Instructor",
      user_email: "",
      user_login: (apiCourse.instructor?.name || "instructor").toLowerCase(),
      user_nicename: (apiCourse.instructor?.name || "instructor").toLowerCase(),
      user_registered: "2024-01-01",
      user_status: 0,
      is_active: true,
      is_verified: true,
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
      last_login: "2024-01-01",
      profile: {
        profile_photo: apiCourse.instructor?.avatar || "",
        bio: "",
        qualifications: [],
        experience_years: 0,
      },
    },
    categories: apiCourse.category
      ? [
          {
            id: 1,
            name: apiCourse.category,
            slug: String(apiCourse.category).toLowerCase(),
            description: "",
            created_at: "2024-01-01",
          },
        ]
      : [],
    slug: apiCourse.slug || "",
    lessons: Array.from({ length: apiCourse.stats?.lessons || 0 }) as any,
    created_at: apiCourse.created_at || "2024-01-01",
    updated_at: apiCourse.updated_at || "2024-01-01",
  } as unknown as Course;
};

export const SeyappaduporulPage = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalCourses: 0,
    totalStudents: 0,
    avgRating: 0,
  });

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoading(true);
        const response = await api.get("/courses", {
          params: {
            category: "seyappaduporul",
            limit: 100,
          },
        });

        const convertedCourses: Course[] = response.data.courses.map(
          convertAPICourseToLocal,
        );
        setCourses(convertedCourses);

        // Calculate stats
        const totalStudents = convertedCourses.reduce(
          (sum, course) => sum + course.total_enrollments,
          0,
        );
        const avgRating =
          convertedCourses.reduce(
            (sum, course) => sum + course.average_rating,
            0,
          ) / (convertedCourses.length || 1);

        setStats({
          totalCourses: convertedCourses.length,
          totalStudents,
          avgRating: Math.round(avgRating * 10) / 10,
        });
      } catch (error) {
        console.error("Error fetching Seyappaduporul courses:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  return (
    <div className={styles.categoryPage}>
      {/* Hero Section */}
      <section className={styles.hero}>
        <PageLayout
          header={
            <PageHeader>
              <div>
                <h1>Seyappaduporul</h1>
                <p className={styles.heroDescription}>
                  Seyappaduporul focuses on the practical application and
                  expression of knowledge through poetic forms, rhetoric, and
                  literary techniques. Master the art of composition, prosody,
                  and the technical aspects of Tamil literature.
                </p>
              </div>
            </PageHeader>
          }
          className="rd-screen rd-screen-category-seyappaduporul"
        >
          <div className={styles.heroIcon}>
            <Sun size={64} />
          </div>
          <div className={styles.heroStats}>
            <div className={styles.statItem}>
              <BookOpen size={24} />
              <div>
                <strong>{stats.totalCourses}</strong>
                <span>Courses</span>
              </div>
            </div>
            <div className={styles.statItem}>
              <Users size={24} />
              <div>
                <strong>{stats.totalStudents}</strong>
                <span>Students</span>
              </div>
            </div>
            <div className={styles.statItem}>
              <Star size={24} />
              <div>
                <strong>{stats.avgRating}</strong>
                <span>Avg Rating</span>
              </div>
            </div>
          </div>
        </PageLayout>
      </section>

      {/* About Section */}
      <section className={styles.about}>
        <div className={styles.container}>
          <h2>About Seyappaduporul</h2>
          <div className={styles.aboutContent}>
            <div className={styles.aboutText}>
              <p>
                <strong>Seyappaduporul</strong> (செய்யப்படுபொருள்) refers to the
                artificial or crafted subject matter in Tamil poetics. It deals
                with the technical and practical aspects of literary creation,
                including meter, rhyme, and rhetorical devices.
              </p>
              <p>Our courses in this category cover:</p>
              <ul>
                <li>Tamil prosody (யாப்பிலக்கணம்) and meter structures</li>
                <li>Rhetorical figures and literary devices (அணி இலக்கணம்)</li>
                <li>Poetic composition techniques and practices</li>
                <li>Grammar and linguistic structures in Tamil</li>
                <li>Practical exercises in writing Tamil poetry and prose</li>
              </ul>
            </div>
            <div className={styles.aboutImage}>
              <img
                src="https://images.unsplash.com/photo-1455390582262-044cdead277a?q=80&w=2073&auto=format&fit=crop"
                alt="Seyappaduporul - Tamil Poetics and Composition"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Courses Section */}
      <section className={styles.courses}>
        <div className={styles.container}>
          <h2>Available Courses</h2>
          {loading ? (
            <div className={styles.loading}>
              <div className={styles.spinner}></div>
              <p>Loading courses...</p>
            </div>
          ) : courses.length > 0 ? (
            <div className={styles.coursesGrid}>
              {courses.map((course) => (
                <CourseCard key={course.id} course={course} />
              ))}
            </div>
          ) : (
            <div className={styles.noCourses}>
              <Sun size={48} />
              <h3>No courses available yet</h3>
              <p>Check back soon for new Seyappaduporul courses!</p>
              <Link to="/courses" className={styles.browseButton}>
                Browse All Courses
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* CTA Section */}
      <section className={styles.cta}>
        <div className={styles.container}>
          <h2>Master the Art of Tamil Composition</h2>
          <p>
            Learn the technical mastery and practical skills needed to create
            beautiful Tamil literature through the systematic study of
            Seyappaduporul.
          </p>
          <div className={styles.ctaButtons}>
            <Link to="/courses" className={styles.primaryButton}>
              Browse All Courses
            </Link>
            <Link to="/about" className={styles.secondaryButton}>
              Learn More About Us
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
