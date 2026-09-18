import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useSEO } from "@/hooks/use-seo";
import { api } from "@/api/axios";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { getMediaUrl } from "@/utils/media";
import { IndependenceDayPopup } from "@/components/promotional/IndependenceDayPopup";
import { OfferTimerWidget } from "@/components/promotional/OfferTimerWidget";
import "./home.css";
import "./home-modern.css";

type HomeStats = { courses: number; labs: number; subjects: number };

function useHomeStats() {
  const [stats, setStats] = useState<HomeStats | null>(null);
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const [coursesRes, labsRes] = await Promise.all([
          api.get("/courses/?page=1&page_size=100"),
          api.get("/virtual-labs"),
        ]);
        if (!live) return;
        const courses = coursesRes.data?.courses ?? [];
        const cats = new Set(
          courses.map((c: any) => (c.category || "").trim()).filter(Boolean),
        );
        setStats({
          courses: coursesRes.data?.total ?? courses.length,
          labs: (labsRes.data?.labs ?? []).length,
          subjects: cats.size,
        });
      } catch {
        /* stats stay hidden on failure — never fabricated */
      }
    })();
    return () => { live = false; };
  }, []);
  return stats;
}

function HeroSection({ stats }: { stats: HomeStats | null }) {
  return (
    <section className="rd-home-hero hm-hero" id="home" data-testid="hero-section">
      <div className="hm-hero-copy">
        <span className="rd-eyebrow hm-fade" style={{ animationDelay: "80ms" }}>
            Learn <i aria-hidden>•</i> Practice <i aria-hidden>•</i> Build
          </span>
        <h1>
          Your next chapter
          <br />
          starts with <em>curiosity.</em>
        </h1>
        <p>
          Explore courses, put ideas to the test in interactive labs, and build
          skills you can use in the real world.
        </p>
        <div className="rd-heading-actions">
          <Link to="/courses" className="rd-home-primary">
            Explore courses <i className="fa-solid fa-arrow-right" />
          </Link>
          <Link to="/labs" className="rd-home-secondary">
            Try a learning lab
          </Link>
        </div>
        <div className="rd-home-paths">
          <Link to="/categories">Explore subjects</Link>
          <Link to="/internships">Find an internship</Link>
          <Link to="/library">Read and discover</Link>
        </div>
      </div>
      <div className="rd-home-guide">
        <img src="/design/sasha-guide.png" alt="Sasha learning guide" />
        <div>
          <span>LEARN BY DOING</span>
          <strong>
            Make a prediction.
            <br />
            Run an experiment.
          </strong>
          <Link to="/labs">Open the lab library →</Link>
        </div>
        {stats && (
          <div className="hm-hero-chips" aria-label="Platform highlights">
            <span className="hm-chip">{stats.courses}+ courses</span>
            <span className="hm-chip">{stats.labs}+ interactive labs</span>
            <span className="hm-chip">{stats.subjects} subjects</span>
          </div>
        )}
      </div>
    </section>
  );
}

function StatsBar() {
  return (
    <section
      className="astra-home-paths"
      data-testid="stats-bar"
      aria-label="Learning opportunities"
    >
      {[
        { to: "/courses", title: "Learn", label: "Explore courses" },
        { to: "/labs", title: "Experiment", label: "Open learning labs" },
        { to: "/library", title: "Read", label: "Browse the digital library" },
        {
          to: "/internships",
          title: "Build experience",
          label: "Find an internship",
        },
      ].map((item) => (
        <Link key={item.to} to={item.to}>
          <strong>{item.title}</strong>
          <span>{item.label}</span>
        </Link>
      ))}
    </section>
  );
}

