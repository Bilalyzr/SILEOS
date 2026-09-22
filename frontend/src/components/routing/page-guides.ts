import { normalizeRole, roleHomePath } from "@/utils/role-routing";
export interface PageGuideInfo {
  title: string;
  purpose: string;
  steps: [string, string, string];
  fallback: string;
}
type Rule = [RegExp, string, string, [string, string, string], string];
/** Home has nothing before it. Every other page gets the shared Back button,
 * except players/editors that already place their own return control in their
 * header (lesson player, lab workspace, course editors) — kept excluded so
 * the page never renders two back controls. */
export function needsPageBack(pathname: string, _search = ""): boolean {
  const path = pathname.replace(/\/$/, "") || "/";
  if (path === "/") return false;
  if (/^\/labs\/[^/]+$/.test(path) || /^\/courses\/[^/]+\/(learn|lessons)(\/|$)/.test(path) || /^\/(instructor|admin)\/courses\/[^/]+\/(edit|quiz-builder|assignment-builder)(\/|$)/.test(path)) return false;
  return true;
}
const rules: Rule[] = [
  [
    /\/exam-pricing(?:\/|$)/,
    "Exam paper pricing",
    "Control which JEE and NEET question ranges students can buy and the price per paper.",
    [
      "Create a question-count slab",
      "Set the price and publish it",
      "Edit or hide it for future purchases",
    ],
    "/admin/dashboard",
  ],
  [
    /\/exam-papers(?:\/|$)/,
    "Practice paper studio",
    "Students purchase one practice paper at a time. Teaching staff can prepare papers from their own text and PDFs.",
    [
      "Choose the exam and question count",
      "Add staff sources or complete checkout",
      "Generate, review and save your paper",
    ],
    "/dashboard",
  ],
  [
    /\/lab-studio(?:\/|$)/,
    "Lab Studio",
    "Create your own investigation, attach a GLB model and publish a reusable learning lab.",
    [
      "Choose a concept and write the investigation",
      "Upload or select a 3D model and preview",
      "Save a draft, then publish or export",
    ],
    "/labs",
  ],
  [
    /\/labs\/[^/]+/,
    "Lab investigation",
    "Explore the experiment, test your prediction and record what you discover.",
    [
      "Read the objective and predict",
      "Change controls or explore the 3D model",
      "Capture evidence and save your conclusion",
    ],
    "/labs",
  ],
  [
    /^\/labs\/?$/,
    "Learning labs",
    "Find interactive experiments by subject, class or curriculum chapter.",
    [
      "Choose a subject or chapter",
      "Open a linked experiment",
      "Investigate and record your observations",
    ],
    "/",
  ],
  [
    /\/course-packages/,
    "Course upload and backup",
    "Turn files into draft lessons or restore a complete Sasha course backup.",
    [
      "Upload course files or one backup",
      "Review the categorized preview",
      "Restore a new draft and check its lessons",
    ],
    "/instructor/courses",
  ],
  [
    /\/courses\/[^/]+\/edit|\/courses\/(create|new)|\/new-course/,
    "Course authoring",
    "Build a course with a unique link, structured curriculum and the right learning assets.",
    [
      "Set the title, course link and details",
      "Organize lessons and attach assets",
      "Preview, save and publish when ready",
    ],
    "/instructor/courses",
  ],
  [
    /^\/courses\/[^/]+/,
    "Course overview",
    "Review the curriculum, teaching format and access options before starting.",
    [
      "Review course details and prerequisites",
      "Enroll or open your existing access",
      "Choose a lesson and begin learning",
    ],
    "/courses",
  ],
  [
    /\/(lesson|learn|lessons)\b/,
    "Lesson workspace",
    "Work through the material and use the lesson resources to deepen your understanding.",
    [
      "Open the lesson content",
      "Practice and review supporting resources",
      "Save progress and continue the course",
    ],
    "/my-courses",
  ],
  [
    /\/(course-coverage|coverage)\b/,
    "Curriculum coverage",
    "Check how course lessons and assessments cover the intended learning concepts.",
    [
      "Select the course scope",
      "Review gaps in coverage",
      "Add or revise the linked learning activities",
    ],
    "/instructor/courses",
  ],
  [
    /\b(courses|my-courses|categories|category-[^/]+)\b/,
    "Course collection",
    "Find and organize learning experiences by topic, level and course type.",
    [
      "Search or filter the collection",
      "Open a course to review its details",
      "Continue learning or manage your course",
    ],
    "/",
  ],
  [
    /\b(recording-lessons)\b/,
    "Recording lessons",
    "Turn recorded teaching sessions into reusable lesson material.",
    [
      "Choose a recording",
      "Transcribe and review chapter boundaries",
      "Create draft lessons and review them",
    ],
    "/instructor/live-classes",
  ],
  [
    /\b(live|live-classes|past-classes)\b/,
    "Live teaching",
    "Manage scheduled sessions, join a class or review its recordings and attendance.",
    [
      "Choose or schedule a session",
      "Join and use the class activities",
      "Review attendance, recordings and follow-up",
    ],
    "/dashboard",
  ],
  [
    /\b(quiz|quizzes|quiz-builder|quiz-taking|assessment-studio|assignment-builder)\b/,
    "Assessment workspace",
    "Prepare or complete assessments with clear questions, scoring and feedback.",
    [
      "Review instructions or select a question type",
      "Build or complete the assessment",
      "Review answers, feedback and results",
    ],
    "/dashboard",
  ],
  [
    /\b(assignment|assignments|assignment-submission)\b/,
    "Assignment workspace",
    "Use the instructions and reference material to prepare a complete submission.",
    [
      "Read the requirements and due date",
      "Prepare your work and attachments",
      "Submit and check feedback",
    ],
    "/my-courses",
  ],
  [
    /\b(grading|grading-queue|assignment-grading|gradebook|review-queue|interventions)\b/,
    "Review and learner support",
    "Review learner work, resolve pending feedback and choose the next teaching action.",
    [
      "Filter the pending work",
      "Review the evidence and add feedback",
      "Record a decision or follow-up action",
    ],
    "/instructor/dashboard",
  ],
  [
    /\b(three-d-tasks|h5p|games|game-builder|content-libraries|meiporul-ar)\b/,
    "Interactive content library",
    "Build and manage reusable 3D models, games and interactive activities.",
    [
      "Choose a content type",
      "Upload or author and preview it",
      "Save and attach it to a learning activity",
    ],
    "/instructor/courses",
  ],
  [
    /\b(ebooks|library|my-library)\b/,
    "Reading and resources",
    "Browse learning resources or prepare books and notes for your learners.",
    [
      "Search or categorize resources",
      "Review the details and available files",
      "Open your resource or publish staff content",
    ],
    "/courses",
  ],
  [
    /\b(certificate|certificates|certificate-designer|verify-certificate)\b/,
    "Certificates",
    "Design, view or verify learning credentials with the relevant course evidence.",
    [
      "Choose the certificate or template",
      "Review its details and eligibility",
      "Save, download or verify the result",
    ],
    "/dashboard",
  ],
  [
    /\b(checkout|cart|wishlist|orders|coupons|bundles|membership|memberships|company-invoices|billing|payments|payouts|my-vouchers)\b/,
    "Purchases and access",
    "Review prices, entitlements and purchase status before confirming an action.",
    [
      "Review the selected items or records",
      "Check pricing and access details",
      "Confirm the action and review its status",
    ],
    "/courses",
  ],
  [
    /\b(my-plan|my-mastery|my-grades|analytics|insights|leaderboard|hall-of-fame|student-activity)\b/,
    "Learning progress",
    "Use progress and achievement information to decide what to work on next.",
    [
      "Select the learner or time range",
      "Review evidence and progress",
      "Choose the next learning or support action",
    ],
    "/dashboard",
  ],
  [
    /\b(internships|internship|my-internships|internship-profile|internship-inbox|internship-requests|for-companies|company|companies|cohort|cohorts|colleges|spocs)\b/,
    "Career and organization workspace",
    "Connect learners, organizations and practical work with clear responsibilities and records.",
    [
      "Choose the opportunity, cohort or organization",
      "Review details, eligibility and activity",
      "Apply, assign or record the next step",
    ],
    "/dashboard",
  ],
  [
    /\b(messages|inbox|blog|blogs|blog-templates|blog-editor)\b/,
    "Communication and publishing",
    "Share useful updates and content with the appropriate audience.",
    [
      "Choose a conversation or publication",
      "Read or prepare the content",
      "Review the audience before sending or publishing",
    ],
    "/dashboard",
  ],
  [
    /\b(profile|settings)\b/,
    "Account and preferences",
    "Keep account information, preferences and available settings up to date.",
    [
      "Choose the section to update",
      "Review and edit the relevant fields",
      "Save and check the confirmation",
    ],
    "/dashboard",
  ],
  [
    /\b(students|instructors|admins|manage|approvals|enrollments|users)\b/,
    "People and permissions",
    "Manage the people, roles and course access within your authorized scope.",
    [
      "Search or filter people and requests",
      "Review the profile and current access",
      "Apply the appropriate update or decision",
    ],
    "/admin/dashboard",
  ],
  [
    /\b(operations|audit|security)\b/,
    "Operations and audit",
    "Inspect service health, background work and administrative records.",
    [
      "Select the service or audit range",
      "Read the status and supporting evidence",
      "Resolve an issue and verify the outcome",
    ],
    "/admin/dashboard",
  ],
  [
    /\b(login|register|verify-email|forgot-password|reset-password|linkedin-callback|signup)\b/,
    "Account access",
    "Sign in, create an account or complete the requested verification step.",
    [
      "Enter the requested account details",
      "Complete any verification",
      "Continue to your workspace",
    ],
    "/",
  ],
  [
    /\b(terms|privacy|refund-policy|shipping)\b/,
    "Policies and information",
    "Read the service information that applies to your account and purchases.",
    [
      "Find the relevant section",
      "Review the policy details",
      "Return to your activity or contact support",
    ],
    "/",
  ],
  [
    /\b(search)\b/,
    "Search learning content",
    "Find courses and learning resources using a topic or keyword.",
    [
      "Enter a search term",
      "Review matching resources",
      "Open the result that matches your goal",
    ],
    "/",
  ],
  [
    /\b(about|contact)\b/,
    "About SashaInfinity",
    "Learn about the platform and find the right way to get help.",
    [
      "Review the platform information",
      "Find the relevant service or contact",
      "Continue exploring or send an enquiry",
    ],
    "/",
  ],
  [
    /\b(dashboard|parent|spoc|superadmin|admin)\b/,
    "Workspace overview",
    "See your priorities and open the tools available for your role.",
    [
      "Review the overview and pending work",
      "Choose a section from navigation",
      "Complete an action and check its result",
    ],
    "/",
  ],
  [
    /^\/$/,
    "Learn, practice and build",
    "Discover courses, interactive labs and practical opportunities in one learning workspace.",
    [
      "Explore a subject or skill",
      "Choose a course or hands-on lab",
      "Start learning and track your progress",
    ],
    "/courses",
  ],
];

export function pageGuide(pathname: string): PageGuideInfo {
  const match = rules.find(([pattern]) => pattern.test(pathname));
  if (match)
    return {
      title: match[1],
      purpose: match[2],
      steps: match[3],
      fallback: match[4],
    };
  return {
    title: "Find your next step",
    purpose:
      "This page helps you continue your learning journey or return to an available workspace.",
    steps: [
      "Review the information on this page",
      "Choose an available action",
      "Return to your previous page when finished",
    ],
    fallback: "/",
  };
}

export function safeBackFallback(pathname: string, role?: string): string {
  role = normalizeRole(role);
  const fallback = pageGuide(pathname).fallback;
  const home =
    role === "parent" ? "/parent/dashboard" : role ? roleHomePath(role) : "/";
  if (
    fallback === "/dashboard" ||
    (fallback.startsWith("/instructor") &&
      !["instructor", "admin", "superadmin"].includes(role || "")) ||
    (fallback.startsWith("/admin") &&
      !["admin", "superadmin"].includes(role || ""))
  )
    return pathname === home ? "/courses" : home;
  if (role === "admin" && fallback === "/instructor/courses")
    return "/admin/courses";
  return fallback === pathname
    ? home === pathname
      ? "/courses"
      : home
    : fallback;
}
