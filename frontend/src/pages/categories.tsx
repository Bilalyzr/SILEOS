import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Code2,
  Smartphone,
  BarChart3,
  Palette,
  Briefcase,
  Camera,
  Box,
  Cpu,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoDimensionLine,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

interface Category {
  id: number;
  code: string;
  name: string;
  slug: string;
  description: string;
  course_count: number;
  icon: LucideIcon;
}

const triadPillars = [
  {
    code: "TR—01",
    tamil: "மெய்ப்பொருள்",
    name: "Meiporul",
    subtitle: "Spatial & Conceptual Truth",
    to: "/meiporul",
    arTo: "/meiporul-ar",
    description:
      "3D WebGL and Augmented Reality visualizations that make mathematical surfaces, vectors, and physical laws directly observable in space.",
    icon: Box,
  },
  {
    code: "TR—02",
    tamil: "உட்பொருள்",
    name: "Utporul",
    subtitle: "Core Theoretical Essence",
    to: "/utporul",
    description:
      "First-principles foundations, analytical reasoning, exam mastery, and deep algorithmic invariants taught without shortcuts.",
    icon: Cpu,
  },
  {
    code: "TR—03",
    tamil: "செயப்படுபொருள்",
    name: "Seyappaduporul",
    subtitle: "Applied Engineering & Execution",
    to: "/seyappaduporul",
    description:
      "Live mentor-led tuition, production software construction, laboratory experimentation, and real-world system deployment.",
    icon: Wrench,
  },
];

const categories: Category[] = [
  {
    id: 1,
    code: "SUB—01",
    name: "Web Development",
    slug: "web-development",
    description:
      "Modern full-stack web engineering including React, TypeScript, FastAPI, distributed APIs, and cloud-native deployment.",
    course_count: 45,
    icon: Code2,
  },
  {
    id: 2,
    code: "SUB—02",
    name: "Mobile Development",
    slug: "mobile-development",
    description:
      "Build high-frame-rate mobile applications for iOS and Android using Flutter, React Native, and native system SDKs.",
    course_count: 32,
    icon: Smartphone,
  },
  {
    id: 3,
    code: "SUB—03",
    name: "Data Science & AI",
    slug: "data-science",
    description:
      "Master statistical modeling, machine learning, neural networks, and applied AI with Python, PyTorch, and TensorFlow.",
    course_count: 28,
    icon: BarChart3,
  },
  {
    id: 4,
    code: "SUB—04",
    name: "Product & Spatial Design",
    slug: "design",
    description:
      "Architectural UI/UX systems, interaction typography, 3D modeling, and design engineering workflows.",
    course_count: 21,
    icon: Palette,
  },
  {
    id: 5,
    code: "SUB—05",
    name: "Business & Systems Strategy",
    slug: "business",
    description:
      "Technical product management, entrepreneurship, operational telemetry, and organizational leadership.",
    course_count: 38,
    icon: Briefcase,
  },
  {
    id: 6,
    code: "SUB—06",
    name: "Visual Media & Storytelling",
    slug: "photography",
    description:
      "Cinematography, technical composition, lighting physics, and digital post-production pipelines.",
    course_count: 19,
    icon: Camera,
  },
];

