import { lazyPage } from "@/components/routing/lazy-page";
import { StudentLiveProvider } from '@/components/live/StudentLiveClasses';
import { AstraRouteTheme } from "@/components/design-system/AstraRouteTheme";
import React from "react";
const LabsPage = lazyPage(() => import("@/pages/labs"));
const InstitutionsPage = lazyPage(() => import("@/pages/institutions"));
const CampusForInstitutionsPage = lazyPage(() => import("@/pages/campus-for-institutions"));
const HelpPage = lazyPage(() => import("@/pages/help"));
const LabWorkspace = lazyPage(() => import("@/pages/lab-workspace"));
const LabStudioPage = lazyPage(() => import("@/pages/instructor/lab-studio"));
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
  QueryCache,
  MutationCache,
} from "@tanstack/react-query";
import { AuthProvider } from "@/hooks/use-auth";
import { CartProvider } from "@/contexts/CartContext";
import { ConfirmProvider } from "@/components/ui/confirm";
import {
  ProtectedRoute,
  StudentRoute,
} from "@/components/routing/protected-route";
import { ProfileCompletionGuard } from "@/components/auth/ProfileCompletionGuard";
import { MainLayout } from "@/components/layout/main-layout";
import {
  StudentLayout,
  InstructorLayout,
  SpocLayout,
  AutoRoleLayout,
} from "@/components/dashboard/RoleLayouts";
import { AuthLayout } from "@/components/layout/auth-layout";
const LinkedInCallbackPage = lazyPage(() =>
  import("@/pages/auth/linkedin-callback").then((m) => ({
    default: m.LinkedInCallbackPage,
  })),
);
import { Toaster } from "react-hot-toast";
import ScrollToTop from "@/components/common/scroll-to-top";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { usePageViewTracker } from "@/hooks/use-page-view-tracker";

// Pages
const HomePage = lazyPage(() =>
  import("@/pages/Home").then((m) => ({ default: m.HomePage })),
);
const CoursesPage = lazyPage(() =>
  import("@/pages/courses").then((m) => ({ default: m.CoursesPage })),
);
const CourseDetailPage = lazyPage(() =>
  import("@/pages/course-detail").then((m) => ({
    default: m.CourseDetailPage,
  })),
);
const CategoriesPage = lazyPage(() =>
  import("@/pages/categories").then((m) => ({ default: m.CategoriesPage })),
);
const LoginPage = lazyPage(() =>
  import("@/pages/auth/login").then((m) => ({ default: m.LoginPage })),
);
const RegisterPage = lazyPage(() =>
  import("@/pages/auth/register").then((m) => ({ default: m.RegisterPage })),
);
const VerifyEmailPage = lazyPage(() =>
  import("@/pages/auth/verify-email").then((m) => ({
    default: m.VerifyEmailPage,
  })),
);
const ForgotPasswordPage = lazyPage(() =>
  import("@/pages/auth/forgot-password").then((m) => ({
    default: m.ForgotPasswordPage,
  })),
);
const ResetPasswordPage = lazyPage(() =>
  import("@/pages/auth/reset-password").then((m) => ({
    default: m.ResetPasswordPage,
  })),
);
const DashboardPage = lazyPage(() =>
  import("@/pages/dashboard").then((m) => ({ default: m.DashboardPage })),
);
const StudentAnalyticsPage = lazyPage(() =>
  import("@/pages/dashboard/analytics").then((m) => ({
    default: m.StudentAnalyticsPage,
  })),
);
const LeaderboardPage = lazyPage(() =>
  import("@/pages/leaderboard").then((m) => ({ default: m.LeaderboardPage })),
);
const GamePlayPage = lazyPage(() => import("@/pages/game-play"));
const MyCoursesPage = lazyPage(() =>
  import("@/pages/my-courses").then((m) => ({ default: m.MyCoursesPage })),
);
const WishlistPage = lazyPage(() =>
  import("@/pages/wishlist").then((m) => ({ default: m.WishlistPage })),
);
const CartPage = lazyPage(() =>
  import("@/pages/cart").then((m) => ({ default: m.CartPage })),
);
const CheckoutPage = lazyPage(() =>
  import("@/pages/checkout").then((m) => ({ default: m.CheckoutPage })),
);
const MembershipPage = lazyPage(() => import("@/pages/membership"));
const BundlesPage = lazyPage(() => import("@/pages/bundles"));
const BundleDetailPage = lazyPage(() => import("@/pages/bundle-detail"));
const ProfilePage = lazyPage(() =>
  import("@/pages/profile").then((m) => ({ default: m.ProfilePage })),
);
const SettingsPage = lazyPage(() =>
  import("@/pages/settings").then((m) => ({ default: m.SettingsPage })),
);
const CommunicationPreferencesPage = lazyPage(() =>
  import("@/pages/communication-preferences").then((m) => ({
    default: m.CommunicationPreferencesPage,
  })),
);
const AdminCommunicationsPage = lazyPage(() =>
  import("@/pages/admin/communications").then((m) => ({
    default: m.AdminCommunicationsPage,
  })),
);
const LessonPageRedesigned = lazyPage(() =>
  import("@/pages/lesson-redesigned").then((m) => ({
    default: m.LessonPageRedesigned,
  })),
);
const CertificatePage = lazyPage(() =>
  import("@/pages/certificate").then((m) => ({ default: m.CertificatePage })),
);
const QuizTaking = lazyPage(() => import("@/pages/quiz-taking"));
const AssignmentSubmission = lazyPage(
  () => import("@/pages/assignment-submission"),
);
const SearchPage = lazyPage(() =>
  import("@/pages/search").then((m) => ({ default: m.SearchPage })),
);
const AboutPage = lazyPage(() =>
  import("@/pages/About").then((m) => ({ default: m.AboutPage })),
);
const ContactPage = lazyPage(() =>
  import("@/pages/Contact").then((m) => ({ default: m.ContactPage })),
);
const NotFoundPage = lazyPage(() =>
  import("@/pages/not-found").then((m) => ({ default: m.NotFoundPage })),
);
const VerifyCertificate = lazyPage(() => import("@/pages/verify-certificate"));
const BlogPage = lazyPage(() =>
  import("@/pages/blog").then((m) => ({ default: m.BlogPage })),
);
const BlogDetailPage = lazyPage(() =>
  import("@/pages/blog-detail").then((m) => ({ default: m.BlogDetailPage })),
);
const UtporulPage = lazyPage(() =>
  import("@/pages/category-utporul").then((m) => ({ default: m.UtporulPage })),
);
const MeiporulPage = lazyPage(() =>
  import("@/pages/category-meiporul").then((m) => ({
    default: m.MeiporulPage,
  })),
);
const MeiporulARPage = lazyPage(() =>
  import("@/pages/meiporul-ar").then((m) => ({ default: m.MeiporulARPage })),
);
const SeyappaduporulPage = lazyPage(() =>
  import("@/pages/category-seyappaduporul").then((m) => ({
    default: m.SeyappaduporulPage,
  })),
);
const RefundPolicyPage = lazyPage(() =>
  import("@/pages/refund-policy").then((m) => ({
    default: m.RefundPolicyPage,
  })),
);
const TermsPage = lazyPage(() =>
  import("@/pages/terms").then((m) => ({ default: m.TermsPage })),
);
const PrivacyPage = lazyPage(() =>
  import("@/pages/privacy").then((m) => ({ default: m.PrivacyPage })),
);
const ShippingPage = lazyPage(() =>
  import("@/pages/shipping").then((m) => ({ default: m.ShippingPage })),
);
const InstructorProfilePage = lazyPage(() =>
  import("@/pages/instructor-profile").then((m) => ({
    default: m.InstructorProfilePage,
  })),
);
const PublicProfilePage = lazyPage(() =>
  import("@/pages/public-profile").then((m) => ({
    default: m.PublicProfilePage,
  })),
);

