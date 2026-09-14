import * as React from "react"
import { Link } from "react-router-dom"
import { Facebook,Twitter,Instagram,Linkedin,Youtube,Mail,Phone,MapPin } from "lucide-react"
import toast from "react-hot-toast"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Logo } from "@/components/ui/logo"
import { api } from "@/api/axios"

export const Footer: React.FC = () => {
  const [email, setEmail] = React.useState("")
  const [subscribing, setSubscribing] = React.useState(false)

  // M-12: this form's onSubmit was e.preventDefault() only — never called
  // anything. POST /blog/newsletter/subscribe already existed
  // (blog.py:721) with zero UI callers.
  const isValidEmail = (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value)

  const handleNewsletterSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValidEmail(email)) {
      toast.error("Please enter a valid email address")
      return
    }
    setSubscribing(true)
    try {
      await api.post("/blog/newsletter/subscribe", { email })
      toast.success("Subscribed! Check your inbox for a welcome email.")
      setEmail("")
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to subscribe. Please try again.")
    } finally {
      setSubscribing(false)
    }
  }

  const footerLinks = {
    company: [
      { name: "About Us", href: "/about" },
      { name: "Contact", href: "/contact" },
      { name: "Careers", href: "/careers" },
      { name: "Press", href: "/press" },
      { name: "Blog", href: "/blog" },
    ],
    courses: [
      { name: "All Courses", href: "/courses" },
      { name: "Categories", href: "/categories" },
      { name: "Free Courses", href: "/courses?price_type=free" },
      { name: "Become Instructor", href: "/register?type=instructor" },
      { name: "Course Bundles", href: "/bundles" },
      { name: "Membership", href: "/membership" },
    ],
    support: [
      { name: "Help Center", href: "/help" },
      { name: "Student Support", href: "/support" },
      { name: "System Status", href: "/status" },
      { name: "Course Guidelines", href: "/guidelines" },
      { name: "Community", href: "/community" },
    ],
    legal: [
      { name: "Privacy Policy", href: "/privacy" },
      { name: "Terms of Service", href: "/terms" },
      { name: "Cookie Policy", href: "/cookies" },
      { name: "Refund Policy", href: "/refund" },
      { name: "Accessibility", href: "/accessibility" },
    ],
  }

  const socialLinks = [
    { icon: Facebook, href: "https://facebook.com", label: "Facebook" },
    { icon: Twitter, href: "https://twitter.com", label: "Twitter" },
    { icon: Instagram, href: "https://instagram.com", label: "Instagram" },
    { icon: Linkedin, href: "https://linkedin.com", label: "LinkedIn" },
    { icon: Youtube, href: "https://youtube.com", label: "YouTube" },
  ]

  return (
    <footer className="bg-neutral-900 text-white">
      {/* Newsletter Section */}
      <div className="bg-primary-600">
        <div className="container-custom py-12">
          <div className="max-w-2xl mx-auto text-center">
            <h3 className="text-2xl font-bold mb-4">Stay Updated</h3>
            <p className="text-primary-100 mb-6">
              Get the latest technology courses, industry insights, and exclusive professional development offers delivered to your inbox.
            </p>
            <form onSubmit={handleNewsletterSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="flex-1 bg-white/10 border-white/20 text-white placeholder:text-white/70"
                required
                disabled={subscribing}
              />
              <Button type="submit" variant="secondary" className="sm:px-8" disabled={subscribing}>
                {subscribing ? "Subscribing…" : "Subscribe"}
              </Button>
            </form>
          </div>
        </div>
      </div>

      {/* Main Footer Content */}
      <div className="container-custom py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-8">
          {/* Brand Section */}
          <div className="lg:col-span-2">
            <Link to="/" className="flex items-center space-x-2 mb-6">
              <Logo size="md" showText={true} variant="white" />
            </Link>
            <p className="text-neutral-400 mb-6 max-w-md">
              Master technology and advance your career. Join thousands of professionals worldwide and unlock your potential with our expert-led technology courses.
            </p>

            {/* Contact Info */}
            <div className="space-y-3 text-sm text-neutral-400">
              <div className="flex items-center space-x-3">
                <Mail className="w-4 h-4" />
                <span>support@sashainfinity.com</span>
              </div>
              <div className="flex items-center space-x-3">
                <Phone className="w-4 h-4" />
                <span>+91 8438740893</span>
              </div>
              <div className="flex items-center space-x-3">
                <MapPin className="w-4 h-4" />
                <span>Ward 1, Uthayapuri Colony, Narasothipatti, Salem, Tamil Nadu 636004</span>
              </div>
            </div>
          </div>

          {/* Links Sections */}
          <div>
            <h4 className="font-semibold text-white mb-4">Company</h4>
            <ul className="space-y-3">
              {footerLinks.company.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-neutral-400 hover:text-white transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-white mb-4">Courses</h4>
            <ul className="space-y-3">
              {footerLinks.courses.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-neutral-400 hover:text-white transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-white mb-4">Support</h4>
            <ul className="space-y-3">
              {footerLinks.support.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-neutral-400 hover:text-white transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-white mb-4">Legal</h4>
            <ul className="space-y-3">
              {footerLinks.legal.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-neutral-400 hover:text-white transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Social Links */}
        <div className="mt-12 pt-8 border-t border-neutral-800">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="flex space-x-4">
              {socialLinks.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-10 h-10 bg-neutral-800 rounded-full flex items-center justify-center hover:bg-primary-500 transition-colors"
                  aria-label={social.label}
                >
                  <social.icon className="w-5 h-5" />
                </a>
              ))}
            </div>

            <div className="text-center md:text-right">
              <p className="text-neutral-400 text-sm">
                © 2024 SashaInfinity. All rights reserved.
              </p>
              <p className="text-neutral-500 text-xs mt-1">
                Empowering learners worldwide since 2024
              </p>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}