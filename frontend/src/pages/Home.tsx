import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUpRight } from "lucide-react";
import { useSEO } from "@/hooks/use-seo";
import { api } from "@/api/axios";
import toast from "react-hot-toast";
import { getMediaUrl } from "@/utils/media";
import { IndependenceDayPopup } from "@/components/promotional/IndependenceDayPopup";
import { OfferTimerWidget } from "@/components/promotional/OfferTimerWidget";
import {
  STAGE_RANGES,
  TowerScene,
  isIntegratedGPU,
  supportsWebGL,
} from "@/components/sympho/TowerScene";
import {
  SplitHeading,
  SymphoBlueprintSvg,
  SymphoButton,
  SymphoCountUp,
  SymphoCtaBanner,
  SymphoDimensionLine,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

type HomeStats = { courses: number; labs: number; subjects: number };

interface CourseSummary {
  id: number;
  title: string;
  slug?: string;
  post_name?: string;
  short_description?: string;
  description?: string;
  category?: string;
  level?: string;
  thumbnail_url?: string;
  featured_image?: string;
  price?: number;
  is_free?: boolean;
  duration_hours?: number;
  total_lessons?: number;
  instructor_name?: string;
}

interface BlogSummary {
  id: number;
  title: string;
  slug: string;
  excerpt?: string;
  category?: string;
  featured_image?: string;
  created_at?: string;
  reading_time?: number;
}

const PROCESS_STAGES: {
  step: string;
  stage: keyof typeof STAGE_RANGES;
  phase: string;
  duration: string;
  title: string;
  summary: string;
  deliverables: string[];
}[] = [
  {
    step: "01",
    stage: "design",
    phase: "Optical Blueprint & Survey",
    duration: "Stage 01 · CAD Wireframe",
    title: "CAD optical mapping & conceptual framing",
    summary:
      "Every learning trajectory begins with an optical and structural survey. Watch the copper CAD wireframe and titanium brow-bar calibrate on the optical turntable as we map your mathematical and engineering baseline.",
    deliverables: [
      "Adaptive Diagnostic",
      "Optical CAD Topology",
      "Custom Study Blueprint",
    ],
  },
  {
    step: "02",
    stage: "approvals",
    phase: "Utporul — Waveguide Optics",
    duration: "Stage 02 · Lens Assembly",
    title: "First-principles lens & chassis engineering",
    summary:
      "Twin calibration gantries sweep across the frame as multi-element Fresnel waveguide lenses and dichroic optics lock into the titanium chassis — establishing crystal-clear first-principles intuition.",
    deliverables: [
      "Dual Waveguide Optics",
      "First-Principles Proofs",
      "Annotated Schematics",
    ],
  },
  {
    step: "03",
    stage: "structure",
    phase: "Seyappaduporul — Compute Arms",
    duration: "Stage 03 · Neural Hardware",
    title: "Articulated temple compute & system assembly",
    summary:
      "Articulated temple arms unfold into position with exposed copper heat-pipes, neural compute pods, and spatial audio drivers — stressing theory under real full-stack, AI, and systems execution loads.",
    deliverables: [
      "Guided Code Sprints",
      "Neural Compute Architecture",
      "System Benchmarks",
    ],
  },
  {
    step: "04",
    stage: "envelope",
    phase: "Interactive Lab — Spatial HUD",
    duration: "Stage 04 · Holographic UI",
    title: "Volumetric HUD projection & browser sandboxes",
    summary:
      "Twin optical frustum beams ignite from the waveguide lenses, projecting floating interactive lab screens into 3D space where learners manipulate wavefunctions, vectors, and live system telemetry.",
    deliverables: [
      "Spatial HUD Sandboxes",
      "CBSE & STEM Simulations",
      "Live 120Hz Telemetry",
    ],
  },
  {
    step: "05",
    stage: "finishes",
    phase: "Meiporul AR — 3D Synthesis",
    duration: "Stage 05 · Orbital Lattice",
    title: "Sacred polyhedron, double-helix & orbital rings",
    summary:
      "Complex geometries, molecular lattices, and multi-dimensional vectors materialize above the AR/VR glass as a rotating 3D icosahedron core, atomic double-helix, and three gyroscopic knowledge rings.",
    deliverables: [
      "WebGL 3D Polyhedra",
      "AR Markerless Optics",
      "Gyroscopic Knowledge Rings",
    ],
  },
  {
    step: "06",
    stage: "handover",
    phase: "Career Commissioning",
    duration: "Stage 06 · Golden Hour",
    title: "Full optical illumination & industry handover",
    summary:
      "Calibration gantries retract and the completed Meiporul AR/VR Learning Glass illuminates at golden hour — unlocking cryptographic certificates, Wall of Fame recognition, and live partner company internships.",
    deliverables: [
      "Verified Certificate",
      "Live Company Internship",
      "Portfolio Defense",
    ],
  },
];

const ECOSYSTEM_DISCIPLINES = [
  {
    index: "01",
    code: "SI—CRS",
    title: "Courses & Mastery Tracks",
    to: "/courses",
    summary:
      "Expert-led engineering, AI, mathematics, and full-stack cohorts structured from foundational axioms to production deployment.",
    deliverables: ["Video Lectures", "Quizzes & Grading", "Verified Certificates"],
    image:
      "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80",
    iconPaths: [
      "M3 20h18",
      "M5 20V9l7-5 7 5v11",
      "M9 20v-6h6v6",
      "M9 10h.01M15 10h.01",
    ],
  },
  {
    index: "02",
    code: "SI—LAB",
    title: "Interactive Learning Labs",
    to: "/labs",
    summary:
      "Hands-on virtual laboratories and curriculum-aligned simulations where learners manipulate variables and test predictions in real time.",
    deliverables: ["Concept Sandboxes", "Guided Labs", "CBSE & STEM Aligned"],
    image:
      "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=900&q=80",
    iconPaths: [
      "M9 3h6",
      "M10 3v5.5L5 17.2A2 2 0 0 0 6.7 20h10.6A2 2 0 0 0 19 17.2L14 8.5V3",
      "M7.5 14h9",
    ],
  },
  {
    index: "03",
    code: "SI—LIB",
    title: "Digital Library & Monographs",
    to: "/library",
    summary:
      "A curated reading room of engineering handbooks, exam compendiums, and annotated reference texts for deep self-study.",
    deliverables: ["E-Books & PDFs", "Study Guides", "Instant Reader"],
    image:
      "https://images.unsplash.com/photo-1507842229356-51c61504d3ab?auto=format&fit=crop&w=900&q=80",
    iconPaths: [
      "M4 19.5A2.5 2.5 0 0 1 6.5 17H20",
      "M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
      "M8 7h8M8 11h6",
    ],
  },
  {
    index: "04",
    code: "SI—MAR",
    title: "Meiporul Spatial AR Studio",
    to: "/meiporul-ar",
    summary:
      "Augmented reality and interactive 3D visualizations that turn abstract mathematical and scientific forms into tangible spatial objects.",
    deliverables: ["3D WebGL Stage", "AR Camera Mode", "Interactive Meshes"],
    image:
      "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=900&q=80",
    iconPaths: [
      "M12 2L3 7l9 5 9-5-9-5z",
      "M3 17l9 5 9-5",
      "M3 12l9 5 9-5",
    ],
  },
  {
    index: "05",
    code: "SI—TRI",
    title: "Subjects & The Tamil Knowledge Triad",
    to: "/categories",
    summary:
      "Courses organized across classical philosophical dimensions — Meiporul (Ultimate Reality), Utporul (Core Essence), and Seyappaduporul (Applied Action).",
    deliverables: ["Meiporul", "Utporul", "Seyappaduporul"],
    image:
      "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=900&q=80",
    iconPaths: [
      "M12 3v18",
      "M3 12h18",
      "M5.6 5.6l12.8 12.8",
      "M18.4 5.6L5.6 18.4",
    ],
  },
  {
    index: "06",
    code: "SI—INT",
    title: "Verified Internships & Company Sprints",
    to: "/internships",
    summary:
      "Bridge academic mastery with industry execution through structured internships, work-log telemetry, and mentor-reviewed deliverables.",
    deliverables: ["Company Cohorts", "Daily Work Logs", "Placement Pipeline"],
    image:
      "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=900&q=80",
    iconPaths: [
      "M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16",
      "M2 8h20v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8z",
    ],
  },
  {
    index: "07",
    code: "SI—CMP",
    title: "Campus OS for Institutions",
    to: "/campus",
    summary:
      "A unified operating system for schools, colleges, and universities — cohorts, live classes, adaptive math pilots, and institutional analytics.",
    deliverables: ["Cohort Management", "Live Classrooms", "SPOC & Admin Portals"],
    image:
      "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=900&q=80",
    iconPaths: [
      "M3 21h18",
      "M5 21V7l7-4 7 4v14",
      "M9 21v-4h6v4",
      "M9 10h6M9 14h6",
    ],
  },
];

const WHY_PILLARS = [
  {
    num: "01",
    title: "Meiporul — Spatial & Conceptual Truth",
    body: "We refuse superficial memorization. Every module is designed to reveal the underlying geometric and structural truth of a discipline through 3D and interactive inquiry.",
    icon: [
      "M12 2L3 7l9 5 9-5-9-5z",
      "M3 17l9 5 9-5",
      "M3 12l9 5 9-5",
    ],
  },
  {
    num: "02",
    title: "Utporul — First-Principles Rigor",
    body: "Curricula authored by practicing engineers and educators who teach the invariant architecture beneath rapidly changing tools and languages.",
    icon: [
      "M4 20h16",
      "M6 20V8l6-4 6 4v12",
      "M10 20v-5h4v5",
    ],
  },
  {
    num: "03",
    title: "Seyappaduporul — Applied Execution",
    body: "Knowledge is validated only when built. Every track culminates in working codebases, laboratory telemetry, and graded real-world assignments.",
    icon: [
      "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
    ],
  },
  {
    num: "04",
    title: "Zero-Setup Browser Laboratories",
    body: "No fragile local installs required to start experimenting. Launch interactive physics, math, chemistry, and coding simulations directly in the browser.",
    icon: [
      "M2 6h20v12H2z",
      "M6 10l3 2-3 2",
      "M11 14h4",
    ],
  },
  {
    num: "05",
    title: "Direct Industry & Campus Bridge",
    body: "From Salem to global engineering teams, our integrated internship portal and Campus OS connect student mastery directly with hiring partners.",
    icon: [
      "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
      "M9 12l2 2 4-4",
    ],
  },
];

const TESTIMONIALS = [
  {
    quote:
      "SashaInfinity completely changed how our students approach mathematics and engineering. The 3D Meiporul visualizations turned abstract calculus and vectors into something students could rotate, test, and genuinely understand.",
    author: "Dr. Aravind Ramanathan",
    role: "Dean of Academic Innovation",
    project: "Campus OS & Adaptive Math Pilot",
    projectHref: "/campus",
  },
  {
    quote:
      "Moving from passive video lectures to SashaInfinity’s interactive learning labs and guided code sprints gave me the confidence to build production APIs and land my first engineering internship.",
    author: "Kavya Sundaram",
    role: "Full-Stack Engineering Fellow",
    project: "Seyappaduporul Cohort · Wall of Fame",
    projectHref: "/hall-of-fame",
  },
  {
    quote:
      "The company internship portal lets our engineering leads review candidate work logs, attendance, and capstone artifacts in one clean architectural ledger. We hired three interns directly from our first cohort.",
    author: "Vikramaditya Nair",
    role: "VP of Engineering, NexaCloud Systems",
    project: "Verified Internship Partner",
    projectHref: "/for-companies",
  },
  {
    quote:
      "The Tamil Knowledge Triad — Meiporul, Utporul, Seyappaduporul — isn’t just philosophical naming; it gives learners a disciplined mental model for why a concept exists, how it works, and how to build with it.",
    author: "Prof. Meenakshi Sundaresan",
    role: "Senior Curriculum Architect",
    project: "Triad Taxonomy & Digital Library",
    projectHref: "/categories",
  },
];

const FAQ_ITEMS = [
  {
    q: "How is SashaInfinity structured differently from standard video course platforms?",
    a: "Standard platforms stop at passive video playback. SashaInfinity combines structured courses with interactive browser-based Learning Labs, spatial 3D/AR visualizations (Meiporul AR), a curated Digital Library, and a verified company internship pipeline — so every concept is learned, simulated, and applied.",
  },
  {
    q: "What is the Tamil Knowledge Triad (Meiporul, Utporul, Seyappaduporul)?",
    a: "Our curriculum taxonomy is inspired by classical Tamil epistemology: Meiporul explores ultimate conceptual truth and spatial 3D intuition; Utporul builds deep theoretical and algorithmic foundations; and Seyappaduporul focuses on hands-on applied engineering and real-world execution.",
  },
  {
    q: "Can schools, colleges, and universities deploy SashaInfinity for their own cohorts?",
    a: "Yes. Through Campus OS (/campus), institutions receive dedicated cohort management, SPOC dashboards, live classroom integration, adaptive mathematics pilots, and real-time student mastery telemetry.",
  },
  {
    q: "How do Course Bundles and Memberships work?",
    a: "Individual courses can be enrolled in standalone, grouped into discounted multi-course Mastery Bundles (/bundles), or unlocked platform-wide through a SashaInfinity Membership plan (/membership) with continuous access to labs and library volumes.",
  },
  {
    q: "How do students qualify for internships on the platform?",
    a: "Students can browse open roles on the Internships Marketplace (/internships), build their verified skill and project profile, and apply directly to partner companies. Once accepted, work logs, attendance, and mentor evaluations are tracked transparently inside the workspace.",
  },
];

const FALLBACK_COURSES: CourseSummary[] = [
  {
    id: 101,
    title: "Full-Stack Systems & Cloud Architecture",
    slug: "full-stack-systems-architecture",
    category: "Seyappaduporul · Applied Engineering",
    level: "Intermediate to Advanced",
    short_description:
      "Design, build, and deploy resilient React, FastAPI, PostgreSQL, and containerized microservices with production telemetry.",
    thumbnail_url:
      "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1200&q=80",
    duration_hours: 48,
    total_lessons: 64,
    is_free: false,
    price: 4999,
  },
  {
    id: 102,
    title: "Spatial Mathematics & Meiporul 3D Visualization",
    slug: "spatial-mathematics-meiporul-3d",
    category: "Meiporul · Spatial Intuition",
    level: "All Levels",
    short_description:
      "Master linear algebra, multivariable calculus, and solid geometry through interactive WebGL scenes and augmented reality projections.",
    thumbnail_url:
      "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=1200&q=80",
    duration_hours: 32,
    total_lessons: 42,
    is_free: true,
    price: 0,
  },
  {
    id: 103,
    title: "Applied AI, Neural Architectures & LLM Systems",
    slug: "applied-ai-neural-architectures",
    category: "Utporul · Core Intelligence",
    level: "Advanced",
    short_description:
      "From transformer mathematics and vector embeddings to production retrieval-augmented generation and autonomous evaluation pipelines.",
    thumbnail_url:
      "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=1200&q=80",
    duration_hours: 56,
    total_lessons: 72,
    is_free: false,
    price: 6499,
  },
  {
    id: 104,
    title: "Data Science, Statistical Modeling & Visual Telemetry",
    slug: "data-science-statistical-modeling",
    category: "Seyappaduporul · Data Systems",
    level: "Intermediate",
    short_description:
      "Turn raw empirical datasets into rigorous statistical models, interactive dashboards, and decision-grade engineering insights.",
    thumbnail_url:
      "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80",
    duration_hours: 40,
    total_lessons: 50,
    is_free: false,
    price: 3999,
  },
];

const FALLBACK_BLOGS: BlogSummary[] = [
  {
    id: 1,
    title: "Why Spatial 3D Pedagogy Outperforms Flat Textbooks in STEM",
    slug: "spatial-3d-pedagogy-stem",
    category: "Meiporul Research",
    reading_time: 6,
    created_at: "2026-05-12",
    excerpt:
      "How interactive WebGL models and augmented reality reduce cognitive load when students first encounter three-dimensional vectors and solid geometry.",
    featured_image:
      "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 2,
    title: "Architecting Browser-Native Learning Labs for 10,000+ Students",
    slug: "architecting-browser-learning-labs",
    category: "Systems Engineering",
    reading_time: 8,
    created_at: "2026-04-28",
    excerpt:
      "Inside our zero-setup simulation engine: deterministic state machines, guided checkpoints, and instant instructor telemetry.",
    featured_image:
      "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 3,
    title: "The Tamil Knowledge Triad as a Modern Engineering Curriculum",
    slug: "tamil-knowledge-triad-curriculum",
    category: "Academic Philosophy",
    reading_time: 5,
    created_at: "2026-04-10",
    excerpt:
      "Connecting classical philosophical categories — Meiporul, Utporul, and Seyappaduporul — to modern software and scientific mastery.",
    featured_image:
      "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=900&q=80",
  },
];

/**
 * Exported NewsletterSection component — preserves the exact M-12 unit test contract
 * in `src/pages/__tests__/home.newsletter.test.tsx`.
 */
export function NewsletterSection() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isValidEmail = (val: string) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val.trim());

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidEmail(email)) {
      toast.error("Please enter a valid email address");
      return;
    }
    try {
      setSubmitting(true);
      await api.post("/blog/newsletter/subscribe", { email: email.trim() });
      toast.success("Subscribed successfully!");
      setEmail("");
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        "Unable to subscribe right now. Please try again.";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-reveal=""
      className="sheet-frame mt-14 rounded-xl border border-ink-900/15 bg-limestone-50 p-8 sm:p-10"
    >
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-center">
        <div className="lg:col-span-7">
          <p className="sheet-label mb-3">Studio Dispatch</p>
          <h3 className="font-display text-display-sm font-light tracking-tight text-ink-900">
            Receive monthly field notes on engineering &{" "}
            <em className="italic">spatial pedagogy</em>
          </h3>
          <p className="mt-2 max-w-xl text-sm text-ink-600">
            New learning labs, curriculum releases, and open internship cohorts
            delivered directly to your inbox. No noise.
          </p>
        </div>
        <div className="lg:col-span-5">
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-3 sm:flex-row"
            noValidate
          >
            <div className="flex flex-1 flex-col">
              <label
                htmlFor="newsletter-email"
                className="sheet-label mb-1.5 block"
              >
                Email address
              </label>
              <input
                id="newsletter-email"
                type="email"
                required
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="field-input"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="sympho-btn bg-ink-900 px-6 py-3 text-sm text-limestone-50 shadow-plate [--fill:var(--color-copper-500)]"
            >
              <span aria-hidden="true" className="sympho-btn-fill" />
              <span className="relative z-10">
                {submitting ? "Subscribing..." : "Subscribe"}
              </span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export function HomePage() {
  useSEO({
    title: "SashaInfinity — Knowledge Architecture, Interactive Labs & Courses",
    description:
      "Master cutting-edge technology, mathematics, and engineering through structured courses, interactive browser labs, Meiporul 3D/AR, and verified internships.",
  });

  const [stats, setStats] = useState<HomeStats>({
    courses: 42,
    labs: 28,
    subjects: 12,
  });
  const [featuredCourses, setFeaturedCourses] =
    useState<CourseSummary[]>(FALLBACK_COURSES);
  const [blogs, setBlogs] = useState<BlogSummary[]>(FALLBACK_BLOGS);

  // Scroll-driven 3D stage state (exact Sympho Build Te choreography)
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stageWrapRef = useRef<HTMLElement | null>(null);
  const stageViewportRef = useRef<HTMLDivElement | null>(null);
  const heroRef = useRef<HTMLElement | null>(null);
  const stageItemRefs = useRef<(HTMLLIElement | null)[]>([]);
  const [sceneReady, setSceneReady] = useState(false);
  const [blueprintFaded, setBlueprintFaded] = useState(false);
  const [heroProgress, setHeroProgress] = useState(0);
  const [activeStageIdx, setActiveStageIdx] = useState(-1);
  const [stageLocalProgress, setStageLocalProgress] = useState(0);

  // Scroll parallax refs for SI—02 featured course plates
  const coursePlateRefs = useRef<(HTMLAnchorElement | null)[]>([]);
  const courseImgInnerRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Interactive ecosystem index state (SI—03 with rAF lerp + velocity tilt)
  const [hoveredDiscipline, setHoveredDiscipline] = useState(-1);
  const indexWrapRef = useRef<HTMLDivElement | null>(null);
  const previewOuterRef = useRef<HTMLDivElement | null>(null);

  // Spotlight state for dark Why section (SI—04)
  const whySectionRef = useRef<HTMLElement | null>(null);

  // Quote carousel state (SI—05 with directional slide)
  const [quoteIdx, setQuoteIdx] = useState(0);
  const [quoteDir, setQuoteDir] = useState(1);

  const selectQuote = useCallback(
    (nextIdx: number) => {
      setQuoteDir(nextIdx > quoteIdx ? 1 : -1);
      setQuoteIdx(
        (nextIdx + TESTIMONIALS.length) % TESTIMONIALS.length
      );
    },
    [quoteIdx]
  );

  // Fetch live platform data
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const [coursesRes, labsRes, blogsRes] = await Promise.allSettled([
          api.get("/courses/?page=1&page_size=12"),
          api.get("/virtual-labs"),
          api.get("/blog?limit=3"),
        ]);
        if (!live) return;

        if (coursesRes.status === "fulfilled") {
          const list: CourseSummary[] = coursesRes.value.data?.courses ?? [];
          const total = coursesRes.value.data?.total ?? list.length;
          const cats = new Set(
            list.map((c) => (c.category || "").trim()).filter(Boolean)
          );
          if (list.length > 0) {
            setFeaturedCourses(list.slice(0, 4));
          }
          setStats((prev) => ({
            courses: total > 0 ? total : prev.courses,
            labs:
              labsRes.status === "fulfilled" &&
              (labsRes.value.data?.labs ?? []).length > 0
                ? labsRes.value.data.labs.length
                : prev.labs,
            subjects: cats.size > 0 ? cats.size : prev.subjects,
          }));
        }

        if (blogsRes.status === "fulfilled") {
          const items: BlogSummary[] =
            blogsRes.value.data?.posts ||
            blogsRes.value.data?.blogs ||
            (Array.isArray(blogsRes.value.data) ? blogsRes.value.data : []);
          if (items.length > 0) {
            setBlogs(items.slice(0, 3));
          }
        }
      } catch {
        // Fallback data remains in place
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  // Exact Sympho Build Hero + 6-Stage Process 3D TowerScene scroll choreography
  useEffect(() => {
    const wrapEl = stageWrapRef.current;
    const heroEl = heroRef.current;
    const canvas = canvasRef.current;
    if (!wrapEl || !heroEl) return;

    let scene: TowerScene | undefined;
    let disposed = false;
    let scrollRaf = 0;
    let fadeTimer: ReturnType<typeof setTimeout> | undefined;

    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    const computeScrollState = () => {
      scrollRaf = 0;
      const vh = window.innerHeight || 1;
      const wrapRect = wrapEl.getBoundingClientRect();
      const stageVp = stageViewportRef.current;
      if (stageVp) {
        if (wrapRect.top >= 0) {
          stageVp.style.position = "absolute";
          stageVp.style.top = "0px";
          stageVp.style.bottom = "auto";
        } else if (wrapRect.bottom <= vh) {
          stageVp.style.position = "absolute";
          stageVp.style.top = "auto";
          stageVp.style.bottom = "0px";
        } else {
          stageVp.style.position = "fixed";
          stageVp.style.top = "0px";
          stageVp.style.bottom = "auto";
        }
      }

      const heroRect = heroEl.getBoundingClientRect();
      const hp = Math.min(
        1,
        Math.max(0, -heroRect.top / Math.max(1, heroRect.height * 0.85))
      );
      setHeroProgress(hp);

      let currentIdx = -1;
      let localProg = 0;
      const triggerY = vh * 0.55;

      stageItemRefs.current.forEach((li, idx) => {
        if (!li) return;
        const r = li.getBoundingClientRect();
        if (r.top <= triggerY) {
          currentIdx = idx;
          localProg = Math.min(
            1,
            Math.max(0, (triggerY - r.top) / Math.max(1, r.height))
          );
        }
      });

      setActiveStageIdx(currentIdx);
      setStageLocalProgress(localProg);

      let buildVal = 0;
      if (currentIdx >= 0) {
        const st = PROCESS_STAGES[currentIdx];
        const range = STAGE_RANGES[st.stage] || [
          currentIdx / PROCESS_STAGES.length,
          (currentIdx + 1) / PROCESS_STAGES.length,
        ];
        buildVal = range[0] + (range[1] - range[0]) * localProg;
      }

      scene?.setHero(hp);
      scene?.setBuild(buildVal);

      // Update continuous scroll parallax on SI—02 course plates
      coursePlateRefs.current.forEach((plateEl, idx) => {
        const innerEl = courseImgInnerRefs.current[idx];
        if (!plateEl || !innerEl || reducedMotion) return;
        const pr = plateEl.getBoundingClientRect();
        if (pr.bottom < -100 || pr.top > vh + 100) return;
        const prog = Math.min(1, Math.max(0, (vh - pr.top) / (vh + pr.height)));
        const shift = ((prog - 0.5) * 12).toFixed(2);
        innerEl.style.transform = `translate3d(0, ${shift}%, 0)`;
      });
    };

    const scheduleScrollUpdate = () => {
      if (!scrollRaf) {
        scrollRaf = requestAnimationFrame(computeScrollState);
      }
    };

    const onPointerMove = (e: PointerEvent) => {
      scene?.setPointer(
        (e.clientX / Math.max(1, window.innerWidth)) * 2 - 1,
        (e.clientY / Math.max(1, window.innerHeight)) * 2 - 1
      );
    };

    window.addEventListener("scroll", scheduleScrollUpdate, { passive: true });
    window.addEventListener("resize", scheduleScrollUpdate, { passive: true });
    computeScrollState();

    let visIo: IntersectionObserver | undefined;
    if (typeof IntersectionObserver !== "undefined") {
      visIo = new IntersectionObserver(([entry]) => {
        scene?.setVisible(entry.isIntersecting);
      });
      visIo.observe(wrapEl);
    }

    let ro: ResizeObserver | undefined;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(() => {
        if (!scene || !canvas) return;
        const rect = canvas.getBoundingClientRect();
        scene.setLayout(window.innerWidth >= 1024 ? "split" : "center");
        scene.resize(rect.width, rect.height);
      });
    }

    if (canvas && supportsWebGL() && !disposed) {
      const nav = navigator as any;
      const isLow =
        window.innerWidth < 768 ||
        (nav.hardwareConcurrency ?? 8) <= 4 ||
        (nav.deviceMemory ?? 8) <= 4;
      try {
        scene = new TowerScene(canvas, {
          quality: isLow ? "low" : isIntegratedGPU() ? "medium" : "high",
          reducedMotion,
          layout: window.innerWidth >= 1024 ? "split" : "center",
          onError: () => setSceneReady(false),
        });
        const rect = canvas.getBoundingClientRect();
        scene.setLayout(window.innerWidth >= 1024 ? "split" : "center");
        scene.resize(rect.width, rect.height);
        ro?.observe(canvas);
        window.addEventListener("pointermove", onPointerMove, {
          passive: true,
        });
        computeScrollState();
        requestAnimationFrame(() => setSceneReady(true));
        fadeTimer = setTimeout(() => setBlueprintFaded(true), 1800);
      } catch {
        setSceneReady(false);
      }
    }

    return () => {
      disposed = true;
      cancelAnimationFrame(scrollRaf);
      if (fadeTimer) clearTimeout(fadeTimer);
      visIo?.disconnect();
      ro?.disconnect();
      window.removeEventListener("scroll", scheduleScrollUpdate);
      window.removeEventListener("resize", scheduleScrollUpdate);
      window.removeEventListener("pointermove", onPointerMove);
      scene?.dispose();
    };
  }, []);

  // SI—03 Floating Preview Card rAF Lerp + Velocity Tilt (matches Re in scratch/node2.js)
  useEffect(() => {
    const wrap = indexWrapRef.current;
    if (!wrap || typeof window === "undefined") return;
    const finePointer =
      window.matchMedia?.("(hover: hover) and (pointer: fine)").matches ?? false;
    if (!finePointer) return;

    const reduced =
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

    let curX = 0;
    let curY = 0;
    let targetX = 0;
    let targetY = 0;
    let raf = 0;

    const tick = () => {
      const dx = targetX - curX;
      curX += dx * (reduced ? 1 : 0.14);
      curY += (targetY - curY) * (reduced ? 1 : 0.14);
      const previewEl = previewOuterRef.current;
      if (previewEl) {
        const tilt = reduced ? 0 : Math.max(-8, Math.min(8, dx * 0.05));
        previewEl.style.transform = `translate3d(${curX.toFixed(
          1
        )}px, ${curY.toFixed(1)}px, 0) rotate(${tilt.toFixed(2)}deg)`;
      }
      raf = requestAnimationFrame(tick);
    };

    const onMove = (e: PointerEvent) => {
      const rect = wrap.getBoundingClientRect();
      targetX = e.clientX - rect.left;
      targetY = e.clientY - rect.top;
    };

    wrap.addEventListener("pointermove", onMove, { passive: true });
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      wrap.removeEventListener("pointermove", onMove);
    };
  }, []);

  const handleWhyPointerMove = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      const el = whySectionRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const mx = ((e.clientX - rect.left) / rect.width) * 100;
      const my = ((e.clientY - rect.top) / rect.height) * 100;
      el.style.setProperty("--mx", `${mx.toFixed(1)}%`);
      el.style.setProperty("--my", `${my.toFixed(1)}%`);
    },
    []
  );

  return (
    <div className="sympho-scope bg-limestone-100 text-ink-900">
      <IndependenceDayPopup />
      <OfferTimerWidget />

      {/* ====================================================================
          STAGE 00 — STICKY 3D WEBGL TOWER STAGE + HERO + 6-STAGE PROCESS
          Exact Sympho Build scroll-driven architecture (Te in node2.js)
          ==================================================================== */}
      <section
        ref={stageWrapRef}
        aria-label="Introduction and knowledge construction process"
        className="on-dark relative bg-ink-900 text-limestone-50"
      >
        {/* Pinned Full-Viewport 3D AR/VR Learning Glass Stage & Blueprint Backdrop */}
        <div
          ref={stageViewportRef}
          aria-hidden="true"
          className="pointer-events-none z-0 h-screen h-svh w-full overflow-hidden"
          style={{
            position: "absolute",
            top: "0px",
            left: 0,
            right: 0,
            height: "100vh",
          }}
        >
          {!(sceneReady && blueprintFaded) && (
            <>
              <div className="blueprint-grid absolute inset-0" />
              <div
                className={`absolute inset-0 flex items-start justify-center pt-[14svh] text-copper-400 transition-opacity duration-1000 lg:items-center lg:justify-end lg:pt-0 lg:pr-[6vw] ${
                  sceneReady ? "opacity-0" : "opacity-100"
                }`}
              >
                <div className="w-[min(92vw,34rem)] lg:w-[min(46vw,44rem)]">
                  <SymphoBlueprintSvg className="h-full w-full text-copper-400" />
                </div>
              </div>
            </>
          )}

          <canvas
            ref={canvasRef}
            className={`absolute inset-0 h-full w-full transition-opacity duration-[1600ms] ease-out ${
              sceneReady ? "opacity-100" : "opacity-0"
            }`}
          />

          {/* Left & Bottom Readability Gradients */}
          <div className="absolute inset-0 bg-gradient-to-t from-ink-900 via-ink-900/35 to-transparent lg:bg-gradient-to-r lg:from-ink-900/90 lg:via-ink-900/30 lg:to-transparent" />
          <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-ink-900/80 to-transparent" />

          {/* Top-Right Architectural Drawing Coordinates */}
          <div className="absolute top-[calc(var(--spacing-header)+1.25rem)] right-gutter hidden text-right font-mono text-label uppercase text-limestone-300 md:block">
            <p>Drawing SI—AR · Scale 1:1 · Waveguide Optics</p>
            <p className="mt-1 text-limestone-400">
              Meiporul Spatial Lab · 11.66° N, 78.14° E
            </p>
          </div>

          {/* Right Vertical Stage Progress Rail */}
          <ol className="absolute top-1/2 right-gutter hidden -translate-y-1/2 flex-col gap-3 xl:flex">
            {PROCESS_STAGES.map((st, idx) => {
              const isCurrent = idx === activeStageIdx;
              return (
                <li
                  key={st.step}
                  className={`flex items-center justify-end gap-3 font-mono text-label uppercase transition-colors duration-500 ${
                    isCurrent ? "text-copper-300" : "text-limestone-100/35"
                  }`}
                >
                  <span
                    className={`rounded-xs bg-ink-900/85 px-2 py-1 transition-opacity duration-500 ${
                      isCurrent ? "opacity-100" : "opacity-0"
                    }`}
                  >
                    {st.phase}
                  </span>
                  <span
                    className={`h-px transition-all duration-700 ease-out-expo ${
                      isCurrent ? "w-10 bg-copper-400" : "w-4 bg-current"
                    }`}
                  />
                </li>
              );
            })}
          </ol>
        </div>

        {/* FOREGROUND HERO + 6-STAGE SCROLL PROCESS */}
        <div className="relative z-10">
          {/* HERO */}
          <header
            ref={(node) => {
              heroRef.current = node;
            }}
            id="home"
            data-testid="hero-section"
            className="container-page flex min-h-svh flex-col justify-end pt-36 pb-16 sm:pb-24"
          >
            <div className="max-w-3xl lg:max-w-[44vw]">
              <p data-reveal="" className="sheet-label mb-8">
                SashaInfinity — Est. Salem · Learn • Practice • Build
              </p>

              <SplitHeading
                as="h1"
                text="Your next chapter starts with architectural curiosity."
                className="text-display-2xl font-light tracking-[-0.04em] text-limestone-50"
                italicLast={2}
              />

              <p
                data-reveal=""
                style={{ ["--reveal-delay" as string]: "350ms" }}
                className="mt-8 max-w-xl text-lede text-limestone-200"
              >
                Explore expert-led courses, put ideas to the test in browser
                learning labs, visualize concepts in 3D Meiporul AR/VR, and
                launch your career through verified industry internships.
              </p>

              <div
                data-reveal=""
                style={{ ["--reveal-delay" as string]: "500ms" }}
                className="mt-10 flex flex-wrap gap-3"
              >
                <SymphoButton to="/courses" variant="on-dark" size="lg" arrow>
                  Explore courses
                </SymphoButton>
                <SymphoButton to="/labs" variant="outline-dark" size="lg">
                  Try a learning lab
                </SymphoButton>
              </div>

              <div
                data-reveal=""
                style={{ ["--reveal-delay" as string]: "620ms" }}
                className="mt-8 flex flex-wrap items-center gap-6 font-mono text-label text-limestone-300"
              >
                <Link
                  to="/categories"
                  className="hover:text-copper-300 transition-colors link-dim"
                >
                  01 · Explore subjects
                </Link>
                <Link
                  to="/internships"
                  className="hover:text-copper-300 transition-colors link-dim"
                >
                  02 · Find an internship
                </Link>
                <Link
                  to="/library"
                  className="hover:text-copper-300 transition-colors link-dim"
                >
                  03 · Digital library
                </Link>
                <Link
                  to="/meiporul-ar"
                  className="hover:text-copper-300 transition-colors link-dim"
                >
                  04 · Meiporul AR
                </Link>
              </div>
            </div>

            <a
              href="#process"
              style={{ opacity: Math.max(0, 1 - heroProgress * 2) }}
              className="mt-16 inline-flex items-center gap-3 self-start font-mono text-label uppercase text-limestone-300 transition-opacity hover:text-limestone-50"
            >
              <span className="relative grid size-10 place-items-center overflow-hidden rounded-full border border-limestone-100/30">
                <ArrowDown
                  size={14}
                  aria-hidden="true"
                  className="scroll-cue"
                />
              </span>
              Scroll to build
            </a>
          </header>

          {/* 6-STAGE SCROLL-DRIVEN PROCESS SECTION */}
          <div
            id="process"
            data-testid="scroll-stack-section"
            className="container-page pt-section-sm pb-[30svh]"
          >
            <div className="max-w-xl">
              <p data-reveal="" className="sheet-label">
                Our process
              </p>
              <SplitHeading
                as="h2"
                id="process-heading"
                text="From first axiom to spatial career mastery"
                className="mt-6 text-display-lg font-light text-limestone-50"
                italicLast={2}
              />
              <p data-reveal="" className="mt-6 text-lede text-limestone-300">
                Every stage of the SashaInfinity learning architecture is
                integrated — watch the 3D Meiporul AR/VR Learning Glass assemble
                its waveguide lenses, unfold its neural compute arms, project
                spatial lab HUDs, and orbit 3D polyhedral knowledge rings as you
                scroll through the six stages below.
              </p>
            </div>

            <ol className="mt-[20svh] flex flex-col">
              {PROCESS_STAGES.map((stage, i) => {
                const isActive = i === activeStageIdx;
                const isPassed = i < activeStageIdx;
                const barScale = isPassed
                  ? 1
                  : isActive
                  ? Math.max(0.18, stageLocalProgress)
                  : 0;

                return (
                  <li
                    key={stage.step}
                    id={`stage-${i + 1}`}
                    ref={(node) => {
                      stageItemRefs.current[i] = node;
                    }}
                    aria-current={isActive ? "step" : undefined}
                    className="flex min-h-[110svh] items-end pb-[42svh] lg:min-h-[95svh] lg:items-center lg:pb-0"
                  >
                    <article
                      data-no-auto-reveal=""
                      className={`sticky bottom-[calc(5.5rem+env(safe-area-inset-bottom))] w-full max-w-md rounded-md border bg-ink-900/90 p-5 transition-[border-color] duration-700 ease-out-expo sm:p-7 lg:static lg:bg-ink-900/85 lg:p-9 ${
                        isActive
                          ? "border-copper-400/60"
                          : "border-limestone-100/12"
                      }`}
                    >
                      <div className="flex items-center justify-between font-mono text-label uppercase">
                        <span className="text-copper-300">
                          Stage {stage.step} / 06
                        </span>
                        <span className="text-limestone-400">
                          {stage.duration}
                        </span>
                      </div>

                      <h3 className="mt-3 font-display text-lg font-semibold leading-snug text-limestone-50 sm:text-xl lg:mt-4">
                        {stage.title}
                      </h3>

                      <p className="mt-2.5 text-sm leading-relaxed text-limestone-200 lg:mt-3">
                        {stage.summary}
                      </p>

                      <ul className="mt-4 flex flex-wrap gap-1.5">
                        {stage.deliverables.map((d) => (
                          <li
                            key={d}
                            className="rounded-pill border border-limestone-100/18 bg-limestone-50/5 px-2.5 py-0.5 font-mono text-[0.64rem] uppercase tracking-wider text-limestone-200"
                          >
                            {d}
                          </li>
                        ))}
                      </ul>

                      <div className="mt-6 h-px w-full bg-limestone-100/12">
                        <div
                          className="h-px origin-left bg-copper-400 transition-transform duration-700 ease-out-expo"
                          style={{ transform: `scaleX(${barScale})` }}
                        />
                      </div>
                    </article>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SI—01 — MEASURED BY WHAT ENDURES (STATS WITH COUNT-UP & DRAW LINES)
          Matches Q in scratch/node2.js
          ==================================================================== */}
      <section
        aria-labelledby="stats-heading"
        data-testid="stats-bar"
        className="container-page border-b border-ink-900/12 py-section"
      >
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <span className="font-mono text-label text-copper-500">SI—01</span>
            <span className="sheet-label">By the Numbers</span>
          </div>
          <h2
            id="stats-heading"
            data-reveal=""
            className="max-w-[30ch] font-display text-display-md font-light text-ink-900"
          >
            Measured by what endures across cohorts, laboratories, and careers.
          </h2>
        </div>

        <dl className="mt-10 grid grid-cols-2 gap-x-6 gap-y-10 lg:grid-cols-4">
          {[
            {
              value: stats.courses,
              suffix: "+",
              label:
                "Structured engineering, AI, mathematics & STEM courses",
            },
            {
              value: stats.labs,
              suffix: "+",
              label:
                "Browser-native interactive learning labs & simulations",
            },
            {
              value: 100,
              suffix: "+",
              label:
                "Meiporul 3D & augmented reality spatial learning models",
            },
            {
              value: 98,
              suffix: "%",
              label:
                "Verified learner & institutional partner satisfaction rate",
            },
          ].map((item, idx) => (
            <div
              key={item.label}
              data-reveal=""
              style={{ ["--reveal-delay" as string]: `${idx * 90}ms` }}
              className="flex flex-col-reverse gap-3"
            >
              <dt className="text-xs leading-snug text-ink-600 sm:text-sm">
                {item.label}
              </dt>
              <dd className="font-display text-[clamp(1.85rem,1.4rem+1.8vw,2.75rem)] font-bold leading-none tracking-[-0.03em] text-ink-900 tabular-nums">
                <SymphoCountUp value={item.value} />
                <span className="text-copper-600">{item.suffix}</span>
              </dd>
              <SymphoDimensionLine className="h-3 w-full text-ink-900/35" />
            </div>
          ))}
        </dl>
      </section>

      {/* ====================================================================
          SI—02 — SELECTED PROGRAMS (MASK REVEAL + SCROLL PARALLAX)
          Matches Me in scratch/node2.js
          ==================================================================== */}
      <section
        aria-labelledby="selected-programs-heading"
        className="relative border-b border-ink-900/12 py-14 lg:py-20"
      >
        <div className="container-page">
          <SymphoSectionHeader
            index="SI—02"
            eyebrow="Selected Programs"
            headingId="selected-programs-heading"
            title="Flagship courses & mastery tracks"
            lede="Curated engineering, AI, and mathematical cohorts with interactive labs and verified credentials."
            action={
              <SymphoButton to="/courses" variant="outline" arrow>
                View all courses ({stats.courses}+)
              </SymphoButton>
            }
          />

          <ol className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
            {featuredCourses.slice(0, 4).map((course, idx) => {
              const href = `/courses/${
                course.slug || course.post_name || course.id
              }`;
              const imgUrl =
                getMediaUrl(course.thumbnail_url || course.featured_image) ||
                FALLBACK_COURSES[idx % FALLBACK_COURSES.length].thumbnail_url!;

              return (
                <li
                  key={course.id}
                  data-reveal=""
                  style={{ ["--reveal-delay" as string]: `${idx * 70}ms` }}
                  className="group flex flex-col overflow-hidden rounded-xl border border-ink-900/12 bg-limestone-50/90 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-copper-500/35 hover:shadow-md"
                >
                  <Link
                    ref={(node) => {
                      coursePlateRefs.current[idx] = node;
                    }}
                    to={href}
                    className="relative block overflow-hidden bg-ink-900"
                  >
                    <div
                      ref={(node) => {
                        courseImgInnerRefs.current[idx] = node;
                      }}
                      className="scale-[1.06] will-change-transform"
                    >
                      <div className="relative aspect-[16/10] max-h-40 w-full overflow-hidden">
                        <img
                          src={imgUrl}
                          alt={course.title}
                          loading="lazy"
                          onError={(e) => {
                            (e.currentTarget as HTMLImageElement).src =
                              FALLBACK_COURSES[
                                idx % FALLBACK_COURSES.length
                              ].thumbnail_url!;
                          }}
                          className="h-full w-full object-cover transition-transform duration-700 ease-out-expo group-hover:scale-[1.05]"
                        />
                        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink-950/50 via-transparent to-transparent" />
                      </div>
                    </div>
                    <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between gap-1.5">
                      <span className="truncate rounded-pill bg-limestone-50/95 px-2.5 py-0.5 font-mono text-[0.65rem] font-semibold uppercase tracking-wider text-ink-900 backdrop-blur-sm">
                        {course.category || "Engineering"}
                      </span>
                      <span className="shrink-0 rounded-pill bg-ink-900/85 px-2.5 py-0.5 font-mono text-[0.65rem] font-semibold text-limestone-100 backdrop-blur-sm">
                        {course.is_free || !course.price
                          ? "Free"
                          : `₹${course.price.toLocaleString("en-IN")}`}
                      </span>
                    </div>
                  </Link>

                  <div className="flex flex-1 flex-col justify-between p-4">
                    <div>
                      <p className="flex items-center justify-between font-mono text-[0.68rem] uppercase tracking-wider text-ink-500">
                        <span className="font-semibold text-copper-600">
                          0{idx + 1} / 0{Math.min(4, featuredCourses.length)}
                        </span>
                        <span>{course.level || "All Levels"}</span>
                      </p>

                      <h3 className="mt-2 font-display text-base font-bold leading-snug text-ink-900 line-clamp-2 group-hover:text-copper-600 transition-colors">
                        <Link to={href}>
                          {course.title}
                        </Link>
                      </h3>

                      <p className="mt-1.5 text-xs leading-relaxed text-ink-600 line-clamp-2">
                        {course.short_description ||
                          course.description ||
                          "Hands-on cohort with interactive labs and real-world project evaluation."}
                      </p>
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-ink-900/10 pt-3 font-mono text-[0.68rem] text-ink-600">
                      <span>
                        {course.duration_hours
                          ? `${course.duration_hours}h total`
                          : "Self-Paced + Live"}
                      </span>
                      <Link
                        to={href}
                        className="inline-flex items-center gap-1 font-semibold uppercase tracking-wider text-copper-600 transition-transform group-hover:translate-x-0.5"
                      >
                        Explore
                        <ArrowUpRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </section>

      {/* ====================================================================
          SI—04 — WHY SASHA INFINITY (ON-DARK BLUEPRINT + ICON-DRAW + SPOTLIGHT)
          Matches He in scratch/node2.js
          ==================================================================== */}
      <section
        ref={(node) => {
          whySectionRef.current = node;
        }}
        onPointerMove={handleWhyPointerMove}
        aria-labelledby="why-heading"
        className="on-dark relative overflow-hidden bg-ink-900 py-section text-limestone-50"
      >
        <div
          aria-hidden="true"
          className="blueprint-grid pointer-events-none absolute inset-0"
        />
        <div
          aria-hidden="true"
          className="spot-light pointer-events-none absolute inset-0"
        />

        <div className="container-page relative">
          <SymphoSectionHeader
            index="SI—04"
            eyebrow="Why SashaInfinity"
            headingId="why-heading"
            title="Pedagogy engineered with structural discipline"
            lede="Five commitments that separate an architectural learning environment from generic content libraries."
          />

          <ol className="mt-10 grid gap-px overflow-hidden rounded-md bg-limestone-100/12 sm:grid-cols-2 lg:grid-cols-5">
            {WHY_PILLARS.map((pillar, idx) => (
              <li
                key={pillar.num}
                data-reveal=""
                style={{ ["--reveal-delay" as string]: `${idx * 80}ms` }}
                className="group relative flex flex-col gap-6 bg-ink-900 p-5 transition-colors duration-500 hover:bg-ink-800 lg:min-h-[17rem]"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-label text-limestone-400">
                    {pillar.num}
                  </span>
                  <span className="icon-draw text-copper-400">
                    <svg
                      viewBox="0 0 24 24"
                      width={26}
                      height={26}
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      {pillar.icon.map((d, pIdx) => (
                        <path key={pIdx} d={d} />
                      ))}
                    </svg>
                  </span>
                </div>
                <div className="mt-auto">
                  <h3 className="font-display text-base font-semibold leading-snug text-limestone-50">
                    {pillar.title}
                  </h3>
                  <p className="mt-2 text-xs leading-relaxed text-limestone-300">
                    {pillar.body}
                  </p>
                </div>
                <span
                  aria-hidden="true"
                  className="absolute inset-x-5 bottom-0 h-px origin-left scale-x-0 bg-copper-400 transition-transform duration-700 ease-out-expo group-hover:scale-x-100"
                />
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ====================================================================
          SI—05 — VOICES FROM OUR COHORTS (DIRECTIONAL EDITORIAL QUOTE CAROUSEL)
          Matches Xe in scratch/node2.js
          ==================================================================== */}
      <section
        aria-labelledby="testimonials-heading"
        aria-roledescription="carousel"
        className="border-b border-ink-900/12 py-section"
      >
        <div className="container-page grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <div data-reveal="" className="mb-3 flex items-center gap-3">
              <span className="font-mono text-label text-copper-500">
                SI—05
              </span>
              <span className="sheet-label">Cohort & Partner Voices</span>
            </div>
            <SplitHeading
              as="h2"
              id="testimonials-heading"
              text="Trusted by learners, deans & engineering leads"
              className="text-display-md tracking-tight text-ink-900"
              italicLast={2}
            />

            <div className="mt-7 flex items-center gap-3">
              <button
                type="button"
                aria-label="Previous testimonial"
                onClick={() => selectQuote(quoteIdx - 1)}
                className="sympho-nav-btn"
              >
                <svg
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  className="size-4"
                >
                  <path
                    d="M10 3L5 8l5 5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <button
                type="button"
                aria-label="Next testimonial"
                onClick={() => selectQuote(quoteIdx + 1)}
                className="sympho-nav-btn"
              >
                <svg
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  className="size-4"
                >
                  <path
                    d="M6 3l5 5-5 5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <p
                aria-live="polite"
                aria-atomic="true"
                className="ml-3 font-mono text-label text-ink-500 tabular-nums"
              >
                0{quoteIdx + 1} / 0{TESTIMONIALS.length}
              </p>
            </div>
          </div>

          <div className="relative lg:col-span-8">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className="absolute -top-5 -left-2 h-14 w-14 text-copper-500/25"
            >
              <path
                fill="currentColor"
                d="M3 21v-7.2C3 8.6 5.6 5.2 10.2 4l.8 1.9C8.3 7 7 9 6.8 11.5H11V21H3zm10 0v-7.2c0-5.2 2.6-8.6 7.2-9.8l.8 1.9c-2.7 1.1-4 3.1-4.2 5.6H21V21h-8z"
              />
            </svg>

            <div className="grid">
              {TESTIMONIALS.map((t, idx) => {
                const isActive = idx === quoteIdx;
                return (
                  <figure
                    key={t.author}
                    aria-roledescription="slide"
                    aria-label={`${idx + 1} of ${TESTIMONIALS.length}`}
                    aria-hidden={!isActive}
                    data-active={isActive ? "" : undefined}
                    style={{ ["--dir" as string]: quoteDir }}
                    className={`sympho-quote relative col-start-1 row-start-1 transition-[opacity,visibility] duration-700 ${
                      isActive ? "visible opacity-100" : "invisible opacity-0"
                    }`}
                  >
                    <blockquote className="font-display text-[clamp(1.1rem,0.95rem+0.8vw,1.5rem)] font-medium leading-relaxed tracking-[-0.012em] text-ink-900">
                      “{t.quote}”
                    </blockquote>
                    <figcaption className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                      <span className="font-semibold text-ink-900">
                        {t.author}
                      </span>
                      <span className="text-ink-500">{t.role}</span>
                      <Link
                        to={t.projectHref}
                        tabIndex={isActive ? 0 : -1}
                        className="link-dim font-mono text-label uppercase text-copper-600"
                      >
                        {t.project}
                      </Link>
                    </figcaption>
                  </figure>
                );
              })}
            </div>

            <div
              role="group"
              aria-label="Choose testimonial"
              className="mt-7 flex gap-2"
            >
              {TESTIMONIALS.map((t, i) => (
                <button
                  key={t.author}
                  type="button"
                  aria-label={`Show testimonial ${i + 1}`}
                  aria-current={i === quoteIdx}
                  onClick={() => selectQuote(i)}
                  className="group grid h-8 flex-1 items-center"
                >
                  <span
                    className={`h-px w-full transition-colors duration-500 ${
                      i === quoteIdx
                        ? "bg-copper-500"
                        : "bg-ink-900/20 group-hover:bg-ink-900/50"
                    }`}
                  />
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SI—06 — FIELD NOTES & INSIGHTS + STUDIO DISPATCH NEWSLETTER
          ==================================================================== */}
      <section
        aria-labelledby="insights-heading"
        className="border-b border-ink-900/12 bg-limestone-200/60 py-section"
      >
        <div className="container-page">
          <SymphoSectionHeader
            index="SI—06"
            eyebrow="Field Notes"
            headingId="insights-heading"
            title="Notes from our academic & engineering studio"
            lede="Essays on spatial pedagogy, browser simulation engineering, and curriculum design — written by the instructors and builders behind SashaInfinity."
            action={
              <SymphoButton to="/blog" variant="outline" arrow>
                All articles
              </SymphoButton>
            }
          />

          <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-12">
            {/* Featured plate — the pinned specimen of the issue */}
            <article data-reveal="" className="group lg:col-span-7">
              <Link
                to={`/blog/${blogs[0].slug}`}
                className="relative block overflow-hidden rounded-lg bg-ink-900"
              >
                <div className="aspect-[16/10] max-h-[26rem] overflow-hidden">
                  <img
                    src={
                      getMediaUrl(blogs[0].featured_image) ||
                      FALLBACK_BLOGS[0].featured_image!
                    }
                    alt={blogs[0].title}
                    loading="lazy"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).src =
                        FALLBACK_BLOGS[0].featured_image!;
                    }}
                    className="h-full w-full object-cover transition-transform duration-700 ease-out-expo group-hover:scale-[1.04]"
                  />
                </div>

                <span className="absolute top-4 left-4 rounded-sm bg-limestone-50/90 px-2.5 py-1 font-mono text-label text-ink-900 backdrop-blur-sm">
                  FIG. 01 — FIELD RECORD
                </span>
                <span
                  aria-hidden="true"
                  className="absolute right-4 bottom-4 hidden font-mono text-label text-limestone-300/80 sm:block"
                >
                  11.66° N · 78.14° E
                </span>

                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink-900/90 via-ink-900/45 to-transparent p-5 pt-16">
                  <div className="flex items-center gap-2.5 font-mono text-label text-limestone-300">
                    <span className="text-copper-500">
                      {blogs[0].category || "Field Note"}
                    </span>
                    <span>·</span>
                    <span>{blogs[0].reading_time || 5} min read</span>
                  </div>
                  <h3 className="mt-2 font-display text-2xl font-semibold leading-snug text-limestone-50">
                    {blogs[0].title}
                  </h3>
                </div>
              </Link>

              <p className="mt-4 text-sm leading-relaxed text-ink-600 line-clamp-2">
                {blogs[0].excerpt ||
                  "An inside look at how SashaInfinity designs interactive learning systems and conceptual frameworks."}
              </p>
              <div className="mt-3 flex items-center justify-between font-mono text-label text-ink-500">
                <span>
                  {blogs[0].created_at
                    ? new Date(blogs[0].created_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })
                    : "2026 Edition"}
                </span>
                <Link
                  to={`/blog/${blogs[0].slug}`}
                  className="text-ink-900 transition-colors duration-500 group-hover:text-copper-600"
                >
                  Read essay →
                </Link>
              </div>
            </article>

            {/* Entry ledger — the remaining notes, ruled like a journal index */}
            <div className="border-t border-ink-900/15 lg:col-span-5">
              {blogs.slice(1, 3).map((post, idx) => {
                const img =
                  getMediaUrl(post.featured_image) ||
                  FALLBACK_BLOGS[
                    (idx + 1) % FALLBACK_BLOGS.length
                  ].featured_image!;
                return (
                  <Link
                    key={post.id || post.slug}
                    to={`/blog/${post.slug}`}
                    data-reveal=""
                    style={{
                      ["--reveal-delay" as string]: `${(idx + 1) * 100}ms`,
                    }}
                    className="group flex items-center justify-between gap-5 border-b border-ink-900/15 py-6"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2.5 font-mono text-label text-ink-500">
                        <span className="text-copper-600">FN—0{idx + 2}</span>
                        <span>·</span>
                        <span>{post.category || "Field Note"}</span>
                        <span>·</span>
                        <span>{post.reading_time || 5} min</span>
                      </div>
                      <h3 className="mt-2 font-display text-lg font-semibold leading-snug text-ink-900 transition-colors duration-500 group-hover:text-copper-600">
                        {post.title}
                      </h3>
                      <p className="mt-1.5 text-xs leading-relaxed text-ink-600 line-clamp-1">
                        {post.excerpt ||
                          "An inside look at how SashaInfinity designs interactive learning systems."}
                      </p>
                    </div>

                    <span className="hidden size-14 shrink-0 overflow-hidden rounded-sm sm:block">
                      <img
                        src={img}
                        alt=""
                        loading="lazy"
                        className="h-full w-full object-cover transition-transform duration-700 ease-out-expo group-hover:scale-[1.06]"
                      />
                    </span>
                    <span
                      aria-hidden="true"
                      className="grid size-11 shrink-0 place-items-center rounded-full border border-ink-900/20 text-ink-900 transition-all duration-500 ease-out-expo group-hover:border-ink-900 group-hover:bg-ink-900 group-hover:text-limestone-50"
                    >
                      <ArrowUpRight size={16} />
                    </span>
                  </Link>
                );
              })}

              <div className="flex items-center justify-between pt-5 font-mono text-label text-ink-500">
                <span>
                  {blogs.length > 3
                    ? `+ ${blogs.length - 3} more entries`
                    : "Updated weekly from the studio"}
                </span>
                <Link
                  to="/blog"
                  className="inline-flex items-center gap-1 text-ink-900 transition-colors duration-500 hover:text-copper-600"
                >
                  Browse the archive
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>

          <NewsletterSection />
        </div>
      </section>

      {/* ====================================================================
          SI—07 — STICKY 12-COL FAQ ACCORDION
          ==================================================================== */}
      <section
        aria-labelledby="faq-heading"
        className="border-b border-ink-900/12 py-section"
      >
        <div className="container-page">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
            <div className="lg:col-span-4">
              <div className="lg:sticky lg:top-28">
                <div data-reveal="" className="mb-3 flex items-center gap-3">
                  <span className="font-mono text-label text-copper-500">
                    SI—07
                  </span>
                  <span className="sheet-label">Common Questions</span>
                </div>
                <SplitHeading
                  as="h2"
                  id="faq-heading"
                  text="Everything you ask before enrolling"
                  className="text-display-md tracking-tight text-ink-900"
                  italicLast={2}
                />
                <p data-reveal="" className="mt-3 text-sm text-ink-600">
                  Need a custom cohort blueprint for your school, university, or
                  engineering organization? Speak directly with our academic
                  directors.
                </p>
                <div data-reveal="" className="mt-6">
                  <SymphoButton
                    to="/contact"
                    variant="outline"
                    size="sm"
                    arrow
                  >
                    Ask a specific question
                  </SymphoButton>
                </div>
              </div>
            </div>

            <div className="divide-y divide-ink-900/12 border-y border-ink-900/12 lg:col-span-8">
              {FAQ_ITEMS.map((item, i) => (
                <details
                  key={item.q}
                  open={i === 0}
                  data-reveal=""
                  style={{ ["--reveal-delay" as string]: `${i * 60}ms` }}
                  className="group py-4"
                >
                  <summary className="flex cursor-pointer list-none items-start justify-between gap-6 text-left [&::-webkit-details-marker]:hidden">
                    <span className="flex items-baseline gap-3.5">
                      <span className="font-mono text-label text-copper-600">
                        0{i + 1}
                      </span>
                      <span className="font-display text-base font-semibold text-ink-900 transition-colors group-hover:text-copper-600">
                        {item.q}
                      </span>
                    </span>
                    <span
                      aria-hidden="true"
                      className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-pill border border-ink-900/20 text-ink-700 transition-transform duration-300 ease-out-expo group-open:rotate-45 group-open:bg-ink-900 group-open:text-limestone-50"
                    >
                      <svg
                        viewBox="0 0 12 12"
                        className="size-2.5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      >
                        <path d="M6 1v10M1 6h10" strokeLinecap="round" />
                      </svg>
                    </span>
                  </summary>
                  <div className="mt-3 pl-8 pr-6 text-sm leading-relaxed text-ink-600">
                    {item.a}
                  </div>
                </details>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          ARCHITECTURAL BLUEPRINT CTA BANNER
          ==================================================================== */}
      <SymphoCtaBanner />
    </div>
  );
}

export default HomePage;