export function CategoriesPage() {
  return (
    <div className="sympho-scope min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—SUB"
        eyebrow="Subjects & Knowledge Taxonomy"
        title="Disciplines organized by conceptual depth & execution"
        lede="Explore our classical three-pillar Tamil Knowledge Triad alongside specialized engineering, mathematics, design, and scientific subject tracks."
        drawingCode="SHEET SI—SUB · TAXONOMY"
        badge="183+ Active Modules"
        specs={[
          { label: "Total Courses", value: "183 Programs" },
          { label: "Active Learners", value: "15,000+" },
          { label: "Curriculum Depth", value: "2,000+ Hours" },
          { label: "Architecture", value: "Triad + 6 Tracks" },
        ]}
        primaryAction={
          <SymphoButton to="/courses" variant="on-dark" arrow>
            Browse all courses
          </SymphoButton>
        }
        secondaryAction={
          <SymphoButton to="/meiporul-ar" variant="outline-dark">
            Explore 3D AR Studio
          </SymphoButton>
        }
      />

      {/* Section 01: The Tamil Knowledge Triad */}
      <section className="border-b border-ink-900/10 py-section">
        <div className="container-page">
          <SymphoSectionHeader
            index="SI—01"
            eyebrow="Philosophical Foundation"
            title="The Tamil Knowledge Triad"
            lede="Every subject at SashaInfinity is anchored in three classical epistemological dimensions — ensuring learners grasp what a concept is, why it holds true, and how to build with it."
          />

          <div className="mt-16 grid grid-cols-1 gap-8 lg:grid-cols-3">
            {triadPillars.map((pillar) => {
              const Icon = pillar.icon;
              return (
                <article
                  key={pillar.code}
                  className="sheet-frame group flex flex-col justify-between rounded-lg border border-ink-900/15 bg-limestone-50 p-8 transition-all duration-300 hover:-translate-y-1 hover:shadow-lift"
                >
                  <div>
                    <div className="flex items-center justify-between border-b border-ink-900/10 pb-4">
                      <span className="font-mono text-label text-copper-600">
                        {pillar.code} · {pillar.tamil}
                      </span>
                      <span className="grid size-10 place-items-center rounded-md border border-ink-900/15 bg-limestone-100 text-ink-900 group-hover:bg-ink-900 group-hover:text-limestone-50">
                        <Icon size={18} />
                      </span>
                    </div>

                    <p className="mt-5 font-mono text-xs uppercase tracking-wider text-ink-500">
                      {pillar.subtitle}
                    </p>
                    <h3 className="mt-1 font-display text-display-sm font-light text-ink-900 group-hover:text-copper-600">
                      {pillar.name}
                    </h3>
                    <p className="mt-3 text-sm leading-relaxed text-ink-600">
                      {pillar.description}
                    </p>
                  </div>

                  <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-ink-900/10 pt-5">
                    <Link
                      to={pillar.to}
                      className="inline-flex items-center gap-1.5 font-mono text-label text-ink-900 hover:text-copper-600"
                    >
                      <span>Explore {pillar.name}</span>
                      <ArrowUpRight size={14} />
                    </Link>
                    {pillar.arTo && (
                      <Link
                        to={pillar.arTo}
                        className="rounded-pill border border-copper-500/40 bg-copper-200/30 px-3 py-1 font-mono text-[0.65rem] uppercase text-copper-600 hover:bg-copper-500 hover:text-limestone-50"
                      >
                        3D AR Gallery
                      </Link>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* Section 02: Platform Figures */}
      <section className="border-b border-ink-900/10 py-14">
        <div className="container-page">
          <div className="grid grid-cols-1 gap-10 sm:grid-cols-3">
            {[
              { num: "183", suffix: "+", label: "Total Courses", note: "Curated across 6 core tracks" },
              { num: "15,000", suffix: "+", label: "Active Students", note: "Across schools, colleges & cohorts" },
              { num: "2,000", suffix: "+", label: "Hours of Content", note: "Lectures, labs & 3D simulations" },
            ].map((stat, i) => (
              <div
                key={stat.label}
                className={
                  i < 2 ? "sm:border-r sm:border-ink-900/10 sm:pr-8" : ""
                }
              >
                <div className="font-display text-display-lg font-light text-ink-900">
                  {stat.num}
                  <span className="text-copper-500">{stat.suffix}</span>
                </div>
                <SymphoDimensionLine />
                <div className="mt-3 font-sans text-base font-semibold text-ink-900">
                  {stat.label}
                </div>
                <p className="text-sm text-ink-500">{stat.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 03: Subject Tracks Grid */}
      <section className="py-section">
        <div className="container-page">
          <SymphoSectionHeader
            index="SI—02"
            eyebrow="Subject Catalog"
            title="Six specialized domain tracks"
            lede="Select a discipline below to filter the course catalog by domain expertise."
          />

          <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
            {categories.map((category) => {
              const Icon = category.icon;
              return (
                <Link
                  key={category.id}
                  to={`/courses?category=${category.slug}`}
                  className="sheet-frame group flex flex-col justify-between rounded-lg border border-ink-900/15 bg-limestone-50 p-7 transition-all duration-300 hover:-translate-y-1 hover:shadow-lift"
                >
                  <div>
                    <div className="flex items-center justify-between border-b border-ink-900/10 pb-4">
                      <span className="font-mono text-label text-copper-600">
                        {category.code}
                      </span>
                      <span className="grid size-10 place-items-center rounded-md border border-ink-900/15 bg-limestone-100 text-ink-900 transition-colors group-hover:bg-ink-900 group-hover:text-limestone-50">
                        <Icon size={18} aria-hidden="true" />
                      </span>
                    </div>

                    <h3 className="mt-5 font-display text-2xl font-normal text-ink-900 transition-colors group-hover:text-copper-600">
                      {category.name}
                    </h3>
                    <p className="mt-2.5 text-sm leading-relaxed text-ink-600">
                      {category.description}
                    </p>
                  </div>

                  <div className="mt-8 flex items-center justify-between border-t border-ink-900/10 pt-4">
                    <span className="rounded-pill border border-ink-900/15 bg-limestone-100 px-3 py-1 font-mono text-label text-ink-700">
                      {category.course_count} courses
                    </span>
                    <span className="inline-flex items-center gap-1 font-mono text-label text-ink-900 group-hover:text-copper-600">
                      Explore <ArrowUpRight size={14} />
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        eyebrow="Ready to Start Learning?"
        title="Join thousands of learners building enduring engineering skills"
        description="Browse our full catalog of courses or unlock multi-course mastery bundles."
        primaryText="Browse All Courses"
        primaryTo="/courses"
        secondaryText="Explore Learning Labs"
        secondaryTo="/labs"
      />
    </div>
  );
}
