"""
Models package - Import all models to register them with SQLAlchemy
"""
from app.core.database import Base
from app.models.user import User, UserProfile, InstructorProfile, AdminImpersonationLog
from app.models.course import Course, Lesson, CourseCategory, CourseTag, CourseReview
from app.models.enrollment import (
    Enrollment,
    LessonProgress,
    StudentCourseActivity,
    CourseAnnouncement,
    WishlistItem,
    WatchSession,
)
from app.models.quiz import (
    Quiz,
    QuizQuestion,
    QuizQuestionAnswer,
    QuizAttempt,
    QuizAttemptAnswer,
)
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.certificate import (
    Certificate,
    IssuedCertificate,
    CertificateElementTemplate,
)
from app.models.payment import Payment, Order, OrderItem
from app.models.instructor_review import InstructorReview
from app.models.blog import BlogPost, BlogComment
from app.models.coupon import Coupon, CouponUsage
from app.models.page_view import PageView
from app.models.internship import Internship, InternshipVoucher
from app.models.candidate import CandidateProfile, CandidateEligibility
from app.models.cohort import (
    College,
    Cohort,
    ReferralCode,
    CohortMembership,
    Session,
    SessionAttendance,
)
from app.models.company import Company, CompanyInterest
from app.models.company_dashboard import (
    CompanyManager,
    DailyWorkLog,
    InternshipAnnouncement,
    InternshipPerformanceReview,
)
from app.models.internship_request import InternshipRequest
from app.models.notification import Notification
from app.models.hall_of_fame import HallOfFameMember
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.models.membership import (
    Membership,
    MembershipPlan,
    MembershipPlanCourse,
    MembershipStatus,
)
from app.models.bundle import Bundle, BundleCourse
from app.models.company_invoice import (
    CompanyInvoice,
    CompanyInvoiceItem,
    CompanySeatPool,
    CompanySeatAssignment,
    InvoiceCounter,
    InvoiceStatus,
)
from app.models.live_class import (
    LiveClassSchedule,
    LiveClass,
    LiveClassJoinToken,
    LiveClassAttendance,
    LiveClassPoll,
    LiveClassPollVote,
    LiveClassEvent,
    LiveClassStatus,
    RecordingStatus,
    PollStatus,
    AttendanceSource,
)
from app.models.h5p import H5PContent, H5PResult
from app.models.gamification import XpEvent, UserGameStats, Badge, UserBadge
from app.models.game import Game, GameResult
from app.models.ebook import Ebook, EbookGrant  # noqa

__all__ = [
    "Base",
    "User",
    "UserProfile",
    "InstructorProfile",
    "AdminImpersonationLog",
    "Course",
    "Lesson",
    "CourseCategory",
    "CourseTag",
    "CourseReview",
    "Enrollment",
    "LessonProgress",
    "StudentCourseActivity",
    "WatchSession",
    "CourseAnnouncement",
    "WishlistItem",
    "Quiz",
    "QuizQuestion",
    "QuizQuestionAnswer",
    "QuizAttempt",
    "QuizAttemptAnswer",
    "Assignment",
    "AssignmentSubmission",
    "Certificate",
    "IssuedCertificate",
    "CertificateElementTemplate",
    "Payment",
    "Order",
    "OrderItem",
    "InstructorReview",
    "BlogPost",
    "BlogComment",
    "Coupon",
    "CouponUsage",
    "PageView",
    "Internship",
    "InternshipVoucher",
    "CandidateProfile",
    "CandidateEligibility",
    "College",
    "Cohort",
    "ReferralCode",
    "CohortMembership",
    "Session",
    "SessionAttendance",
    "Company",
    "CompanyInterest",
    "CompanyManager",
    "DailyWorkLog",
    "InternshipAnnouncement",
    "InternshipPerformanceReview",
    "InternshipRequest",
    "Notification",
    "HallOfFameMember",
    "WebhookEvent",
    "WebhookEventStatus",
    "Membership",
    "MembershipPlan",
    "MembershipPlanCourse",
    "MembershipStatus",
    "Bundle",
    "BundleCourse",
    "CompanyInvoice",
    "CompanyInvoiceItem",
    "CompanySeatPool",
    "CompanySeatAssignment",
    "InvoiceCounter",
    "InvoiceStatus",
    "LiveClassSchedule",
    "LiveClass",
    "LiveClassJoinToken",
    "LiveClassAttendance",
    "LiveClassPoll",
    "LiveClassPollVote",
    "LiveClassEvent",
    "LiveClassStatus",
    "RecordingStatus",
    "PollStatus",
    "AttendanceSource",
    "H5PContent",
    "H5PResult",
    "XpEvent",
    "UserGameStats",
    "Badge",
    "UserBadge",
    "Game",
    "GameResult",
    "Ebook",
    "EbookGrant",
]