// Instructor Pages
const InstructorBlogPage = lazyPage(() =>
  import("@/pages/instructor/blog").then((m) => ({
    default: m.InstructorBlogPage,
  })),
);
const BlogEditorPage = lazyPage(() =>
  import("@/pages/instructor/blog-editor").then((m) => ({
    default: m.BlogEditorPage,
  })),
);
const InstructorDashboard = lazyPage(() =>
  import("@/pages/instructor/dashboard").then((m) => ({
    default: m.InstructorDashboard,
  })),
);
const InstructorCourses = lazyPage(() =>
  import("@/pages/instructor/courses").then((m) => ({
    default: m.InstructorCourses,
  })),
);
const CourseStartPage = lazyPage(
  () => import("@/pages/instructor/course-start"),
);
const PastClassesPage = lazyPage(
  () => import("@/pages/instructor/past-classes"),
);
const MyGradesPage = lazyPage(() => import("@/pages/student/my-grades"));
const MyMasteryPage = lazyPage(() => import("@/pages/student/my-mastery"));
const LearningPlanPage = lazyPage(
  () => import("@/pages/student/learning-plan"),
);
const InterventionsPage = lazyPage(
  () => import("@/pages/instructor/interventions"),
);
const AssessmentStudio = lazyPage(
  () => import("@/pages/instructor/assessment-studio"),
);
const RecordingLessons = lazyPage(
  () => import("@/pages/instructor/recording-lessons"),
);
const ExamPapers = lazyPage(() => import("@/pages/exam-papers"));
const ExamPricing = lazyPage(() => import("@/pages/admin/exam-pricing"));
const CoursePackages = lazyPage(
  () => import("@/pages/instructor/course-packages"),
);
const OperationsCenter = lazyPage(() => import("@/pages/admin/operations"));
const RecordingLessonPage = lazyPage(() => import("@/pages/recording-lesson"));
const CourseCoveragePage = lazyPage(
  () => import("@/pages/instructor/course-coverage"),
);
const InsightsPage = lazyPage(() => import("@/pages/instructor/insights"));
const ParentDashboard = lazyPage(() => import("@/pages/parent/dashboard"));
const EditCourse = lazyPage(() =>
  import("@/pages/instructor/edit-course").then((m) => ({
    default: m.EditCourse,
  })),
);
const InstructorStudents = lazyPage(() =>
  import("@/pages/instructor/students").then((m) => ({
    default: m.InstructorStudents,
  })),
);
const InstructorAnalytics = lazyPage(() =>
  import("@/pages/instructor/analytics").then((m) => ({
    default: m.InstructorAnalytics,
  })),
);
const QuizBuilder = lazyPage(() => import("@/pages/instructor/quiz-builder"));
const AssignmentBuilder = lazyPage(
  () => import("@/pages/instructor/assignment-builder"),
);
const AssignmentGrading = lazyPage(
  () => import("@/pages/instructor/assignment-grading"),
);
const InstructorGradebookPage = lazyPage(
  () => import("@/pages/instructor/gradebook"),
);
const InstructorGradingQueuePage = lazyPage(
  () => import("@/pages/instructor/grading-queue"),
);
const InstructorGradingPickerPage = lazyPage(
  () => import("@/pages/instructor/grading"),
);
const InstructorLiveClassesPage = lazyPage(() =>
  import("@/pages/instructor/live-classes").then((m) => ({
    default: m.InstructorLiveClassesPage,
  })),
);
const InstructorLiveClassNewPage = lazyPage(() =>
  import("@/pages/instructor/live-class-new").then((m) => ({
    default: m.InstructorLiveClassNewPage,
  })),
);
const InstructorLiveClassConsolePage = lazyPage(() =>
  import("@/pages/instructor/live-class-console").then((m) => ({
    default: m.InstructorLiveClassConsolePage,
  })),
);
const InstructorLiveClassReportPage = lazyPage(() =>
  import("@/pages/instructor/live-class-report").then((m) => ({
    default: m.InstructorLiveClassReportPage,
  })),
);
const InstructorCertificateDesignerPage = lazyPage(
  () => import("@/pages/instructor/certificate-designer"),
);
const InstructorGamesPage = lazyPage(() => import("@/pages/instructor/games"));
const InstructorThreeDTasksPage = lazyPage(
  () => import("@/pages/instructor/three-d-tasks"),
);
const ReviewQueuePage = lazyPage(
  () => import("@/pages/instructor/review-queue"),
);
const InstructorH5PLibraryPage = lazyPage(
  () => import("@/pages/instructor/h5p-library"),
);
const LibraryPage = lazyPage(() => import("@/pages/library"));
const LibraryDetailPage = lazyPage(() => import("@/pages/library-detail"));
const MyLibraryPage = lazyPage(() => import("@/pages/my-library"));
const InstructorEbooksPage = lazyPage(
  () => import("@/pages/instructor/ebooks"),
);
const GameBuilderPage = lazyPage(
  () => import("@/pages/instructor/game-builder"),
);

