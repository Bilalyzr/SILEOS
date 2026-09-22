import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Search, ShoppingCart, Menu, X, ChevronDown, User } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useCart } from "@/contexts/CartContext";
import { roleHomePath } from "@/utils/role-routing";

const learnLinks = [
  ["/courses", "Courses"],
  ["/labs", "Learning labs"],
  ["/library", "Digital library"],
  ["/categories", "Subjects"],
  ["/meiporul-ar", "Meiporul AR"],
  ["/bundles", "Course bundles"],
  ["/membership", "Membership"],
];
const communityLinks = [
  ["/blog", "Blog"],
  ["/about", "About us"],
  ["/contact", "Contact"],
  ["/register?role=instructor", "Become an Instructor"],
];

export default function PublicHeader() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { user, logout } = useAuthStore();
  const { getItemCount } = useCart();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const headerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    setMobileOpen(false);
    headerRef.current
      ?.querySelectorAll("details[open]")
      .forEach((el) => el.removeAttribute("open"));
  }, [pathname]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        headerRef.current
          ?.querySelectorAll("details[open]")
          .forEach((el) => el.removeAttribute("open"));
      }
    };
    const outside = (event: MouseEvent) => {
      if (
        headerRef.current &&
        !headerRef.current.contains(event.target as Node)
      )
        headerRef.current
          .querySelectorAll("details[open]")
          .forEach((el) => el.removeAttribute("open"));
    };
    document.addEventListener("keydown", close);
    document.addEventListener("click", outside);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("click", outside);
    };
  }, []);
  const dashboard =
    user?.role === "parent" ? "/parent" : roleHomePath(user?.role);
  const count = getItemCount();
  const search = (event: React.FormEvent) => {
    event.preventDefault();
    if (query.trim()) {
      navigate(`/courses?search=${encodeURIComponent(query.trim())}`);
      setMobileOpen(false);
    }
  };
  return (
    <header className="rd-public-header" ref={headerRef}>
      <div className="rd-public-bar">
        <Link to="/" className="rd-brand" aria-label="SashaInfinity home">
          <span aria-hidden>∞</span>
          <strong>SashaInfinity</strong>
        </Link>
        <nav className="rd-public-nav" aria-label="Main navigation">
          <NavLink to="/" end>
            Home
          </NavLink>
          <details>
            <summary>
              Learn <ChevronDown size={13} />
            </summary>
            <div>
              {learnLinks.map(([to, label]) => (
                <NavLink key={to} to={to}>
                  {label}
                </NavLink>
              ))}
            </div>
          </details>
          <NavLink to="/campus">For institutions</NavLink>
          <NavLink to="/internships">Internships</NavLink>
          <details>
            <summary>
              Community <ChevronDown size={13} />
            </summary>
            <div>
              {communityLinks.map(([to, label]) => (
                <NavLink key={to} to={to}>
                  {label}
                </NavLink>
              ))}
            </div>
          </details>
        </nav>
        <form onSubmit={search} className="rd-public-search" role="search">
          <Search size={16} />
          <input
            aria-label="Search courses"
            placeholder="Search courses..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button aria-label="Submit course search">Go</button>
        </form>
        <Link
          to="/cart"
          className="rd-cart"
          aria-label={`Cart, ${count} items`}
        >
          <ShoppingCart size={18} />
          {count > 0 && <span>{count}</span>}
        </Link>
        {user ? (
          <details className="rd-account-menu">
            <summary>
              <User size={17} />
              <span>Workspace</span>
              <ChevronDown size={12} />
            </summary>
            <div>
              <Link to={dashboard}>Dashboard</Link>
              <Link to="/profile">Profile</Link>
              <Link to="/settings">Settings</Link>
              <button
                onClick={() => {
                  logout();
                  navigate("/");
                  setMobileOpen(false);
                }}
              >
                Log out
              </button>
            </div>
          </details>
        ) : (
          <div className="rd-public-auth">
            <Link to="/login">Log in</Link>
            <Link to="/register">Get started</Link>
          </div>
        )}
        <button
          className="rd-public-menu-toggle"
          aria-label="Toggle menu"
          aria-expanded={mobileOpen}
          aria-controls="public-mobile-nav"
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
      {mobileOpen && (
        <nav
          className="rd-public-mobile"
          id="public-mobile-nav"
          aria-label="Mobile navigation"
        >
          <form onSubmit={search} className="rd-search">
            <Search size={17} />
            <input
              aria-label="Search courses on mobile"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search courses..."
            />
            <button>Search</button>
          </form>
          <div>
            <section>
              <h2>Learn</h2>
              {learnLinks.map(([to, label]) => (
                <Link key={to} to={to}>
                  {label}
                </Link>
              ))}
            </section>
            <section>
              <h2>Discover</h2>
              <Link to="/">Home</Link>
              <Link to="/internships">Internships</Link>
              <Link to="/campus">For institutions</Link>
              {communityLinks.map(([to, label]) => (
                <Link key={to} to={to}>
                  {label}
                </Link>
              ))}
            </section>
          </div>
        </nav>
      )}
    </header>
  );
}
