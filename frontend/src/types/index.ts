// User Types - SashaInfinity LMS user structure
export interface User {
  id: number;
  user_login: string;
  user_email: string;
  user_nicename: string;
  display_name: string;
  user_url?: string;
  user_registered: string;
  user_status: number;
  is_active: boolean;
  is_verified: boolean;
  profile_completed?: boolean;
  last_login?: string;
  created_at: string;
  updated_at: string;
  role: string; // student | instructor | admin | superadmin | spoc | company | company_manager
  totp_enabled?: boolean; // two-factor auth enrolled (admins/superadmin required)
  // Convenience aliases
  email?: string; // alias for user_email (optional for compatibility)
  first_name?: string; // from UserProfile
  last_name?: string; // from UserProfile
  avatar?: string; // profile photo URL, flattened from UserProfile.profile_photo by some endpoints
  profile?: UserProfile; // included when user profile is loaded
}

export interface UserProfile {
  profile_completed?: boolean;
  id: number;
  user_id: number;
  first_name: string;
  last_name: string;
  description: string;
  phone: string;
  designation: string;
  address: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  profile_photo: string;
  cover_photo: string;
  facebook: string;
  twitter: string;
  linkedin: string;
  website: string;
  show_email: boolean;
  receive_notifications: boolean;
  created_at: string;
  updated_at: string;
}

export interface InstructorProfile {
  id: number;
  user_id: number;
  instructor_rating: string;
  instructor_bio: string;
  instructor_designation: string;
  profile_completion: number;
  is_approved: boolean;
  is_blocked: boolean;
  earning_commission_type: string;
  earning_commission_amount: string;
  created_at: string;
  updated_at: string;
}

// Course Types - SashaInfinity LMS course structure
export interface Course {
  id: number;
  /** URL slug — prefer when building /courses/:ref links. Falls back to `${id}`. */
  slug?: string;
  post_author: number;
  post_date: string;
  post_content: string;
  post_title: string;
  post_excerpt: string;
  post_status: string;
  post_name: string;
  post_modified: string;
  post_parent: number;
  menu_order: number;
  post_type: string;

  // Course specific fields
  course_price_type: string;
  course_price: number;
  course_sale_price: number;
  course_duration: string;
  course_level: string;
  course_benefits: string;
  course_requirements: string;
  course_target_audience: string;
  course_material_includes: string;
  course_thumbnail: string;
  course_cover_image: string;
  course_intro_video: string;
  course_retakes_allowed: boolean;
  course_auto_start_next_lesson: boolean;
  course_content_drip_type: string;
  certificate_template: string;
  total_enrollments: number;
  average_rating: number;
  total_reviews: number;
  num_offline_workshops?: number;
  num_hours?: number;
  institution?: string;
  created_at: string;
  updated_at: string;

  // Enrollment status (for current user)
  is_enrolled?: boolean;

  // Lesson count coming straight from the backend serializer (`stats.lessons`).
  // Prefer this over `lessons?.length`: the course *list* endpoint returns the
  // count in `stats` but omits the full `lessons` array, so `lessons?.length`
  // is 0 on cards. Detail endpoint populates both.
  lesson_count?: number;
  stats?: {
    lessons?: number;
    quizzes?: number;
    duration?: number;
    students?: number;
  };

  // Relationships
  instructor?: User;
  lessons?: Lesson[];
  quizzes?: Quiz[];
  categories?: CourseCategory[];
  tags?: CourseTag[];
  reviews?: CourseReview[];
}

export interface Lesson {
  id: number;
  post_author: number;
  post_date: string;
  post_content: string;
  post_title: string;
  post_excerpt: string;
  post_status: string;
  post_name: string;
  post_modified: string;
  post_parent: number;
  menu_order: number;
  post_type: string;

  // Lesson specific fields
  lesson_video_source: string;
  lesson_video_url: string;
  lesson_video_duration: string;
  lesson_video_poster: string;
  lesson_attachments: string;
  lesson_preview: boolean;
  created_at: string;
  updated_at: string;

  // Relationships
  course?: Course;
  progress?: LessonProgress[];
}

export interface CourseCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  parent_id?: number;
  term_order: number;
  created_at: string;

  // Relationships
  courses?: Course[];
  parent?: CourseCategory;
}

export interface CourseTag {
  id: number;
  name: string;
  slug: string;
  description: string;
  created_at: string;

  // Relationships
  courses?: Course[];
}

export interface CourseReview {
  id: number;
  course_id: number;
  user_id: number;
  rating: number;
  review_title: string;
  review_content: string;
  review_status: string;
  created_at: string;
  updated_at: string;

  // Relationships
  course?: Course;
  user?: User;
}

