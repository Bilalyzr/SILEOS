import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Compass, Sparkles } from "lucide-react";
import { api } from "@/api/axios";
import { CourseCard } from "@/components/course/course-card";
import { Course } from "@/types";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

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

const PILLARS = [
  {
    code: "MP—01",
    title: "Sangam Classical Corpus",
    detail: "Ettuthokai and Pattuppattu anthologies examined through structural and ecological landscapes (Tinai).",
  },
  {
    code: "MP—02",
    title: "Akam & Puram Dialectics",
    detail: "The interior landscape of human devotion and the exterior architecture of civic valor and statecraft.",
  },
  {
    code: "MP—03",
    title: "Ethical & Dharmic Treatises",
    detail: "Tirukkural, Naladiyar, and didactic frameworks for moral clarity, governance, and relational harmony.",
  },
  {
    code: "MP—04",
    title: "Spatial & Hermeneutic Analysis",
    detail: "First-principles literary interpretation paired with interactive 3D spatial reconstructions.",
  },
];

export const MeiporulPage = () => {
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
            category: "meiporul",
            limit: 100,
          },
        });

        const convertedCourses: Course[] = (response.data?.courses || []).map(
          convertAPICourseToLocal,
        );
        setCourses(convertedCourses);

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
        console.error("Error fetching Meiporul courses:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  return (
    <div className="sympho-scope rd-screen rd-screen-category-meiporul min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—DIV.01"
        category="TAMIL TRIAD // மெய்ப்பொருள்"
        code="CLASSICAL DIVISION I"
        title="Meiporul — The True Essence of Reality."
        subtitle="Meiporul represents the foundational truth, authentic human experience, and essential subject matter in classical Tamil literary architecture. Dive into the timeless themes of love, ethics, and existence."
        metrics={[
          {
            value: String(stats.totalCourses),
            unit: "tracks",
            label: "Published Courses",
            code: "DIM—01",
          },
          {
            value: String(stats.totalStudents),
            unit: "scholars",
            label: "Enrolled Learners",
            code: "DIM—02",
          },
          {
            value: stats.avgRating > 0 ? stats.avgRating.toFixed(1) : "4.9",
            unit: "/ 5.0",
            label: "Average Rating",
            code: "DIM—03",
          },
        ]}
        actions={
          <>
            <SymphoButton to="/meiporul-ar" variant="copper">
              Open Meiporul 3D AR Studio
            </SymphoButton>
            <SymphoButton to="/courses" variant="ghost-dark">
              Browse Full Catalog
            </SymphoButton>
          </>
        }
      />

      {/* Triad Division Switcher Bar */}
      <div className="border-b border-ink-900/10 bg-limestone-50">
        <div className="mx-auto flex max-w-[1680px] flex-wrap items-center justify-between gap-4 px-gutter py-4">
          <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-500">
            <Compass className="h-3.5 w-3.5 text-copper-500" />
            <span>Classical Tamil Knowledge Triad</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/category/meiporul"
              className="rounded-pill bg-ink-900 px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-limestone-100"
            >
              01 · Meiporul (மெய்ப்பொருள்)
            </Link>
            <Link
              to="/category/utporul"
              className="rounded-pill border border-ink-900/15 bg-limestone-100 px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700 transition-colors hover:border-copper-500 hover:text-copper-500"
            >
              02 · Utporul (உட்பொருள்)
            </Link>
            <Link
              to="/category/seyappaduporul"
              className="rounded-pill border border-ink-900/15 bg-limestone-100 px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700 transition-colors hover:border-copper-500 hover:text-copper-500"
            >
              03 · Seyappaduporul (செய்யப்படுபொருள்)
            </Link>
          </div>
        </div>
      </div>

      {/* Monograph Treatise Section */}
      <section className="relative border-b border-ink-900/10 py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="MP—01"
            category="ARCHIVAL MONOGRAPH"
            code="EPISTEMIC FOUNDATION"
            title="About Meiporul"
            subtitle="Meiporul (மெய்ப்பொருள்) signifies the authentic substance beneath appearances — as immortalized in Tiruvalluvar's couplet: discerning the truth of a thing regardless of who speaks it."
          />

          <div className="mt-12 grid grid-cols-1 gap-10 lg:grid-cols-12">
            <div className="lg:col-span-7">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {PILLARS.map((pillar) => (
                  <div
                    key={pillar.code}
                    className="sheet-frame flex flex-col justify-between bg-limestone-50/90 p-6 transition-colors hover:border-copper-500/40"
                  >
                    <div>
                      <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                        {pillar.code}
                      </span>
                      <h3 className="mt-2 font-display text-xl font-light text-ink-900">
                        {pillar.title}
                      </h3>
                      <p className="mt-2 text-sm leading-relaxed text-ink-600">
                        {pillar.detail}
                      </p>
                    </div>
                    <div className="mt-6 border-t border-ink-900/10 pt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                      Primary Division I // Verified Syllabus
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:col-span-5">
              <div className="sheet-frame overflow-hidden bg-ink-950 text-limestone-100">
                <div className="relative aspect-[16/10] overflow-hidden border-b border-limestone-100/10">
                  <img
                    src="https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?q=80&w=2070&auto=format&fit=crop"
                    alt="Meiporul - Tamil Literature and Poetry"
                    className="h-full w-full object-cover opacity-80 transition-transform duration-700 hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/30 to-transparent" />
                  <div className="absolute bottom-4 left-5 right-5 flex items-end justify-between">
                    <div>
                      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-copper-400">
                        KURAL 423 // EPISTEMIC AXIOM
                      </span>
                      <p className="mt-1 font-display text-2xl font-light italic text-limestone-50">
                        மெய்ப்பொருள் காண்பது அறிவு
                      </p>
                    </div>
                  </div>
                </div>
                <div className="p-6">
                  <p className="text-sm leading-relaxed text-limestone-200/80">
                    &ldquo;To discern the true essence in whatever is spoken, by whomsoever it is spoken — that alone is true wisdom.&rdquo;
                  </p>
                  <div className="mt-5 flex items-center justify-between border-t border-limestone-100/10 pt-4">
                    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-limestone-300/60">
                      3D Spatial Companion Available
                    </span>
                    <Link
                      to="/meiporul-ar"
                      className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-copper-400 hover:text-copper-300"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      Launch AR Viewer →
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Courses Section */}
      <section className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="MP—02"
            category="CURRICULUM LEDGER"
            code={`${courses.length} TRACKS`}
            title="Available Courses"
            subtitle="Structured studio tracks exploring classical Tamil literature, ethics, and philosophical analysis."
          />

          <div className="mt-12">
            {loading ? (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {[1, 2, 3].map((n) => (
                  <div
                    key={n}
                    className="sheet-frame h-96 animate-pulse bg-limestone-50 p-6"
                  />
                ))}
              </div>
            ) : courses.length > 0 ? (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {courses.map((course) => (
                  <CourseCard key={course.id} course={course} />
                ))}
              </div>
            ) : (
              <div className="sheet-frame mx-auto max-w-2xl bg-limestone-50 p-12 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-ink-900/15 bg-limestone-100 text-copper-500">
                  <BookOpen className="h-6 w-6" />
                </div>
                <span className="mt-4 block font-mono text-[10px] uppercase tracking-[0.18em] text-copper-500">
                  ARCHIVE STATUS // COHORT IN PREPARATION
                </span>
                <h3 className="mt-2 font-display text-3xl font-light text-ink-900">
                  No courses available yet
                </h3>
                <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
                  Check back soon for new Meiporul courses, or explore our interactive 3D AR models and full course catalog right now.
                </p>
                <div className="mt-8 flex flex-wrap justify-center gap-3">
                  <SymphoButton to="/courses" variant="primary">
                    Browse All Courses
                  </SymphoButton>
                  <SymphoButton to="/meiporul-ar" variant="outline">
                    Explore Meiporul 3D AR
                  </SymphoButton>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—TRIAD // 01"
        eyebrow="CLASSICAL TAMIL SCHOLARSHIP"
        title="Discover the beauty of Tamil literature."
        description="Immerse yourself in the rich tradition of Meiporul and explore authentic emotions, timeless ethics, and profound wisdom."
        primaryLabel="Browse All Courses"
        primaryTo="/courses"
        secondaryLabel="Learn More About Us"
        secondaryTo="/about"
      />
    </div>
  );
};