function ScrollStackSection() {
  const cards = [
    {
      icon: "fa-solid fa-vr-cardboard",
      title: "Immersive AR/VR Learning",
      desc: "Experience mathematics like never before with our cutting-edge Augmented and Virtual Reality modules. Visualize complex concepts in 3D and interact with mathematical models in real-time.",
      stats: [
        { n: "100+", l: "AR Models" },
        { n: "3D", l: "Visualization" },
        { n: "Real-time", l: "Interaction" },
      ],
    },
    {
      icon: "fa-solid fa-brain",
      title: "Personalized Learning Paths",
      desc: "Our AI-driven platform creates customized learning journeys for each student. Adaptive quizzes, progress tracking, and data-driven insights ensure every learner reaches their full potential.",
      stats: [
        { n: "AI", l: "Powered" },
        { n: "50+", l: "Students" },
        { n: "98%", l: "Satisfaction" },
      ],
    },
    {
      icon: "fa-solid fa-school",
      title: "Hybrid Tutoring Centers",
      desc: "Combining the best of online and offline education. Our hybrid centers in tier 2 and tier 3 cities provide hands-on guidance with the flexibility of digital learning tools.",
      stats: [
        { n: "5+", l: "Expert Tutors" },
        { n: "70+", l: "Lessons" },
        { n: "24/7", l: "Support" },
      ],
    },
    {
      icon: "fa-solid fa-chart-line",
      title: "Analytics & Data Science",
      desc: "Go beyond traditional math education with our analytics courses. Learn data science, visualization, and real-world problem solving skills that prepare you for the future of work.",
      stats: [
        { n: "10+", l: "Courses" },
        { n: "Pro", l: "Certification" },
        { n: "100+", l: "Videos" },
      ],
    },
  ];

  return (
    <section
      className="sasha-scroll-stack-section"
      data-testid="scroll-stack-section"
    >
      <div className="scroll-stack-header" data-glass="content">
        <div className="section-label" style={{ justifyContent: "center" }}>
          Why SashaInfinity
        </div>
        <h2>What Makes Us Different</h2>
        <p>
          Discover how we're transforming education with cutting-edge technology
          and personalized learning.
        </p>
      </div>
      <div className="astra-feature-grid">
        {cards.map((card, i) => (
          <article key={i}>
            <div className="scroll-stack-card-content">
              <div className="card-icon">
                <i className={card.icon}></i>
              </div>
              <h3>{card.title}</h3>
              <p>{card.desc}</p>
              <div className="card-stats">
                {card.stats.map((s, j) => (
                  <div key={j}>
                    <div className="card-stat-num">{s.n}</div>
                    <div className="card-stat-label">{s.l}</div>
                  </div>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function AboutSection() {
  const morphIdx = 0;
  const texts = [
    "The Place Where You Can Achieve",
    "Immersive AR/VR Learning",
    "Personalized Education",
    "Data-Driven Learning Paths",
    "Hybrid Tutoring Centers",
  ];

  return (
    <section className="sasha-about-section" id="about">
      <div className="sasha-container">
        <div className="about-grid">
          <div className="about-visual">
            <div className="about-visual-placeholder">
              <div className="about-exp-badge">
                <div className="year">2+</div>
                <div className="label">Years</div>
              </div>
              <img
                src="/assets/images/Untitled_design__2__1_-removebg-preview-1.png"
                alt="About Sashainfinity"
              />
            </div>
          </div>
          <div className="about-content">
            <div className="section-label">Get To Know About Us</div>
            <div className="morph-container">
              <h2 className="morph-text-display" key={morphIdx}>
                {texts[morphIdx]}
              </h2>
            </div>
            <p>
              Sashainfinity is a pioneering EdTech Company transforming
              mathematics education for students in tier 2 and tier 3 cities.
              With cutting-edge AR/VR integration, hybrid tutoring centers and
              analytics courses.
            </p>
            <p>
              Personalized Tutoring by using customized and dedicated LMS module
              to actively engage students with quizzes and engaging content.
            </p>
            <ul className="feature-list">
              <li>
                <span className="icon">
                  <i className="fa-solid fa-vr-cardboard"></i>
                </span>{" "}
                Immersive AR/VR Math Learning
              </li>
              <li>
                <span className="icon">
                  <i className="fa-solid fa-brain"></i>
                </span>{" "}
                Personalized Interactive Quizzes
              </li>
              <li>
                <span className="icon">
                  <i className="fa-solid fa-school"></i>
                </span>{" "}
                Hybrid Tutoring Centers
              </li>
              <li>
                <span className="icon">
                  <i className="fa-solid fa-chart-line"></i>
                </span>{" "}
                Analytics Courses for Everyone
              </li>
              <li>
                <span className="icon">
                  <i className="fa-solid fa-route"></i>
                </span>{" "}
                Custom Learning Paths
              </li>
            </ul>
            <div className="about-stats">
              <div className="about-stat">
                <div className="icon-wrap">
                  <i className="fa-solid fa-headset"></i>
                </div>
                <div className="stat-info">
                  <strong>5+ Expert Tutors</strong>
                  <span>Dedicated mentors</span>
                </div>
              </div>
              <div className="about-stat">
                <div className="icon-wrap">
                  <i className="fa-solid fa-file-alt"></i>
                </div>
                <div className="stat-info">
                  <strong>70+ Top Lessons</strong>
                  <span>Quality content</span>
                </div>
              </div>
              <div className="about-stat">
                <div className="icon-wrap">
                  <i className="fa-solid fa-user-graduate"></i>
                </div>
                <div className="stat-info">
                  <strong>50+ Students</strong>
                  <span>And growing</span>
                </div>
              </div>
              <div className="about-stat">
                <div className="icon-wrap">
                  <i className="fa-solid fa-video"></i>
                </div>
                <div className="stat-info">
                  <strong>100+ Pro Videos</strong>
                  <span>Learn anywhere</span>
                </div>
              </div>
            </div>
            <Link
              to="/courses"
              className="hero-btn hero-btn-fill"
              style={{ marginTop: 28 }}
            >
              Discover More <i className="fa-solid fa-arrow-right"></i>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function CategoriesSection() {
  return (
    <section className="sasha-categories-section" id="categories">
      <div className="sasha-container">
        <div className="categories-top">
          <div>
            <div className="section-label">Unique Online Courses</div>
            <h2>Browse By Categories</h2>
            <Link
              to="/courses"
              className="hero-btn hero-btn-fill"
              style={{ marginTop: 24 }}
            >
              All Categories <i className="fa-solid fa-arrow-right"></i>
            </Link>
          </div>
          <div className="categories-grid">
            <Link to="/courses/meiporul" className="category-card">
              <div className="category-icon">
                <i className="fa-solid fa-rocket"></i>
              </div>
              <h3>Meiporul</h3>
              <span>06 Courses</span>
            </Link>
            <Link to="/courses" className="category-card">
              <div className="category-icon">
                <i className="fa-solid fa-sun"></i>
              </div>
              <h3>Seyappaduporul</h3>
              <span>08 Courses</span>
            </Link>
            <Link to="/courses" className="category-card">
              <div className="category-icon">
                <i className="fa-solid fa-lightbulb"></i>
              </div>
              <h3>Utporul</h3>
              <span>13 Courses</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function CardSwapSection() {
  const activeIdx = 0;
  const cards = [
    {
      icon: "fa-solid fa-vr-cardboard",
      title: "AR/VR Learning",
      desc: "Immersive augmented and virtual reality experiences that bring complex concepts to life in 3D.",
      tag: "Immersive",
    },
    {
      icon: "fa-solid fa-brain",
      title: "AI Personalized Paths",
      desc: "Smart learning paths powered by AI that adapt to each student's pace, strengths and areas to improve.",
      tag: "AI Powered",
    },
    {
      icon: "fa-solid fa-chalkboard-user",
      title: "Hybrid Tutoring",
      desc: "The best of online and offline education combined. Expert tutors guide you through every concept.",
      tag: "Hybrid",
    },
    {
      icon: "fa-solid fa-chart-line",
      title: "Analytics & Data",
      desc: "Track progress with detailed analytics dashboards. Data-driven insights help optimize the learning journey.",
      tag: "Data Driven",
    },
  ];

  return (
    <section className="sasha-card-swap-section">
      <div className="sasha-container">
        <div className="card-swap-layout">
          <div className="card-swap-content">
            <div className="section-label">What We Offer</div>
            <h2>Discover Our Learning Programs</h2>
            <p>
              From AR/VR immersive lessons to personalized tutoring, explore
              programs designed to make learning engaging, effective, and fun
              for every student.
            </p>
            <Link to="/courses" className="hero-btn hero-btn-fill">
              View All Programs <i className="fa-solid fa-arrow-right"></i>
            </Link>
          </div>
          <div className="card-swap-display">
            {cards.map((card, i) => (
              <div
                key={i}
                className={`swap-card-item ${i === activeIdx ? "active" : ""}`}
              >
                <div className="swap-card-icon">
                  <i className={card.icon}></i>
                </div>
                <h3>{card.title}</h3>
                <p>{card.desc}</p>
                <div className="swap-card-footer">
                  <span className="swap-card-tag">{card.tag}</span>
                  <div className="swap-card-arrow">
                    <i className="fa-solid fa-arrow-right"></i>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function TestimonialSection() {
  const [current, setCurrent] = useState(0);
  const testimonials = [
    {
      text: "Hi, this is Annamalai Venkatachalam. I have completed the Sasha Infinity course, which had excellent content and wonderful teaching methods.",
      author: "Annamalai Venkatachalam",
      role: "Student",
    },
    {
      text: "I am very satisfied with this course. Topics are very clear and the teaching methodology is excellent.",
      author: "Durkka P",
      role: "Student",
    },
  ];

  return (
    <section className="sasha-testimonial-section">
      <div className="sasha-container">
        <div className="section-header">
          <div className="section-label" style={{ justifyContent: "center" }}>
            Testimonials
          </div>
          <h2>What Students Say</h2>
        </div>
        <div className="testimonial-card">
          <div className="quote-icon">
            <i className="fa-solid fa-quote-left"></i>
          </div>
          <div className="testimonial-stars">
            {[...Array(5)].map((_, i) => (
              <i key={i} className="fa-solid fa-star"></i>
            ))}
          </div>
          <p className="testimonial-text" key={current}>
            {testimonials[current].text}
          </p>
          <div className="testimonial-author">
            {testimonials[current].author}
          </div>
          <div className="testimonial-role">{testimonials[current].role}</div>
          <div className="testimonial-nav">
            <button
              aria-label="Previous testimonial"
              onClick={() =>
                setCurrent(
                  (current - 1 + testimonials.length) % testimonials.length,
                )
              }
            >
              <i className="fa-solid fa-chevron-left"></i>
            </button>
            <button
              aria-label="Next testimonial"
              onClick={() => setCurrent((current + 1) % testimonials.length)}
            >
              <i className="fa-solid fa-chevron-right"></i>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

interface TopInstructor {
  id: number;
  name: string;
  photo?: string;
  role: string;
  color: string;
}

// NOTE: this section used to seed itself with four invented instructors
// ("Mathematics Lead", "Tech Lead", …) so it never rendered blank. They were
// indistinguishable from real staff and stayed on screen whenever the API
// returned nothing or errored — which is what "instructors are not listing
// correctly" was. The section now shows only real instructors and hides
// itself entirely when there are none.

function TeamSection() {
  const [instructors, setInstructors] = useState<TopInstructor[]>([]);
  const [loaded, setLoaded] = useState(false);
  const gridRef = useRef<HTMLDivElement>(null);

  // Cards start hidden (opacity:0 in CSS) and are normally revealed by the
  // page-level IntersectionObserver, which only runs at mount. Because these
  // cards re-render after the API resolves (new DOM nodes the observer never
  // sees), reveal them here whenever the list changes so they never stay blank.
  useEffect(() => {
    gridRef.current
      ?.querySelectorAll<HTMLElement>(".team-card")
      .forEach((node, i) => {
        node.style.transition = "opacity 0.6s ease, transform 0.6s ease";
        node.style.transitionDelay = `${(i % 4) * 0.08}s`;
        requestAnimationFrame(() => {
          node.style.opacity = "1";
          node.style.transform = "translateY(0)";
        });
      });
  }, [instructors]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Top instructors ranked by course count + rating (see users router).
        const res = await api.get("/users/instructors/top?limit=4");
        const list = Array.isArray(res.data)
          ? res.data
          : res.data?.instructors || [];
        if (cancelled) return;
        const colors = ["c1", "c2", "c3", "c4"];
        setInstructors(
          list.slice(0, 4).map((ins: any, i: number) => ({
            id: ins.id,
            name: ins.name || "Instructor",
            photo: getMediaUrl(ins.profile_photo) || undefined,
            role:
              ins.expertise ||
              (ins.course_count
                ? `${ins.course_count} Course${ins.course_count > 1 ? "s" : ""}`
                : "Expert Instructor"),
            color: colors[i % colors.length],
          })),
        );
      } catch {
        // Leave the list empty — better an absent section than invented people.
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Nothing real to show: render nothing rather than a header over an empty
  // grid (or, as before, over fabricated instructors).
  if (loaded && instructors.length === 0) return null;

  return (
    <section className="sasha-team-section">
      <div className="sasha-container">
        <div className="section-header">
          <div className="section-label" style={{ justifyContent: "center" }}>
            Our Qualified People Matter
          </div>
          <h2>Top Class Instructors</h2>
        </div>
        <div className="team-grid" ref={gridRef}>
          {instructors.map((t, i) => {
            const card = (
              <>
                <div className={`team-card-img ${t.color}`}>
                  {t.photo ? (
                    <img
                      src={t.photo}
                      alt={t.name}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        position: "absolute",
                        inset: 0,
                      }}
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display =
                          "none";
                      }}
                    />
                  ) : (
                    <i className="fa-solid fa-user"></i>
                  )}
                </div>
                <div className="team-card-info">
                  <div className="role">{t.role}</div>
                  <h4>{t.name}</h4>
                </div>
              </>
            );
            return t.id ? (
              <Link to={`/instructor/${t.id}`} className="team-card" key={i}>
                {card}
              </Link>
            ) : (
              <div className="team-card" key={i}>
                {card}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className="sasha-cta-section">
      <div className="sasha-container">
        <div className="cta-box">
          <div>
            <h2>
              Join Us &amp; Spread
              <br />
              Experiences
            </h2>
            <p>
              Join SashaInfinity and experience the future of education with
              AR/VR powered courses, personalized learning, and expert guidance.
            </p>
          </div>
          <Link to="/register" className="hero-btn hero-btn-fill">
            Become an Instructor <i className="fa-solid fa-arrow-right"></i>
          </Link>
        </div>
      </div>
    </section>
  );
}

interface BlogPreview {
  slug: string;
  title: string;
  tag: string;
  date: string;
  author: string;
  image?: string;
  gradient: string;
  icon: string;
}

const BLOG_GRADIENTS = [
  "linear-gradient(135deg, #667EEA, #764BA2)",
  "linear-gradient(135deg, #F093FB, #F5576C)",
  "linear-gradient(135deg, #4FACFE, #00F2FE)",
];
const BLOG_ICONS = [
  "fa-solid fa-newspaper",
  "fa-solid fa-feather",
  "fa-solid fa-book-open",
];

// NOTE: three hardcoded posts used to seed this section, with fixed
// "Nov 21, 2025" dates and slugs that may not exist. They rendered as real
// articles whenever the blog API was empty or failing, and clicking one led
// to a 404. Real posts only now — the section hides itself when there are none.

const formatBlogDate = (iso?: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

function BlogPreviewSection() {
  const [blogs, setBlogs] = useState<BlogPreview[]>([]);
  const [loaded, setLoaded] = useState(false);
  const gridRef = useRef<HTMLDivElement>(null);

  // Reveal blog cards whenever the list changes (see TeamSection for why the
  // page-level observer isn't enough for async-loaded cards).
  useEffect(() => {
    gridRef.current
      ?.querySelectorAll<HTMLElement>(".blog-card")
      .forEach((node, i) => {
        node.style.transition = "opacity 0.6s ease, transform 0.6s ease";
        node.style.transitionDelay = `${(i % 3) * 0.08}s`;
        requestAnimationFrame(() => {
          node.style.opacity = "1";
          node.style.transform = "translateY(0)";
        });
      });
  }, [blogs]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Public blog listing, newest first (see blog router).
        const res = await api.get("/blog/?limit=3");
        const list = Array.isArray(res.data)
          ? res.data
          : res.data?.posts || res.data?.items || [];
        if (cancelled) return;
        setBlogs(
          list.slice(0, 3).map((p: any, i: number) => {
            const author =
              typeof p.author === "string"
                ? p.author
                : p.author?.name || p.author_name || "Admin";
            return {
              slug: p.slug,
              title: p.title,
              tag: p.category || "Blog",
              date: formatBlogDate(p.post_date || p.created_at),
              author,
              image: getMediaUrl(p.featured_image) || undefined,
              gradient: BLOG_GRADIENTS[i % BLOG_GRADIENTS.length],
              icon: BLOG_ICONS[i % BLOG_ICONS.length],
            };
          }),
        );
      } catch {
        // Leave empty — a missing section beats fake articles that 404.
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loaded && blogs.length === 0) return null;

  return (
    <section className="sasha-blog-section">
      <div className="sasha-container">
        <div className="section-header">
          <div className="section-label" style={{ justifyContent: "center" }}>
            Always Smart To Hear News
          </div>
          <h2>Latest News &amp; Blog</h2>
        </div>
        <div className="blog-grid" ref={gridRef}>
          {blogs.map((b, i) => (
            <Link
              to={`/blog/${b.slug}`}
              className="blog-card"
              key={b.slug || i}
            >
              <div
                className="blog-card-thumb"
                style={{
                  background: b.gradient,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {b.image ? (
                  <img
                    src={b.image}
                    alt={b.title}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      position: "absolute",
                      inset: 0,
                    }}
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display =
                        "none";
                    }}
                  />
                ) : (
                  <i className={b.icon}></i>
                )}
              </div>
              <div className="blog-card-body">
                <span className="blog-card-tag">{b.tag}</span>
                <h4>{b.title}</h4>
                <div className="blog-card-meta">
                  <span>
                    <i className="fa-solid fa-user"></i> {b.author}
                  </span>
                  {b.date && (
                    <span>
                      <i className="fa-solid fa-calendar"></i> {b.date}
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

function PartnersSection() {
  return (
    <section className="sasha-partners-section">
      <div className="sasha-container">
        <div className="partners-track">
          <img
            src="/assets/images/sif-logo-png-e1750397156954.png"
            alt="Sona Incubations"
          />
          <img
            src="/assets/images/blue-horizontal-3-scaled.png"
            alt="StartupTN"
          />
          <img
            src="/assets/images/Trueline-lOGO-1-scaled-e1750400158902.png"
            alt="Trueline Research"
          />
        </div>
      </div>
    </section>
  );
}

// M-12: Home footer's onSubmit was e.preventDefault() only — the newsletter
// form never called anything. POST /blog/newsletter/subscribe already
// existed (blog.py:721) with zero UI callers. Exported (not just used
// locally) so it can be unit-tested without mounting the rest of this
// THREE.js-heavy page.
export function NewsletterSection() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isValidEmail = (value: string) =>
    /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidEmail(email)) {
      toast.error("Please enter a valid email address");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/blog/newsletter/subscribe", { email });
      toast.success("Subscribed! Check your inbox for a welcome email.");
      setEmail("");
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail || "Failed to subscribe. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="sasha-newsletter-section">
      <div className="sasha-container">
        <h3>Stay Updated</h3>
        <p>Subscribe to our newsletter for the latest updates and courses.</p>
        <form className="newsletter-form" onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={submitting}
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Subscribing…" : "Subscribe"}
          </button>
        </form>
      </div>
    </section>
  );
}


function FeaturedCoursesSection() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    api
      .get("/courses/?page=1&page_size=4&sort=latest")
      .then((r) => { if (live) setCourses(r.data?.courses ?? []); })
      .catch(() => {})
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);
  return (
    <section className="hm-section" aria-labelledby="hm-featured-title">
      <div className="hm-section-head">
        <div>
          <span className="hm-kicker">Featured courses</span>
          <h2 id="hm-featured-title">Learn from real, hands-on courses</h2>
        </div>
        <Link to="/courses" className="hm-ghost-link">
          View all courses <span aria-hidden>→</span>
        </Link>
      </div>
      <div className="hm-course-grid">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="hm-course-card hm-skeleton" aria-hidden>
                <div className="hm-course-thumb" />
                <div className="hm-skeleton-line" />
                <div className="hm-skeleton-line short" />
              </div>
            ))
          : courses.map((c) => (
              <Link
                key={c.id}
                to={`/courses/${c.slug}`}
                className="hm-course-card"
              >
                <div className="hm-course-thumb">
                  {c.featured_image ? (
                    <img src={c.featured_image} alt="" loading="lazy" />
                  ) : null}
                  <span className="hm-course-cat">{c.category}</span>
                </div>
                <div className="hm-course-body">
                  <h3>{c.title}</h3>
                  <p className="hm-course-meta">
                    {c.instructor?.display_name || "SashaInfinity"} ·{" "}
                    {c.level}
                  </p>
                  <div className="hm-course-foot">
                    <span className="hm-price">
                      {Number(c.price) > 0
                        ? `₹${Number(c.price).toLocaleString("en-IN")}`
                        : "Free"}
                    </span>
                    <span className="hm-go">View <span aria-hidden>→</span></span>
                  </div>
                </div>
              </Link>
            ))}
      </div>
    </section>
  );
}

function PlatformStatsSection({ stats }: { stats: HomeStats | null }) {
  const items = stats
    ? [
        { value: stats.courses, label: "Courses" },
        { value: stats.labs, label: "Interactive labs" },
        { value: stats.subjects, label: "Subjects" },
      ]
    : [];
  return (
    <section className="hm-stats" aria-label="Platform statistics">
      {items.map((it) => (
        <CountUp key={it.label} value={it.value} label={it.label} />
      ))}
    </section>
  );
}

function CountUp({ value, label }: { value: number; label: string }) {
  const [n, setN] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const done = useRef(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const run = () => {
      if (done.current) return;
      done.current = true;
      if (reduced) { setN(value); return; }
      const t0 = performance.now();
      const dur = 900;
      const tick = (t: number) => {
        const p = Math.min(1, (t - t0) / dur);
        setN(Math.round(value * (1 - Math.pow(1 - p, 3))));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    const io = new IntersectionObserver((es) => es[0].isIntersecting && run(), { threshold: 0.4 });
    io.observe(el);
    return () => io.disconnect();
  }, [value]);
  return (
    <div className="hm-stat" ref={ref}>
      <strong>{n.toLocaleString("en-IN")}+</strong>
      <span>{label}</span>
    </div>
  );
}

function LiveClassesSection() {
  const { user } = useAuthStore();
  const [classes, setClasses] = useState<any[] | null>(null);
  useEffect(() => {
    if (!user) return;
    let live = true;
    api
      .get("/live/classes?scope=upcoming&page_size=3")
      .then((r) => { if (live) setClasses(r.data?.items ?? []); })
      .catch(() => {});
    return () => { live = false; };
  }, [user]);
  return (
    <section className="hm-section hm-live" aria-labelledby="hm-live-title">
      <div className="hm-live-grid">
        <div className="hm-live-copy">
          <span className="hm-kicker">Live learning</span>
          <h2 id="hm-live-title">Real-time classes with your instructors</h2>
          <p>
            Scheduled doubt-clearing sessions and live walkthroughs for
            enrolled courses — ask questions and practice together.
          </p>
          <Link to={user ? "/dashboard" : "/register"} className="hm-primary-cta">
            {user ? "View your schedule" : "Create free account"}
          </Link>
        </div>
        <div className="hm-live-list">
          {classes === null ? (
            <div className="hm-live-card hm-skeleton">
              <div className="hm-skeleton-line" />
              <div className="hm-skeleton-line short" />
            </div>
          ) : classes.length === 0 ? (
            <div className="hm-live-card">
              <strong>No upcoming sessions right now</strong>
              <span>New classes are scheduled with every course cycle.</span>
            </div>
          ) : (
            classes.map((c) => (
              <div key={c.id} className="hm-live-card">
                <span className="hm-live-dot" aria-hidden />
                <div>
                  <strong>{c.title}</strong>
                  <span>
                    {new Date(c.scheduled_start).toLocaleString("en-IN", {
                      weekday: "short",
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

const FAQS: Array<[string, string]> = [
  ["Are the learning labs really interactive?", "Yes — the labs run directly in your browser: 60+ simulations across physics, chemistry, biology and maths. No installs, no special hardware."],
  ["Do you offer live classes?", "Yes. Courses include scheduled live sessions with instructors for doubts and walkthroughs. Enrolled students see the schedule on their dashboard."],
  ["Is content available in Tamil?", "Yes — several courses are taught in Tamil, and lab guidance includes Tamil explanations where authored."],
  ["Will I get a certificate?", "Yes, completing a course makes you eligible for a certificate you can download and share."],
  ["Can I try a course before paying?", "Yes — courses with preview lessons are free to sample, and several complete courses are free."],
];

function FaqSection() {
  return (
    <section className="hm-section" aria-labelledby="hm-faq-title">
      <div className="hm-section-head">
        <div>
          <span className="hm-kicker">Questions</span>
          <h2 id="hm-faq-title">Frequently asked</h2>
        </div>
      </div>
      <div className="hm-faq-list">
        {FAQS.map(([q, a]) => (
          <details key={q} className="hm-faq">
            <summary>{q}</summary>
            <p>{a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

export const HomePage = () => {
  useSEO({
    title: "SashaInfinity | Learn, practice and build",
    description:
      "Explore expert-led courses, interactive learning labs and career opportunities.",
  });
  const stats = useHomeStats();
  return (
    <div className="sasha-home rd-home">
      <HeroSection stats={stats} />
      <StatsBar />
      <FeaturedCoursesSection />
      <PlatformStatsSection stats={stats} />
      <ScrollStackSection />
      <AboutSection />
      <CategoriesSection />
      <CardSwapSection />
      <TestimonialSection />
      <TeamSection />
      <LiveClassesSection />
      <FaqSection />
      <CTASection />
      <BlogPreviewSection />
      <PartnersSection />
      <NewsletterSection />
      <IndependenceDayPopup />
      <OfferTimerWidget />
    </div>
  );
};
