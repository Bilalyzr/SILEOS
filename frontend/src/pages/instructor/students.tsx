import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useState, useEffect } from "react";
import {
  Users,
  Search,
  MessageCircle,
  Mail,
  BookOpen,
  Award,
  Star,
  Calendar,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar } from "@/components/ui/avatar";
import { api } from "@/api/axios";

interface Student {
  id: number;
  name: string;
  email: string;
  avatar?: string;
  enrolledCourses: EnrolledCourse[];
  totalCourses: number;
  completedCourses: number;
  joinDate: string;
  lastActive: string;
  averageRating: number;
}

interface EnrolledCourse {
  courseId: number;
  courseTitle: string;
  progress: number;
  status: "active" | "completed" | "cancelled";
  lastAccessed: string;
  timeSpent: number;
}

interface Course {
  id: number;
  title: string;
}

/**
 * The backend stores raw enrollment statuses ("enrolled", "completed",
 * "cancelled" — see backend/app/models/enrollment.py) which did NOT match the
 * filter dropdown's values ("active"/"completed"/"paused"), so the status
 * filter matched nothing. Normalize every status to the vocabulary the UI
 * filters on so the dropdown, badges and colors all line up.
 */
const normalizeStatus = (raw?: string): EnrolledCourse["status"] => {
  switch ((raw || "").toLowerCase()) {
    case "completed":
      return "completed";
    case "cancelled":
    case "canceled":
    case "paused":
      return "cancelled";
    // "enrolled", "active", empty, or anything else → an active enrollment
    default:
      return "active";
  }
};