// Student Pages
const StudentBlogCreate = lazyPage(() =>
  import("@/pages/student/blog-create").then((m) => ({
    default: m.StudentBlogCreate,
  })),
);
const StudentLiveClassesPage = lazyPage(() =>
  import("@/pages/student/live-classes").then((m) => ({
    default: m.StudentLiveClassesPage,
  })),
);
const StudentLiveClassJoinPage = lazyPage(() =>
  import("@/pages/student/live-class-join").then((m) => ({
    default: m.StudentLiveClassJoinPage,
  })),
);
const StudentLiveClassRecordingPage = lazyPage(() =>
  import("@/pages/student/live-class-recording").then((m) => ({
    default: m.StudentLiveClassRecordingPage,
  })),
);

// Admin Pages
import { AdminLayout } from "@/components/layout/admin/admin-layout";
import { SuperAdminLayout } from "@/components/layout/admin/superadmin-layout";
const AdminDashboard = lazyPage(() =>
  import("@/pages/admin/dashboard").then((m) => ({
    default: m.AdminDashboard,
  })),
);
const AdminCourses = lazyPage(() =>
  import("@/pages/admin/courses").then((m) => ({ default: m.AdminCourses })),
);
const AdminStudentActivity = lazyPage(() =>
  import("@/pages/admin/student-activity").then((m) => ({
    default: m.AdminStudentActivity,
  })),
);
const AdminCourseReviews = lazyPage(() =>
  import("@/pages/admin/reviews").then((m) => ({
    default: m.AdminCourseReviews,
  })),
);
const AdminNewCourse = lazyPage(() =>
  import("@/pages/admin/new-course").then((m) => ({
    default: m.AdminNewCourse,
  })),
);
const AdminStudents = lazyPage(() =>
  import("@/pages/admin/students").then((m) => ({ default: m.AdminStudents })),
);
const AdminApprovals = lazyPage(() =>
  import("@/pages/admin/approvals").then((m) => ({
    default: m.AdminApprovals,
  })),
);
const AdminInstructors = lazyPage(() =>
  import("@/pages/admin/instructors").then((m) => ({
    default: m.AdminInstructors,
  })),
);
const AdminManage = lazyPage(() =>
  import("@/pages/admin/manage").then((m) => ({ default: m.AdminManage })),
);
const AdminEnrollments = lazyPage(() =>
  import("@/pages/admin/enrollments").then((m) => ({
    default: m.AdminEnrollments,
  })),
);
const AdminCategories = lazyPage(() =>
  import("@/pages/admin/categories").then((m) => ({
    default: m.AdminCategories,
  })),
);
const AdminTags = lazyPage(() =>
  import("@/pages/admin/tags").then((m) => ({ default: m.AdminTags })),
);
const AdminAnalytics = lazyPage(() =>
  import("@/pages/admin/analytics").then((m) => ({
    default: m.AdminAnalytics,
  })),
);
const AdminOrders = lazyPage(() =>
  import("@/pages/admin/orders").then((m) => ({ default: m.AdminOrders })),
);
const AdminLessons = lazyPage(() =>
  import("@/pages/admin/lessons").then((m) => ({ default: m.AdminLessons })),
);
const AdminQuizzes = lazyPage(() =>
  import("@/pages/admin/quizzes").then((m) => ({ default: m.AdminQuizzes })),
);
const AdminCertificates = lazyPage(() =>
  import("@/pages/admin/certificates").then((m) => ({
    default: m.AdminCertificates,
  })),
);
const AdminSettings = lazyPage(() =>
  import("@/pages/admin/settings").then((m) => ({ default: m.AdminSettings })),
);
const CouponsPage = lazyPage(() =>
  import("@/pages/admin/coupons").then((m) => ({ default: m.CouponsPage })),
);
const MembershipsPage = lazyPage(() =>
  import("@/pages/admin/memberships").then((m) => ({
    default: m.MembershipsPage,
  })),
);
const AdminBundlesPage = lazyPage(() =>
  import("@/pages/admin/bundles").then((m) => ({ default: m.BundlesPage })),
);
const AdminContentLibrariesPage = lazyPage(() =>
  import("@/pages/admin/content-libraries").then((m) => ({
    default: m.AdminContentLibrariesPage,
  })),
);
const AdminCompanyInvoicesPage = lazyPage(() =>
  import("@/pages/admin/company-invoices").then((m) => ({
    default: m.CompanyInvoicesPage,
  })),
);
const AdminBlogs = lazyPage(() =>
  import("@/pages/admin/blogs").then((m) => ({ default: m.AdminBlogs })),
);
const AdminHallOfFame = lazyPage(() =>
  import("@/pages/admin/hall-of-fame").then((m) => ({
    default: m.AdminHallOfFame,
  })),
);
const AdminBlogTemplates = lazyPage(() =>
  import("@/pages/admin/blog-templates").then((m) => ({
    default: m.AdminBlogTemplates,
  })),
);
const AdminInternships = lazyPage(() =>
  import("@/pages/admin/internships").then((m) => ({
    default: m.AdminInternships,
  })),
);
const AdminInternshipRequests = lazyPage(() =>
  import("@/pages/admin/internship-requests").then((m) => ({
    default: m.AdminInternshipRequests,
  })),
);
const AdminColleges = lazyPage(() =>
  import("@/pages/admin/colleges").then((m) => ({ default: m.AdminColleges })),
);
const AdminCohorts = lazyPage(() =>
  import("@/pages/admin/cohorts").then((m) => ({ default: m.AdminCohorts })),
);
const AdminSpocs = lazyPage(() =>
  import("@/pages/admin/spocs").then((m) => ({ default: m.AdminSpocs })),
);