// Quiz Types - SashaInfinity LMS quiz structure
export interface Quiz {
  id: number;
  post_author: number;
  post_date: string;
  post_content: string;
  post_title: string;
  post_excerpt: string;
  post_status: string;
  post_name: string;
  post_modified: string;
  post_parent: number;
  menu_order: number;
  post_type: string;

  // Quiz settings
  quiz_time_limit: number;
  quiz_feedback_mode: string;
  quiz_max_questions_for_take: number;
  quiz_max_attempts_allowed: number;
  quiz_passing_grade: number;
  quiz_question_layout_view: string;
  quiz_questions_order: string;
  quiz_hide_quiz_details: boolean;
  quiz_hide_quiz_time_display: boolean;
  quiz_auto_start: boolean;
  created_at: string;
  updated_at: string;

  // Relationships
  course?: Course;
  questions?: QuizQuestion[];
  attempts?: QuizAttempt[];
}

export interface QuizQuestion {
  question_id: number;
  quiz_id: number;
  question_title: string;
  question_description: string;
  answer_explanation: string;
  question_type: string;
  question_mark: number;
  question_settings: Record<string, any>;
  question_order: number;
  created_at: string;
  updated_at: string;

  // Relationships
  quiz?: Quiz;
  answers?: QuizQuestionAnswer[];
}

export interface QuizQuestionAnswer {
  answer_id: number;
  belongs_question_id: number;
  belongs_question_type: string;
  answer_title: string;
  is_correct: boolean;
  image_id: number;
  answer_two_gap_match: string;
  answer_view_format: string;
  answer_settings: Record<string, any>;
  answer_order: number;
  created_at: string;

  // Relationships
  question?: QuizQuestion;
}

export interface QuizAttempt {
  attempt_id: number;
  course_id: number;
  quiz_id: number;
  user_id: number;
  total_questions: number;
  total_answered_questions: number;
  total_marks: number;
  earned_marks: number;
  attempt_info: Record<string, any>;
  attempt_status: string;
  attempt_ip: string;
  attempt_started_at: string;
  attempt_ended_at?: string;
  created_at: string;
  updated_at: string;

  // Relationships
  user?: User;
  quiz?: Quiz;
  course?: Course;
  answers?: QuizAttemptAnswer[];
}

export interface QuizAttemptAnswer {
  attempt_answer_id: number;
  user_id: number;
  quiz_id: number;
  question_id: number;
  quiz_attempt_id: number;
  given_answer: string;
  question_mark: number;
  achieved_mark: number;
  minus_mark: number;
  is_correct: boolean;
  created_at: string;

  // Relationships
  user?: User;
  quiz?: Quiz;
  question?: QuizQuestion;
  attempt?: QuizAttempt;
}

// Enrollment Types
export interface Enrollment {
  id: number;
  course_id: number;
  user_id: number;
  order_id?: number;
  enrollment_date: string;
  enrollment_status: string;
  course_progress_percentage: number;
  completed_lessons: number;
  total_lessons: number;
  completed_quizzes: number;
  total_quizzes: number;
  completion_date?: string;
  completion_mode: string;
  completion_mode_text: string;
  created_at: string;
  updated_at: string;

  // Relationships
  student?: User;
  course?: Course;
  order?: Order;
}

export interface LessonProgress {
  id: number;
  user_id: number;
  course_id: number;
  lesson_id: number;
  enrollment_id: number;
  progress_status: string;
  completion_date?: string;
  video_current_time: number;
  video_total_duration: number;
  video_completion_percentage: number;
  reading_time: number;
  created_at: string;
  updated_at: string;

  // Relationships
  user?: User;
  course?: Course;
  lesson?: Lesson;
  enrollment?: Enrollment;
}

// Payment Types
export interface Order {
  id: number;
  user_id: number;
  order_key: string;
  order_status: string;
  currency: string;
  total_amount: number;
  subtotal_amount: number;
  tax_amount: number;
  shipping_amount: number;
  discount_amount: number;
  payment_method: string;
  payment_method_title: string;
  transaction_id: string;
  billing_first_name: string;
  billing_last_name: string;
  billing_email: string;
  billing_phone: string;
  billing_address_1: string;
  billing_city: string;
  billing_state: string;
  billing_country: string;
  billing_postcode: string;
  customer_note: string;
  date_created: string;
  date_modified: string;
  date_paid?: string;
  date_completed?: string;
  created_at: string;
  updated_at: string;

  // Relationships
  user?: User;
  order_items?: OrderItem[];
  payments?: Payment[];
}

export interface OrderItem {
  id: number;
  order_id: number;
  course_id: number;
  order_item_name: string;
  order_item_type: string;
  quantity: number;
  subtotal: number;
  subtotal_tax: number;
  total: number;
  total_tax: number;
  product_data: Record<string, any>;
  created_at: string;

  // Relationships
  order?: Order;
  course?: Course;
}