export function InstructorStudents() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [courseFilter, setCourseFilter] = useState("all");
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStudents();
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    try {
      const res = await api.get("/dashboard/instructor");
      const courseList = (res.data.courses || []).map((c: any) => ({
        id: c.id,
        title: c.title,
      }));
      setCourses(courseList);
    } catch (err) {
      console.error("Error fetching courses:", err);
    }
  };

  const fetchStudents = async () => {
    try {
      setLoading(true);
      // Fetch students from instructor students endpoint
      const res = await api.get("/dashboard/instructor/students");
      // Normalize enrollment statuses up-front so filters/badges are consistent.
      const normalized = (res.data.students || []).map((s: any) => ({
        ...s,
        enrolledCourses: (s.enrolledCourses || []).map((c: any) => ({
          ...c,
          status: normalizeStatus(c.status),
        })),
      }));
      setStudents(normalized);
    } catch (err) {
      console.error("Error fetching students:", err);
      setError("Failed to load students");
      setStudents([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredStudents = students.filter((student) => {
    const matchesSearch =
      student.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.email.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ||
      student.enrolledCourses.some((course) => course.status === statusFilter);

    const matchesCourse =
      courseFilter === "all" ||
      student.enrolledCourses.some(
        (course) => course.courseId === parseInt(courseFilter),
      );

    return matchesSearch && matchesStatus && matchesCourse;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-600";
      case "completed":
        return "bg-blue-600";
      case "cancelled":
        return "bg-yellow-600";
      default:
        return "bg-gray-600";
    }
  };

  const formatTimeSpent = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const sendMessage = (student: Student) => {
    // No in-app instructor↔student messaging backend exists yet, so open the
    // mail client pre-addressed with a subject rather than leaving a dead button.
    const subject = encodeURIComponent("Message from your instructor");
    window.open(`mailto:${student.email}?subject=${subject}`, "_blank");
  };

  const sendEmail = (student: Student) => {
    window.open(`mailto:${student.email}`, "_blank");
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="h-6 bg-gray-200 rounded w-64"></div>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 bg-gray-200 rounded animate-pulse"></div>
        ))}
      </div>
    );
  }

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="dash-h1 mb-1">Students</h1>
          <p className="text-slate-600 text-sm">
            Manage and communicate with your students
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-students"
    >
      {error && (
        <Card className="p-6 mb-8 bg-red-50 border-red-200">
          <p className="text-red-600">{error}</p>
          <Button
            onClick={fetchStudents}
            className="mt-4"
            variant="outline"
            size="sm"
          >
            Retry
          </Button>
        </Card>
      )}
      <Card className="p-6 mb-8">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex flex-col md:flex-row gap-4 flex-1">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search students..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <select
              value={courseFilter}
              onChange={(e) => setCourseFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Courses</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id.toString()}>
                  {course.title}
                </option>
              ))}
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          <div className="text-sm text-gray-600">
            {filteredStudents.length} student
            {filteredStudents.length !== 1 ? "s" : ""}
          </div>
        </div>
      </Card>
      {students.length === 0 ? (
        <Card className="p-12 text-center">
          <Users className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No students yet
          </h3>
          <p className="text-gray-600 mb-6">
            Students will appear here once they enroll in your courses.
          </p>
          <Button
            onClick={() => (window.location.href = "/instructor/courses")}
          >
            Manage Courses
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Students List */}
          <div className="lg:col-span-2">
            <div className="space-y-4">
              {filteredStudents.map((student) => (
                <Card
                  key={student.id}
                  className={`p-6 cursor-pointer transition-all hover:shadow-lg ${
                    selectedStudent?.id === student.id
                      ? "ring-2 ring-blue-500"
                      : ""
                  }`}
                  onClick={() => setSelectedStudent(student)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4">
                      <Avatar className="w-12 h-12">
                        {student.avatar ? (
                          <img
                            src={student.avatar}
                            alt={student.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full bg-gradient-to-br from-orange-400 to-orange-600 text-white flex items-center justify-center text-lg font-bold">
                            {student.name.charAt(0).toUpperCase()}
                          </div>
                        )}
                      </Avatar>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">
                          {student.name}
                        </h3>
                        <p className="text-sm text-gray-600 mb-2">
                          {student.email}
                        </p>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-gray-500">Courses</p>
                            <p className="font-medium">
                              {student.enrolledCourses.length}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500">Completed</p>
                            <p className="font-medium text-green-600">
                              {
                                student.enrolledCourses.filter(
                                  (c) => c.status === "completed",
                                ).length
                              }
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500">Joined</p>
                            <p className="font-medium">
                              {new Date(student.joinDate).toLocaleDateString()}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500">Last Active</p>
                            <p className="font-medium">
                              {new Date(
                                student.lastActive,
                              ).toLocaleDateString()}
                            </p>
                          </div>
                        </div>

                        {/* Current Courses */}
                        {student.enrolledCourses.length > 0 && (
                          <div className="mt-4">
                            <p className="text-sm font-medium text-gray-700 mb-2">
                              Enrolled Courses:
                            </p>
                            <div className="space-y-2">
                              {student.enrolledCourses
                                .slice(0, 3)
                                .map((course) => (
                                  <div
                                    key={course.courseId}
                                    className="flex items-center justify-between bg-gray-50 rounded p-2"
                                  >
                                    <div className="flex-1">
                                      <p className="text-sm font-medium text-gray-900">
                                        {course.courseTitle}
                                      </p>
                                      <div className="flex items-center space-x-3 mt-1">
                                        <div className="w-20 bg-gray-200 rounded-full h-2">
                                          <div
                                            className="bg-blue-600 h-2 rounded-full"
                                            style={{
                                              width: `${course.progress}%`,
                                            }}
                                          />
                                        </div>
                                        <span className="text-xs text-gray-600">
                                          {course.progress}%
                                        </span>
                                        <Badge
                                          className={getStatusColor(
                                            course.status,
                                          )}
                                          size="sm"
                                        >
                                          {course.status}
                                        </Badge>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          sendMessage(student);
                        }}
                      >
                        <MessageCircle className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          sendEmail(student);
                        }}
                      >
                        <Mail className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Student Details Sidebar */}
          <div>
            {selectedStudent ? (
              <Card className="p-6 sticky top-8">
                <div className="text-center mb-6">
                  <Avatar className="w-20 h-20 mx-auto mb-4">
                    {selectedStudent.avatar ? (
                      <img
                        src={selectedStudent.avatar}
                        alt={selectedStudent.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-orange-400 to-orange-600 text-white flex items-center justify-center text-2xl font-bold">
                        {selectedStudent.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                  </Avatar>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {selectedStudent.name}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {selectedStudent.email}
                  </p>
                </div>

                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-3">
                      Student Stats
                    </h4>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <BookOpen className="h-4 w-4 text-blue-600 mr-2" />
                          <span className="text-sm text-gray-600">
                            Total Courses
                          </span>
                        </div>
                        <span className="font-medium">
                          {selectedStudent.enrolledCourses.length}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <Award className="h-4 w-4 text-green-600 mr-2" />
                          <span className="text-sm text-gray-600">
                            Completed
                          </span>
                        </div>
                        <span className="font-medium text-green-600">
                          {
                            selectedStudent.enrolledCourses.filter(
                              (c) => c.status === "completed",
                            ).length
                          }
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <Star className="h-4 w-4 text-yellow-600 mr-2" />
                          <span className="text-sm text-gray-600">
                            Avg Rating
                          </span>
                        </div>
                        <span className="font-medium">
                          {selectedStudent.averageRating}/5
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <Calendar className="h-4 w-4 text-purple-600 mr-2" />
                          <span className="text-sm text-gray-600">
                            Member Since
                          </span>
                        </div>
                        <span className="font-medium">
                          {new Date(
                            selectedStudent.joinDate,
                          ).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {selectedStudent.enrolledCourses.length > 0 && (
                    <div className="pt-4 border-t">
                      <h4 className="text-sm font-medium text-gray-700 mb-3">
                        Course Progress
                      </h4>
                      <div className="space-y-3">
                        {selectedStudent.enrolledCourses.map((course) => (
                          <div key={course.courseId}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="text-gray-900 font-medium line-clamp-1">
                                {course.courseTitle}
                              </span>
                              <span className="text-gray-600">
                                {course.progress}%
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full"
                                style={{ width: `${course.progress}%` }}
                              />
                            </div>
                            <div className="flex justify-between text-xs text-gray-500">
                              <span>
                                Time: {formatTimeSpent(course.timeSpent)}
                              </span>
                              <Badge
                                className={getStatusColor(course.status)}
                                size="sm"
                              >
                                {course.status}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-4 border-t space-y-3">
                    <Button
                      className="w-full"
                      onClick={() => sendMessage(selectedStudent)}
                    >
                      <MessageCircle className="h-4 w-4 mr-2" />
                      Send Message
                    </Button>
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => sendEmail(selectedStudent)}
                    >
                      <Mail className="h-4 w-4 mr-2" />
                      Send Email
                    </Button>
                  </div>
                </div>
              </Card>
            ) : (
              <Card className="p-6 text-center">
                <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Select a Student
                </h3>
                <p className="text-gray-600">
                  Click on a student from the list to view their details and
                  progress
                </p>
              </Card>
            )}
          </div>
        </div>
      )}
    </PageLayout>
  );
}