// SPOC Pages
const SpocDashboard = lazyPage(() =>
  import("@/pages/spoc/dashboard").then((m) => ({ default: m.SpocDashboard })),
);
const SpocCohortDetail = lazyPage(() =>
  import("@/pages/spoc/cohort").then((m) => ({ default: m.SpocCohortDetail })),
);
const SpocInternshipDetail = lazyPage(() =>
  import("@/pages/spoc/internship").then((m) => ({
    default: m.SpocInternshipDetail,
  })),
);
const SpocBlogPage = lazyPage(() =>
  import("@/pages/spoc/blog").then((m) => ({ default: m.SpocBlogPage })),
);
const SpocProfilePage = lazyPage(() =>
  import("@/pages/spoc/profile").then((m) => ({ default: m.SpocProfilePage })),
);

// Internship Pages (public)
const InternshipsPage = lazyPage(() =>
  import("@/pages/internships").then((m) => ({ default: m.InternshipsPage })),
);
const InternshipDetailPage = lazyPage(() =>
  import("@/pages/internship-detail").then((m) => ({
    default: m.InternshipDetailPage,
  })),
);

// Candidate / Internship profile (SS2)
const InternshipProfilePage = lazyPage(() =>
  import("@/pages/dashboard/internship-profile").then((m) => ({
    default: m.InternshipProfilePage,
  })),
);
const MyVouchersPage = lazyPage(() =>
  import("@/pages/dashboard/my-vouchers").then((m) => ({
    default: m.MyVouchersPage,
  })),
);
const MyInternshipsPage = lazyPage(() =>
  import("@/pages/dashboard/my-internships").then((m) => ({
    default: m.MyInternshipsPage,
  })),
);
const MyInternshipDetailPage = lazyPage(() =>
  import("@/pages/dashboard/my-internship-detail").then((m) => ({
    default: m.MyInternshipDetailPage,
  })),
);

// SS3 — Company portal + marketplace
const ForCompaniesPage = lazyPage(() =>
  import("@/pages/for-companies").then((m) => ({
    default: m.ForCompaniesPage,
  })),
);
const ForCompaniesSignupPage = lazyPage(() =>
  import("@/pages/for-companies/signup").then((m) => ({
    default: m.ForCompaniesSignupPage,
  })),
);
const CompanyDashboardPage = lazyPage(() =>
  import("@/pages/company/dashboard").then((m) => ({
    default: m.CompanyDashboardPage,
  })),
);
const InternshipInboxPage = lazyPage(() =>
  import("@/pages/dashboard/internship-inbox").then((m) => ({
    default: m.InternshipInboxPage,
  })),
);
const StudentMessagesPage = lazyPage(() =>
  import("@/pages/dashboard/messages").then((m) => ({
    default: m.StudentMessagesPage,
  })),
);
const AdminCompaniesPage = lazyPage(() =>
  import("@/pages/admin/companies").then((m) => ({
    default: m.AdminCompaniesPage,
  })),
);
const AdminMessagesPage = lazyPage(() =>
  import("@/pages/admin/messages").then((m) => ({
    default: m.AdminMessagesPage,
  })),
);
const SuperAdminDashboard = lazyPage(() =>
  import("@/pages/superadmin/dashboard").then((m) => ({
    default: m.SuperAdminDashboard,
  })),
);
const SuperAdminStudents = lazyPage(() =>
  import("@/pages/superadmin/students").then((m) => ({
    default: m.SuperAdminStudents,
  })),
);
const SuperAdminInstructors = lazyPage(() =>
  import("@/pages/superadmin/instructors").then((m) => ({
    default: m.SuperAdminInstructors,
  })),
);
const SuperAdminAdmins = lazyPage(() =>
  import("@/pages/superadmin/admins").then((m) => ({
    default: m.SuperAdminAdmins,
  })),
);
const SuperAdminAudit = lazyPage(() =>
  import("@/pages/superadmin/audit").then((m) => ({
    default: m.SuperAdminAudit,
  })),
);
const HallOfFamePage = lazyPage(() =>
  import("@/pages/hall-of-fame").then((m) => ({ default: m.HallOfFamePage })),
);