export interface Payment {
  id: number;
  order_id: number;
  user_id: number;
  payment_method: string;
  gateway_transaction_id: string;
  gateway_payment_id: string;
  gateway_order_id: string;
  amount: number;
  currency: string;
  payment_status: string;
  gateway_response: Record<string, any>;
  failure_reason: string;
  payment_date: string;
  processed_date?: string;
  created_at: string;
  updated_at: string;

  // Relationships
  order?: Order;
  user?: User;
}

// Certificate Types
export interface Certificate {
  id: number;
  post_author: number;
  post_date: string;
  post_content: string;
  post_title: string;
  post_excerpt: string;
  post_status: string;
  post_name: string;
  post_modified: string;
  post_parent: number;
  menu_order: number;
  post_type: string;

  // Certificate settings
  certificate_orientation: string;
  certificate_size: string;
  certificate_width: number;
  certificate_height: number;
  background_image: string;
  background_color: string;
  title_font_size: number;
  title_font_color: string;
  title_font_family: string;
  body_font_size: number;
  body_font_color: string;
  body_font_family: string;
  elements_config: Record<string, any>;
  show_student_name: boolean;
  show_course_name: boolean;
  show_completion_date: boolean;
  show_certificate_id: boolean;
  show_instructor_signature: boolean;
  show_admin_signature: boolean;
  enable_qr_code: boolean;
  qr_code_size: number;
  qr_code_position: string;
  created_at: string;
  updated_at: string;

  // Relationships
  author?: User;
  issued_certificates?: IssuedCertificate[];
}

export interface IssuedCertificate {
  id: number;
  certificate_id: number;
  course_id: number;
  user_id: number;
  certificate_hash: string;
  certificate_title: string;
  certificate_content: string;
  completion_date: string;
  course_completion_percentage: number;
  quiz_completion_percentage: number;
  assignment_completion_percentage: number;
  certificate_file_path: string;
  certificate_download_url: string;
  is_valid: boolean;
  invalidated_date?: string;
  invalidation_reason: string;
  email_sent: boolean;
  email_sent_date?: string;
  created_at: string;
  updated_at: string;

  // Relationships
  template?: Certificate;
  course?: Course;
  student?: User;
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: Record<string, string[]>;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  last_page: number;
  from: number;
  to: number;
}

// Form Types
export interface LoginForm {
  email: string;
  password: string;
  remember?: boolean;
  /**
   * TOTP code, sent only on the retry after the server answers 401
   * "otp_required" for an account with two-factor auth enabled.
   */
  otp_code?: string;
}

export interface RegisterForm {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  confirm_password: string;
  user_type: 'student' | 'instructor';
  agree_to_terms: boolean;
  // Optional — only used by instructor signup path; ignored for students
  phone?: string;
  bio?: string;
  designation?: string;
}

export interface CourseFilters {
  course_type?: string;
  category?: string;
  level?: string;
  price_type?: string;
  rating?: number;
  search?: string;
  instructor?: string;
  sort?: string;
  page?: number;
  per_page?: number;
}

// Component Props Types
export interface CourseCardProps {
  course: Course;
  showInstructor?: boolean;
  showProgress?: boolean;
  className?: string;
}

export interface QuizComponentProps {
  quiz: Quiz;
  attempt?: QuizAttempt;
  onComplete?: (attempt: QuizAttempt) => void;
  readonly?: boolean;
}

export interface VideoPlayerProps {
  src: string;
  poster?: string;
  onProgress?: (progress: number) => void;
  onComplete?: () => void;
  currentTime?: number;
  autoPlay?: boolean;
}

// State Types for Zustand stores
export interface AuthState {
  user: User | null;
  profile: UserProfile | null;
  instructorProfile: InstructorProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginForm) => Promise<void>;
  register: (data: RegisterForm) => Promise<void>;
  logout: () => void;
  updateProfile: (profile: Partial<UserProfile>) => Promise<void>;
  checkAuth: () => Promise<void>;
}

export interface CourseState {
  courses: Course[];
  currentCourse: Course | null;
  enrolledCourses: Course[];
  isLoading: boolean;
  filters: CourseFilters;
  setFilters: (filters: Partial<CourseFilters>) => void;
  fetchCourses: () => Promise<void>;
  fetchCourse: (id: number) => Promise<void>;
  enrollInCourse: (courseId: number) => Promise<void>;
}

export interface QuizState {
  currentQuiz: Quiz | null;
  currentAttempt: QuizAttempt | null;
  answers: Record<number, string>;
  timeRemaining: number;
  isSubmitting: boolean;
  startQuiz: (quizId: number) => Promise<void>;
  submitAnswer: (questionId: number, answer: string) => void;
  submitQuiz: () => Promise<void>;
  resetQuiz: () => void;
}