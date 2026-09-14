import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Users,
  Clock,
  Code2,
  Smartphone,
  BarChart3,
  Palette,
  Briefcase,
  Camera,
  type LucideIcon,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Category {
  id: number;
  name: string;
  slug: string;
  description: string;
  course_count: number;
  color: string;
  icon: LucideIcon;
}

const categories: Category[] = [
  {
    id: 1,
    name: "Web Development",
    slug: "web-development",
    description:
      "Learn modern web technologies including React, Vue, Angular, and more",
    course_count: 45,
    color: "bg-blue-500",
    icon: Code2,
  },
  {
    id: 2,
    name: "Mobile Development",
    slug: "mobile-development",
    description:
      "Build mobile apps for iOS and Android using React Native, Flutter, and native SDKs",
    course_count: 32,
    color: "bg-green-500",
    icon: Smartphone,
  },
  {
    id: 3,
    name: "Data Science",
    slug: "data-science",
    description:
      "Master data analysis, machine learning, and AI with Python, R, and TensorFlow",
    course_count: 28,
    color: "bg-purple-500",
    icon: BarChart3,
  },
  {
    id: 4,
    name: "Design",
    slug: "design",
    description:
      "UI/UX design, graphic design, and creative tools like Figma, Adobe Creative Suite",
    course_count: 21,
    color: "bg-pink-500",
    icon: Palette,
  },
  {
    id: 5,
    name: "Business",
    slug: "business",
    description:
      "Marketing, entrepreneurship, project management, and business strategy",
    course_count: 38,
    color: "bg-orange-500",
    icon: Briefcase,
  },
  {
    id: 6,
    name: "Photography",
    slug: "photography",
    description:
      "Digital photography, photo editing, and visual storytelling techniques",
    course_count: 19,
    color: "bg-yellow-500",
    icon: Camera,
  },
];

export function CategoriesPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <PageLayout
        header={
          <PageHeader>
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Course Categories
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Explore our comprehensive range of course categories and find the
              perfect learning path for your goals
            </p>
          </PageHeader>
        }
        className="rd-screen rd-screen-categories"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div
            className="bg-white rounded-lg p-6 text-center shadow-sm"
            data-glass="content"
          >
            <BookOpen className="h-8 w-8 text-blue-600 mx-auto mb-2" />
            <h3 className="text-2xl font-bold text-gray-900">183</h3>
            <p className="text-gray-600">Total Courses</p>
          </div>
          <div
            className="bg-white rounded-lg p-6 text-center shadow-sm"
            data-glass="content"
          >
            <Users className="h-8 w-8 text-green-600 mx-auto mb-2" />
            <h3 className="text-2xl font-bold text-gray-900">15,000+</h3>
            <p className="text-gray-600">Active Students</p>
          </div>
          <div
            className="bg-white rounded-lg p-6 text-center shadow-sm"
            data-glass="content"
          >
            <Clock className="h-8 w-8 text-purple-600 mx-auto mb-2" />
            <h3 className="text-2xl font-bold text-gray-900">2,000+</h3>
            <p className="text-gray-600">Hours of Content</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {categories.map((category) => (
            <Link
              key={category.id}
              to={`/courses?category=${category.slug}`}
              className="group"
            >
              <Card className="h-full p-6 hover:shadow-lg transition-shadow duration-200 group-hover:border-blue-500">
                <div className="flex items-start space-x-4">
                  <div className="astra-category-icon rounded-lg p-3">
                    <category.icon size={24} aria-hidden="true" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 mb-2 group-hover:text-blue-600">
                      {category.name}
                    </h3>
                    <p className="text-gray-600 mb-4 text-sm">
                      {category.description}
                    </p>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">
                        {category.course_count} courses
                      </Badge>
                      <span className="text-blue-600 font-medium text-sm group-hover:underline">
                        Explore →
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
        <div className="mt-16 text-center">
          <div className="bg-blue-600 rounded-2xl p-8 text-white">
            <h2 className="text-3xl font-bold mb-4">
              Ready to Start Learning?
            </h2>
            <p className="text-blue-100 mb-6 max-w-2xl mx-auto">
              Join thousands of students already learning with our expert
              instructors and comprehensive courses
            </p>
            <Link
              to="/courses"
              className="inline-block bg-white text-blue-600 font-semibold px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Browse All Courses
            </Link>
          </div>
        </div>
      </PageLayout>
    </div>
  );
}
