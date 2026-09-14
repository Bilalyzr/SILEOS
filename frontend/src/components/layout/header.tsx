import * as React from "react"
import { Link,useNavigate,useLocation } from "react-router-dom"
import {
Search,
ShoppingCart,User,
Menu,
X,
LogOut,
Settings,
BookOpen,GraduationCap
} from "lucide-react"
import { Logo } from "@/components/ui/logo"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar,AvatarImage,AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import * as DropdownMenu from "@radix-ui/react-dropdown-menu"
import { cn } from "@/utils/cn"
import { useAuth } from "@/hooks/use-auth"
import { roleHomePath } from "@/utils/role-routing"
import { useCart } from "@/contexts/CartContext"

const navigation = [
  { name: "Home", href: "/" },
  { name: "Meiporul", href: "/meiporul" },
  { name: "Seyappaduporul", href: "/seyappaduporul" },
  { name: "Utporul", href: "/utporul" },
  { name: "Courses", href: "/courses" },
  { name: "Bundles", href: "/bundles" },
  { name: "Membership", href: "/membership" },
  { name: "Categories", href: "/categories" },
  { name: "Internships", href: "/internships" },
  { name: "About", href: "/about" },
  { name: "Contact", href: "/contact" },
]

export const Header: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false)
  const [searchQuery, setSearchQuery] = React.useState("")
  const navigate = useNavigate()
  const location = useLocation()
  const { user, isAuthenticated, logout, userInitials, fullName, avatarUrl } = useAuth()
  const { getItemCount } = useCart()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-orange-100/80 bg-white/70 backdrop-blur-xl">
      <div className="container-custom">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link
            to="/"
            className="flex items-center space-x-2"
          >
            <Logo size="md" showText={true} />
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  "text-sm font-medium transition-colors hover:text-primary-600",
                  location.pathname === item.href
                    ? "text-primary-600"
                    : "text-neutral-700"
                )}
              >
                {item.name}
              </Link>
            ))}
          </nav>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="hidden lg:flex items-center">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
              <Input
                type="search"
                placeholder="Search courses..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-64 pl-10"
              />
            </div>
          </form>

          {/* Right Section */}
          <div className="flex items-center space-x-4">
            {/* Cart Icon */}
            <Button variant="ghost" size="icon" asChild className="relative">
              <Link to="/cart">
                <ShoppingCart className="w-5 h-5" />
                {getItemCount() > 0 && (
                  <span className="absolute -top-1 -right-1 bg-primary-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium">
                    {getItemCount()}
                  </span>
                )}
              </Link>
            </Button>

            {isAuthenticated ? (
              <>

                {/* User Menu */}
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                      <Avatar size="sm">
                        <AvatarImage src={avatarUrl} />
                        <AvatarFallback>
                          {userInitials}
                        </AvatarFallback>
                      </Avatar>
                    </Button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Portal>
                    <DropdownMenu.Content
                      className="z-popover w-56 bg-white rounded-md shadow-lg border p-2"
                      align="end"
                    >
                      <div className="px-2 py-1.5">
                        <p className="text-sm font-medium">{fullName}</p>
                        <p className="text-xs text-neutral-600">{user?.user_email}</p>
                        <Badge className="mt-1" variant="outline">
                          {user?.role}
                        </Badge>
                      </div>
                      <DropdownMenu.Separator className="my-1 h-px bg-neutral-200" />

                      <DropdownMenu.Item asChild>
                        <Link
                          to={roleHomePath(user?.role)}
                          className="flex items-center px-2 py-1.5 text-sm cursor-pointer hover:bg-neutral-50 rounded-md"
                        >
                          <User className="mr-2 w-4 h-4" />
                          Dashboard
                        </Link>
                      </DropdownMenu.Item>

                      <DropdownMenu.Item asChild>
                        <Link
                          to="/profile"
                          className="flex items-center px-2 py-1.5 text-sm cursor-pointer hover:bg-neutral-50 rounded-md"
                        >
                          <User className="mr-2 w-4 h-4" />
                          My Profile
                        </Link>
                      </DropdownMenu.Item>

                      {user?.role === 'student' && (
                        <DropdownMenu.Item asChild>
                          <Link
                            to="/my-courses"
                            className="flex items-center px-2 py-1.5 text-sm cursor-pointer hover:bg-neutral-50 rounded-md"
                          >
                            <BookOpen className="mr-2 w-4 h-4" />
                            My Courses
                          </Link>
                        </DropdownMenu.Item>
                      )}

                      {user?.role === 'instructor' && (
                        <DropdownMenu.Item asChild>
                          <Link
                            to="/instructor/courses"
                            className="flex items-center px-2 py-1.5 text-sm cursor-pointer hover:bg-neutral-50 rounded-md"
                          >
                            <BookOpen className="mr-2 w-4 h-4" />
                            My Courses
                          </Link>
                        </DropdownMenu.Item>
                      )}

                      <DropdownMenu.Separator className="my-1 h-px bg-neutral-200" />

                      <DropdownMenu.Item asChild>
                        <Link
                          to="/settings"
                          className="flex items-center px-2 py-1.5 text-sm cursor-pointer hover:bg-neutral-50 rounded-md"
                        >
                          <Settings className="mr-2 w-4 h-4" />
                          Settings
                        </Link>
                      </DropdownMenu.Item>

                      <DropdownMenu.Separator className="my-1 h-px bg-neutral-200" />

                      <DropdownMenu.Item
                        className="flex items-center px-2 py-1.5 text-sm cursor-pointer hover:bg-neutral-50 rounded-md text-danger-600"
                        onClick={handleLogout}
                      >
                        <LogOut className="mr-2 w-4 h-4" />
                        Logout
                      </DropdownMenu.Item>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </>
            ) : (
              <>
                <Button variant="ghost" asChild>
                  <Link to="/login">Login</Link>
                </Button>
                <Button variant="outline" asChild className="hidden md:flex">
                  <Link to="/register?role=instructor">
                    <GraduationCap className="w-4 h-4 mr-2" />
                    Become an Instructor
                  </Link>
                </Button>
              </>
            )}

            {/* Mobile menu button */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 border-t">
              {/* Mobile Search */}
              <div className="px-3 py-2">
                <form onSubmit={handleSearch}>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
                    <Input
                      type="search"
                      placeholder="Search courses..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </form>
              </div>

              {/* Mobile Navigation Links */}
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "block px-3 py-2 text-base font-medium rounded-md transition-colors",
                    location.pathname === item.href
                      ? "text-primary-600 bg-primary-50"
                      : "text-neutral-700 hover:text-primary-600 hover:bg-neutral-50"
                  )}
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.name}
                </Link>
              ))}

              {/* Mobile User Menu */}
              {isAuthenticated && (
                <>
                  <div className="px-3 py-2 border-t mt-2">
                    <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                      Account
                    </p>
                  </div>
                  <Link
                    to={roleHomePath(user?.role)}
                    className="flex items-center px-3 py-2 text-base font-medium rounded-md text-neutral-700 hover:text-primary-600 hover:bg-neutral-50"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    <User className="mr-2 w-5 h-5" />
                    Dashboard
                  </Link>
                  <Link
                    to="/profile"
                    className="flex items-center px-3 py-2 text-base font-medium rounded-md text-neutral-700 hover:text-primary-600 hover:bg-neutral-50"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    <User className="mr-2 w-5 h-5" />
                    My Profile
                  </Link>
                  {user?.role === 'student' && (
                    <Link
                      to="/my-courses"
                      className="flex items-center px-3 py-2 text-base font-medium rounded-md text-neutral-700 hover:text-primary-600 hover:bg-neutral-50"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      <BookOpen className="mr-2 w-5 h-5" />
                      My Courses
                    </Link>
                  )}
                  {user?.role === 'instructor' && (
                    <Link
                      to="/instructor/courses"
                      className="flex items-center px-3 py-2 text-base font-medium rounded-md text-neutral-700 hover:text-primary-600 hover:bg-neutral-50"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      <BookOpen className="mr-2 w-5 h-5" />
                      My Courses
                    </Link>
                  )}
                  <Link
                    to="/settings"
                    className="flex items-center px-3 py-2 text-base font-medium rounded-md text-neutral-700 hover:text-primary-600 hover:bg-neutral-50"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    <Settings className="mr-2 w-5 h-5" />
                    Settings
                  </Link>
                  <button
                    onClick={() => {
                      handleLogout()
                      setIsMenuOpen(false)
                    }}
                    className="flex items-center w-full px-3 py-2 text-base font-medium rounded-md text-danger-600 hover:bg-danger-50"
                  >
                    <LogOut className="mr-2 w-5 h-5" />
                    Logout
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