# --- SILEOS feature pack (docs/SILEOS_FEATURES.md) ---
from .geogebra import GeoGebraApplet  # noqa: E402,F401
from .three_d import ThreeDModel  # noqa: E402,F401
from .content_library import VirtualLabCatalog, VirtualLabResult  # noqa: E402,F401
from .three_d_task import ThreeDTask, ThreeDTaskAttempt  # noqa: E402,F401
from .mastery import (
    ConceptLink,
    ConceptPrerequisite,
    CourseOutcome,
    LearnerMastery,
    MasteryEvidence,
)  # noqa: E402,F401
from .tag_cluster import TagCluster  # noqa: E402,F401
from .live_class_report import ClassReport, RecordingAudit  # noqa: E402,F401
from .course_settings import CourseStudioSettings  # noqa: E402,F401
from .ai_layer import ContentErrorReport, TutorEscalation  # noqa: E402,F401
from .flywheel import TeachBack, TeachBackRating  # noqa: E402,F401
from .funnel import FunnelEvent  # noqa: E402,F401
from .course_ops import CourseCollaborator  # noqa: E402,F401
from .learning_signals import (
    AdaptiveSession,
    LearningSignal,
    LessonConceptMarker,
)  # noqa: E402,F401
from .sileos_pack import (  # noqa: E402,F401
    AiJob,
    BankQuestion,
    CoursePrerequisite,
    LearningPath,
    QuestionBank,
    StudentRiskFlag,
    XapiStatement,
)

from .learning_planner import (
    LearningGoal,
    LearningIntervention,
    LearningPlanTask,
)  # noqa: E402,F401

from .assessment_studio import StudioQuestion  # noqa: F401

from .recording_lesson import RecordingLesson  # noqa: F401

from .lab_notebook import LabNotebook  # noqa: F401
from .operations import ServiceHeartbeat, CourseTransfer  # noqa: F401

from .exam_paper import ExamPriceSlab, ExamPaper  # noqa: F401
from .learning_release import LabInvestigationAttempt, OfflineSyncReceipt  # noqa: F401
from .institution import (
    Institution,
    InstitutionMember,
    InstitutionInvite,
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionCourse,
    InstitutionAssignment,
    InstitutionAudit,
    InstitutionPlanRequest,
)  # noqa: F401

from .campus_operations import (
    CampusTerm,
    CampusAttendance,
    CampusAssessment,
    CampusScore,
    CampusResource,
    CampusBranding,
    CampusMailJob,
    ParentLinkRequest,
    CampusSubscription,
)
from .campus_pilot import (  # noqa: F401
    CampusAnnouncement,
    CampusEvent,
    CampusGoal,
    CampusGradePolicy,
    CampusNoticeRead,
    CampusOnboardingState,
    CampusReportComment,
    CampusWhatsAppCampaign,
    CampusWhatsAppContact,
    CampusWhatsAppMessage,
    CampusWhatsAppWebhookEvent,
)
from .whatsapp import (  # noqa: F401
    WhatsAppCampaign,
    WhatsAppContact,
    WhatsAppMessage,
    WhatsAppStatusReceipt,
)
from .campus_growth import CampusLead  # noqa: F401
from .campus_action_center import CampusActionItem  # noqa: F401
from .campus_control_plane import (  # noqa: F401
    CampusConsentReceipt,
    CampusDomain,
    CampusIntegration,
    CampusPrivacyRequest,
    CampusRetentionPolicy,
)
from .admissions import (  # noqa: F401
    AdmissionProgram,
    AdmissionIntake,
    AdmissionApplication,
    AdmissionDocument,
    AdmissionNote,
    AdmissionTask,
    AdmissionStageHistory,
    CampusLearnerProfile,
    CampusLearnerLifecycleHistory,
)
from .tuition import (  # noqa: F401
    TuitionFeePlan,
    TuitionFeeComponent,
    TuitionInstallmentTemplate,
    TuitionFeeAssignment,
    TuitionInstallment,
    TuitionPayment,
    TuitionAdjustment,
    TuitionLedgerEntry,
    TuitionReceipt,
)
from .campus_exams import (  # noqa: F401
    CampusExam,
    CampusExamPaper,
    CampusExamMark,
    CampusHallTicket,
)
from .tuition_reminders import TuitionReminderPolicy, TuitionReminder  # noqa: F401
from .campus_staff import CampusLeaveType, CampusLeaveRequest, CampusSubstitution  # noqa: F401
from .campus_transport import (  # noqa: F401
    CampusTransportRoute,
    CampusTransportStop,
    CampusTransportAssignment,
    CampusTransportLog,
)
from .campus_hostel import (  # noqa: F401
    CampusHostelBlock,
    CampusHostelRoom,
    CampusHostelAllocation,
    CampusHostelPass,
    CampusHostelVisitor,
)
from .tuition_collection import TuitionInvoice, TuitionOnlineOrder  # noqa: F401
