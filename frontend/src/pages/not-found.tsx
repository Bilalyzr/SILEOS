import * as React from "react"
import { Link } from "react-router-dom"
import { Home, Search, BookOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export const NotFoundPage = () => {
  const [searchQuery, setSearchQuery] = React.useState("")

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      window.location.href = `/courses?search=${encodeURIComponent(searchQuery.trim())}`
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-secondary-50 flex items-center justify-center px-4">
      <div className="max-w-2xl mx-auto text-center">
        {/* 404 Illustration */}
        <div className="mb-8">
          <div className="text-8xl font-bold text-primary-200 mb-4">404</div>
          <div className="w-32 h-32 mx-auto mb-6 bg-primary-100 rounded-full flex items-center justify-center">
            <BookOpen className="w-16 h-16 text-primary-600" />
          </div>
        </div>

        {/* Content */}
        <h1 className="text-4xl md:text-5xl font-bold text-neutral-900 mb-4">
          Page Not Found
        </h1>
        <p className="text-xl text-neutral-600 mb-8 max-w-lg mx-auto">
          Oops! The page you're looking for doesn't exist. It might have been moved, deleted, or you entered the wrong URL.
        </p>

        {/* Search */}
        <form onSubmit={handleSearch} className="mb-8 max-w-md mx-auto">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-neutral-400 w-5 h-5" />
            <Input
              type="search"
              placeholder="Search for courses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-12 pr-4 h-12"
            />
            <Button
              type="submit"
              className="absolute right-2 top-2 h-8"
              size="sm"
            >
              Search
            </Button>
          </div>
        </form>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
          <Button size="lg" asChild>
            <Link to="/">
              <Home className="w-5 h-5 mr-2" />
              Go Home
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/courses">
              <BookOpen className="w-5 h-5 mr-2" />
              Browse Courses
            </Link>
          </Button>
        </div>

        {/* Helpful Links */}
        <div className="border-t border-neutral-200 pt-8">
          <h3 className="text-lg font-semibold text-neutral-900 mb-4">
            Popular Pages
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <Link
              to="/courses"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              All Courses
            </Link>
            <Link
              to="/categories"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Categories
            </Link>
            <Link
              to="/about"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              About Us
            </Link>
            <Link
              to="/contact"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Contact
            </Link>
            <Link
              to="/help"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Help Center
            </Link>
            <Link
              to="/register"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Sign Up
            </Link>
            <Link
              to="/login"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}