// Import global styles
import "@/styles/globals.css";

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      // Log query errors with context (queryKey) for debugging
      console.error("Query error:", {
        queryKey: query.queryKey,
        error,
      });
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, variables) => {
      // Log mutation errors with context for debugging
      console.error("Mutation error:", {
        variables,
        error,
      });
    },
  }),
});

function PageViewTracker() {
  usePageViewTracker();
  return null;
}

// Guard for /company/dashboard. Allows the company role + company_manager,
// AND allows admin when the mock "view as company" flag is set in
// sessionStorage. Anything else falls back to the standard ProtectedRoute
// 403 screen.
function CompanyDashboardGuard({ children }: { children: React.ReactNode }) {
  const isImpersonating =
    typeof window !== "undefined" &&
    !!sessionStorage.getItem("mock_view_as_company");
  return (
    <ProtectedRoute requiredRole={isImpersonating ? "admin" : "company"}>
      {children}
    </ProtectedRoute>
  );
}

// Guard for /spoc routes. Allows the spoc role,
// AND allows admin when the mock "view as spoc" flag is set in
// sessionStorage. Anything else falls back to the standard ProtectedRoute
// 403 screen.
function SpocDashboardGuard({ children }: { children: React.ReactNode }) {
  const isImpersonating =
    typeof window !== "undefined" &&
    !!sessionStorage.getItem("mock_view_as_spoc");
  return (
    <ProtectedRoute requiredRole={isImpersonating ? "admin" : "spoc"}>
      {children}
    </ProtectedRoute>
  );
}

/**
 * Scopes the error boundary to the active route, so a page that throws during
 * render shows a recoverable fallback instead of blanking the whole app — and
 * navigating elsewhere clears it.
 */
function RouteErrorBoundary({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return <ErrorBoundary resetKey={location.pathname}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <Router>
          <AuthProvider>
            <StudentLiveProvider><CartProvider>
              <ConfirmProvider>
                <ProfileCompletionGuard>
                  <div className="App">
                    <AstraRouteTheme />
                    <ScrollToTop />
                    <PageViewTracker />
                    <RouteErrorBoundary>
                      <Routes>
                        {/* Auth Routes - No Layout */}
                        <Route
                          path="/campus"
                          element={
                            <MainLayout>
                              <CampusForInstitutionsPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/help"
                          element={
                            <MainLayout>
                              <HelpPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/labs"
                          element={
                            <MainLayout>
                              <LabsPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/labs/:slug"
                          element={
                            <MainLayout>
                              <LabWorkspace />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/instructor/lab-studio"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <LabStudioPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/lab-studio"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <LabStudioPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/auth/linkedin/callback"
                          element={<LinkedInCallbackPage />}
                        />
                        <Route
                          path="/login"
                          element={
                            <AuthLayout>
                              <LoginPage />
                            </AuthLayout>
                          }
                        />
                        <Route
                          path="/register"
                          element={
                            <AuthLayout>
                              <RegisterPage />
                            </AuthLayout>
                          }
                        />
                        <Route
                          path="/verify-email"
                          element={
                            <AuthLayout>
                              <VerifyEmailPage />
                            </AuthLayout>
                          }
                        />
                        <Route
                          path="/forgot-password"
                          element={
                            <AuthLayout>
                              <ForgotPasswordPage />
                            </AuthLayout>
                          }
                        />
                        <Route
                          path="/reset-password"
                          element={
                            <AuthLayout>
                              <ResetPasswordPage />
                            </AuthLayout>
                          }
                        />

                        {/* Public Routes - With Main Layout */}
                        <Route
                          path="/"
                          element={
                            <MainLayout>
                              <HomePage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/hall-of-fame"
                          element={
                            <MainLayout>
                              <HallOfFamePage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/courses"
                          element={
                            <MainLayout>
                              <CoursesPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/courses/:id"
                          element={
                            <MainLayout>
                              <CourseDetailPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/categories"
                          element={
                            <MainLayout>
                              <CategoriesPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/membership"
                          element={
                            <MainLayout>
                              <MembershipPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/bundles"
                          element={
                            <MainLayout>
                              <BundlesPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/bundles/:slug"
                          element={
                            <MainLayout>
                              <BundleDetailPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/search"
                          element={
                            <MainLayout>
                              <SearchPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/about"
                          element={
                            <MainLayout>
                              <AboutPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/contact"
                          element={
                            <MainLayout>
                              <ContactPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/verify-certificate"
                          element={
                            <MainLayout>
                              <VerifyCertificate />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/verify-certificate/:certificateId"
                          element={
                            <MainLayout>
                              <VerifyCertificate />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/blog"
                          element={
                            <MainLayout>
                              <BlogPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/blog/:slug"
                          element={
                            <MainLayout>
                              <BlogDetailPage />
                            </MainLayout>
                          }
                        />

                        {/* Category Pages */}
                        <Route
                          path="/courses/utporul"
                          element={
                            <MainLayout>
                              <UtporulPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/meiporul-ar"
                          element={
                            <MainLayout>
                              <MeiporulARPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/courses/meiporul"
                          element={
                            <MainLayout>
                              <MeiporulPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/courses/seyappaduporul"
                          element={
                            <MainLayout>
                              <SeyappaduporulPage />
                            </MainLayout>
                          }
                        />

                        {/* Policy Pages */}
                        <Route
                          path="/refund-policy"
                          element={
                            <MainLayout>
                              <RefundPolicyPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/terms"
                          element={
                            <MainLayout>
                              <TermsPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/privacy"
                          element={
                            <MainLayout>
                              <PrivacyPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/shipping"
                          element={
                            <MainLayout>
                              <ShippingPage />
                            </MainLayout>
                          }
                        />

                        {/* Public Instructor Profile */}
                        <Route
                          path="/instructor/:id"
                          element={
                            <MainLayout>
                              <InstructorProfilePage />
                            </MainLayout>
                          }
                        />

                        {/* Public, read-only user profile (shareable). Separate from the
                  protected /profile route so it opens for anyone. */}
                        <Route
                          path="/u/:username"
                          element={
                            <MainLayout>
                              <PublicProfilePage />
                            </MainLayout>
                          }
                        />

                        {/* Public Internships */}
                        <Route
                          path="/internships"
                          element={
                            <MainLayout>
                              <InternshipsPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/internships/:slug"
                          element={
                            <MainLayout>
                              <InternshipDetailPage />
                            </MainLayout>
                          }
                        />

                        {/* Protected Student Routes — wrapped in StudentLayout (sidebar + workspace) */}
                        <Route
                          path="/dashboard"
                          element={
                            <ProtectedRoute>
                              <StudentRoute>
                                <StudentLayout>
                                  <DashboardPage />
                                </StudentLayout>
                              </StudentRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/dashboard/analytics"
                          element={
                            <ProtectedRoute>
                              <StudentRoute>
                                <StudentLayout>
                                  <StudentAnalyticsPage />
                                </StudentLayout>
                              </StudentRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/leaderboard"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <LeaderboardPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/games/:id/play"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <GamePlayPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/my-courses"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <MyCoursesPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/wishlist"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <WishlistPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/student/blog/create"
                          element={
                            <ProtectedRoute requiredRole="student">
                              <StudentLayout>
                                <StudentBlogCreate />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/student/blog/create/:id"
                          element={
                            <ProtectedRoute requiredRole="student">
                              <StudentLayout>
                                <StudentBlogCreate />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/student/live-classes"
                          element={
                            <ProtectedRoute requiredRole="student">
                              <StudentLayout>
                                <StudentLiveClassesPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/student/live-classes/:id/join"
                          element={
                            <ProtectedRoute requiredRole="student">
                              <StudentLayout>
                                <StudentLiveClassJoinPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/student/live-classes/:id/recording"
                          element={
                            <ProtectedRoute requiredRole="student">
                              <StudentLayout>
                                <StudentLiveClassRecordingPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        {/* Cart + checkout stay on the public marketing layout — buying flow comes from listing pages. */}
                        <Route
                          path="/cart"
                          element={
                            <MainLayout>
                              <CartPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/checkout"
                          element={
                            <ProtectedRoute>
                              <MainLayout>
                                <CheckoutPage />
                              </MainLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/checkout/:courseId"
                          element={
                            <ProtectedRoute>
                              <MainLayout>
                                <CheckoutPage />
                              </MainLayout>
                            </ProtectedRoute>
                          }
                        />
                        {/* /profile and /settings are shared across roles — use AutoRoleLayout
                  so an instructor sees the instructor sidebar, etc. */}
                        <Route
                          path="/exam-papers"
                          element={
                            <ProtectedRoute>
                              <AutoRoleLayout>
                                <ExamPapers />
                              </AutoRoleLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/exam-pricing"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <ExamPricing />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/profile"
                          element={
                            <ProtectedRoute>
                              <AutoRoleLayout>
                                <ProfilePage />
                              </AutoRoleLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/institutions"
                          element={<ProtectedRoute><InstitutionsPage /></ProtectedRoute>}
                        />
                        <Route
                          path="/institutions/:institutionId/*"
                          element={<ProtectedRoute><InstitutionsPage /></ProtectedRoute>}
                        />
                        <Route
                          path="/settings"
                          element={
                            <ProtectedRoute>
                              <AutoRoleLayout>
                                <SettingsPage />
                              </AutoRoleLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/communication-preferences"
                          element={
                            <ProtectedRoute>
                              <AutoRoleLayout>
                                <CommunicationPreferencesPage />
                              </AutoRoleLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/communications"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AutoRoleLayout>
                                <AdminCommunicationsPage />
                              </AutoRoleLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/dashboard/my-vouchers"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <MyVouchersPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/dashboard/my-internships"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <MyInternshipsPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/dashboard/my-internships/:slug"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <MyInternshipDetailPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/dashboard/internship-profile"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <InternshipProfilePage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/dashboard/internship-inbox"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <InternshipInboxPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/dashboard/messages"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <StudentMessagesPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />

                        {/* SS3 — public company marketing + signup/setup */}
                        <Route
                          path="/for-companies"
                          element={
                            <MainLayout>
                              <ForCompaniesPage />
                            </MainLayout>
                          }
                        />
                        <Route
                          path="/for-companies/signup"
                          element={
                            <MainLayout>
                              <ForCompaniesSignupPage />
                            </MainLayout>
                          }
                        />

                        {/* SS3 — company dashboard (full-width private workspace, no public site chrome).
                  Allow admin too so the "View as company" mockup can render this page. */}
                        <Route
                          path="/company/dashboard"
                          element={
                            <CompanyDashboardGuard>
                              <CompanyDashboardPage />
                            </CompanyDashboardGuard>
                          }
                        />

                        {/* Learning Experience Routes */}
                        <Route
                          path="/courses/:id/learn"
                          element={
                            <ProtectedRoute>
                              <LessonPageRedesigned />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/courses/:courseId/lessons/:lessonId"
                          element={
                            <ProtectedRoute>
                              <LessonPageRedesigned />
                            </ProtectedRoute>
                          }
                        />
                        {/* Dead-path removal (plan Task 3 / spec A1.10): this used to
                  render pages/quiz.tsx (QuizPage), which called endpoints
                  that don't exist on the backend. Repointed to the working
                  quiz-taking page — same component /quiz/:quizId already
                  uses. pages/quiz.tsx, store/quiz.ts and api/quiz.ts were
                  the only files depending on the dead path and are deleted. */}
                        <Route
                          path="/courses/:courseId/quizzes/:quizId"
                          element={
                            <ProtectedRoute>
                              <QuizTaking />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/quiz/:quizId"
                          element={
                            <ProtectedRoute>
                              <QuizTaking />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/courses/:courseId/assignments/:assignmentId"
                          element={
                            <ProtectedRoute>
                              <AssignmentSubmission />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/assignment/:assignmentId"
                          element={
                            <ProtectedRoute>
                              <AssignmentSubmission />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/courses/:courseId/certificate"
                          element={
                            <ProtectedRoute>
                              <CertificatePage />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/certificates/:courseId"
                          element={
                            <ProtectedRoute>
                              <CertificatePage />
                            </ProtectedRoute>
                          }
                        />

                        {/* Instructor Routes */}
                        <Route
                          path="/instructor"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <Navigate to="/instructor/dashboard" replace />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/dashboard"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorDashboard />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorCourses />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/parent"
                          element={
                            <ProtectedRoute>
                              <ParentDashboard />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/my-grades"
                          element={
                            <ProtectedRoute>
                              <MyGradesPage />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/my-plan"
                          element={
                            <ProtectedRoute>
                              <StudentLayout>
                                <LearningPlanPage />
                              </StudentLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/operations"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <OperationsCenter />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/course-packages"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <CoursePackages />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/course-packages"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <CoursePackages />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/recording-lessons"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <RecordingLessons />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/recordings/:classId"
                          element={
                            <ProtectedRoute>
                              <RecordingLessonPage />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/assessment-studio"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <AssessmentStudio />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/interventions"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InterventionsPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/my-mastery"
                          element={
                            <ProtectedRoute>
                              <MyMasteryPage />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/insights"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InsightsPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/past-classes"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <PastClassesPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/past-classes"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <PastClassesPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/create"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <CourseStartPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/:id/edit"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <EditCourse />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/:id/coverage"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <CourseCoveragePage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/live-classes"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorLiveClassesPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/live-classes/new"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorLiveClassNewPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/live-classes/:id/console"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorLiveClassConsolePage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/live-classes/:id/report"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorLiveClassReportPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/students"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorStudents />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/analytics"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorAnalytics />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/:courseId/quiz-builder/:quizId"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <QuizBuilder />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/:courseId/quiz-builder"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <QuizBuilder />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/:courseId/assignment-builder/:assignmentId"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <AssignmentBuilder />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/:courseId/assignment-builder"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <AssignmentBuilder />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/assignments/:assignmentId/grade"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <AssignmentGrading />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/grading"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorGradingPickerPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route path="/library" element={<LibraryPage />} />
                        <Route
                          path="/library/:slug"
                          element={<LibraryDetailPage />}
                        />
                        <Route
                          path="/my-library"
                          element={
                            <ProtectedRoute>
                              <MyLibraryPage />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/:id/gradebook"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorGradebookPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/courses/:id/grading-queue"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorGradingQueuePage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/certificate-designer"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorCertificateDesignerPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/games"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorGamesPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/three-d-tasks"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorThreeDTasksPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/review-queue"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <ReviewQueuePage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/games/new"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <GameBuilderPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/games/:id/edit"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <GameBuilderPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/h5p"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorH5PLibraryPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/ebooks"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorEbooksPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/blog"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <InstructorBlogPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/blog/create"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <BlogEditorPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/instructor/blog/edit/:id"
                          element={
                            <ProtectedRoute requiredRole="instructor">
                              <InstructorLayout>
                                <BlogEditorPage />
                              </InstructorLayout>
                            </ProtectedRoute>
                          }
                        />

                        {/* Admin Routes */}
                        <Route
                          path="/admin"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <Navigate to="/admin/dashboard" replace />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/dashboard"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminDashboard />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminCourses />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/new"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminNewCourse />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/:courseId/activity"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminStudentActivity />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/categories"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminCategories />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/tags"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminTags />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/course-reviews"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminCourseReviews />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/students"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminStudents />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/approvals"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminApprovals />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/manage"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminManage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/:id/edit"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <EditCourse />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/:courseId/quiz-builder/:quizId"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <QuizBuilder />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/:courseId/quiz-builder"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <QuizBuilder />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/:courseId/assignment-builder/:assignmentId"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AssignmentBuilder />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/:courseId/assignment-builder"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AssignmentBuilder />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/courses/create"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <CourseStartPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/instructors"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminInstructors />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/enrollments"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminEnrollments />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/analytics"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminAnalytics />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/internships"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminInternships />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/internship-requests"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminInternshipRequests />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/orders"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminOrders />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/lessons"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminLessons />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/quizzes"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminQuizzes />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/certificates"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminCertificates />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/blogs"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminBlogs />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/hall-of-fame"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminHallOfFame />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/blogs/create"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <BlogEditorPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/blogs/edit/:id"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <BlogEditorPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/blog-templates"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminBlogTemplates />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/settings"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminSettings />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/coupons"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <CouponsPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/memberships"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <MembershipsPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/bundles"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminBundlesPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/content-libraries"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminContentLibrariesPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/company-invoices"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminCompanyInvoicesPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/companies"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminCompaniesPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/messages"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminMessagesPage />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />

                        {/* SS1 — Admin: colleges + cohorts */}
                        <Route
                          path="/admin/colleges"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminColleges />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/cohorts"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminCohorts />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/admin/spocs"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <AdminLayout>
                                <AdminSpocs />
                              </AdminLayout>
                            </ProtectedRoute>
                          }
                        />

                        {/* SS1 — SPOC, all wrapped in SpocLayout */}
                        <Route
                          path="/spoc/dashboard"
                          element={
                            <SpocDashboardGuard>
                              <SpocLayout>
                                <SpocDashboard />
                              </SpocLayout>
                            </SpocDashboardGuard>
                          }
                        />
                        <Route
                          path="/spoc/cohort/:id"
                          element={
                            <SpocDashboardGuard>
                              <SpocLayout>
                                <SpocCohortDetail />
                              </SpocLayout>
                            </SpocDashboardGuard>
                          }
                        />
                        <Route
                          path="/spoc/internship/:id"
                          element={
                            <SpocDashboardGuard>
                              <SpocLayout>
                                <SpocInternshipDetail />
                              </SpocLayout>
                            </SpocDashboardGuard>
                          }
                        />
                        <Route
                          path="/spoc/blog"
                          element={
                            <SpocDashboardGuard>
                              <SpocLayout>
                                <SpocBlogPage />
                              </SpocLayout>
                            </SpocDashboardGuard>
                          }
                        />
                        <Route
                          path="/spoc/blog/create"
                          element={
                            <SpocDashboardGuard>
                              <SpocLayout>
                                <BlogEditorPage />
                              </SpocLayout>
                            </SpocDashboardGuard>
                          }
                        />
                        <Route
                          path="/spoc/blog/edit/:id"
                          element={
                            <SpocDashboardGuard>
                              <SpocLayout>
                                <BlogEditorPage />
                              </SpocLayout>
                            </SpocDashboardGuard>
                          }
                        />
                        <Route
                          path="/spoc/:spocId/profile"
                          element={
                            <SpocDashboardGuard>
                              <SpocLayout>
                                <SpocProfilePage />
                              </SpocLayout>
                            </SpocDashboardGuard>
                          }
                        />

                        {/* SuperAdmin Routes — supervisory role above admin.
                  SuperAdmin can ALSO reach /admin/* (hasRole bypass), but
                  these /superadmin/* routes are superadmin-exclusive. */}
                        <Route
                          path="/superadmin"
                          element={
                            <ProtectedRoute requiredRole="superadmin">
                              <Navigate to="/superadmin/dashboard" replace />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/superadmin/dashboard"
                          element={
                            <ProtectedRoute requiredRole="superadmin">
                              <SuperAdminLayout>
                                <SuperAdminDashboard />
                              </SuperAdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/superadmin/students"
                          element={
                            <ProtectedRoute requiredRole="superadmin">
                              <SuperAdminLayout>
                                <SuperAdminStudents />
                              </SuperAdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/superadmin/instructors"
                          element={
                            <ProtectedRoute requiredRole="superadmin">
                              <SuperAdminLayout>
                                <SuperAdminInstructors />
                              </SuperAdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/superadmin/admins"
                          element={
                            <ProtectedRoute requiredRole="superadmin">
                              <SuperAdminLayout>
                                <SuperAdminAdmins />
                              </SuperAdminLayout>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/superadmin/audit"
                          element={
                            <ProtectedRoute requiredRole="superadmin">
                              <SuperAdminLayout>
                                <SuperAdminAudit />
                              </SuperAdminLayout>
                            </ProtectedRoute>
                          }
                        />

                        {/* 404 Route */}
                        <Route
                          path="*"
                          element={
                            <MainLayout>
                              <NotFoundPage />
                            </MainLayout>
                          }
                        />
                      </Routes>
                    </RouteErrorBoundary>

                    {/* Global Toast Notifications */}
                    <Toaster
                      position="top-right"
                      toastOptions={{
                        duration: 4000,
                        // 2026-09-05 UI system: frosted toasts that match the glass dialogs
                        style: {
                          background: "rgba(255,255,255,0.78)",
                          backdropFilter: "blur(16px)",
                          WebkitBackdropFilter: "blur(16px)",
                          color: "#1f2937",
                          border: "1px solid rgba(255,255,255,0.8)",
                          borderRadius: "0.9rem",
                          boxShadow:
                            "0 12px 32px rgba(249, 115, 22, 0.14), 0 1px 0 rgba(255,255,255,0.9) inset",
                          fontWeight: 500,
                        },
                        success: {
                          iconTheme: { primary: "#f97316", secondary: "#fff" },
                          style: { borderLeft: "4px solid #f97316" },
                        },
                        error: { style: { borderLeft: "4px solid #ef4444" } },
                      }}
                    />
                  </div>
                </ProfileCompletionGuard>
              </ConfirmProvider>
            </CartProvider></StudentLiveProvider>
          </AuthProvider>
        </Router>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;
