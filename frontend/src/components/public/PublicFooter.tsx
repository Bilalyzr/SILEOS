import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Instagram, Linkedin } from "lucide-react";
import { api } from "@/api/axios";
import styles from "./PublicFooter.module.css";

interface Course {
  id: number;
  title: string;
  category: string;
}

const PublicFooter = () => {
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await api.get("/courses/", {
          params: {
            page: 1,
            page_size: 4,
          },
        });
        setCourses(response.data.courses || []);
      } catch (error) {
        console.error("Error fetching courses for footer:", error);
        // Keep empty array on error
      }
    };

    fetchCourses();
  }, []);

  return (
    <footer className={`astra-footer ${styles.footerSection}`}>
      <div className="container">
        <div className={styles.footerGrid}>
          {/* Company Info */}
          <div className={styles.footerColumn}>
            <Link to="/">
              <img
                src="/assets/images/sasha-logo-small.png"
                alt="SashaInfinity Logo"
                className={styles.footerLogo}
              />
            </Link>
            <p className={styles.address}>
              Ward 1, Uthayapuri Colony, Narasothipatti, Salem, Tamil Nadu
              636004
            </p>
            <p className={styles.phone}>+91 8438740893</p>
            <div className={styles.socialLinks}>
              <a
                href="https://www.instagram.com/sashainfinityedu?igsh=cmVycTFseHRjYmw2"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Instagram"
              >
                <Instagram size={24} />
              </a>
              <a
                href="https://www.linkedin.com/company/sashainfinity/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LinkedIn"
              >
                <Linkedin size={24} />
              </a>
            </div>
          </div>

          {/* Resources */}
          <div className={styles.footerColumn}>
            <h3 className={styles.columnTitle}>Resources</h3>
            <ul className={styles.footerLinks}>
              <li>
                <Link to="/about">About Us</Link>
              </li>
              <li>
                <Link to="/hall-of-fame">Wall of Fame</Link>
              </li>
              <li>
                <Link to="/contact">Contact</Link>
              </li>
              <li>
                <Link to="/refund-policy">Refund and Returns</Link>
              </li>
              <li>
                <Link to="/terms">Conditions</Link>
              </li>
              <li>
                <Link to="/privacy">Privacy Policy</Link>
              </li>
              <li>
                <Link to="/shipping">Shipping & Delivery</Link>
              </li>
              <li>
                <Link to="/courses">Paid Courses</Link>
              </li>
              <li>
                <Link to="/bundles">Course Bundles</Link>
              </li>
              <li>
                <Link to="/membership">Membership</Link>
              </li>
            </ul>
          </div>

          {/* Courses */}
          <div className={styles.footerColumn}>
            <h3 className={styles.columnTitle}>Courses</h3>
            <ul className={styles.footerLinks}>
              {courses.length > 0 ? (
                courses.map((course) => (
                  <li key={course.id}>
                    <Link
                      to={`/courses/${(course as any).slug || (course as any).post_name || course.id}`}
                    >
                      {course.title}
                    </Link>
                  </li>
                ))
              ) : (
                <li>
                  <Link to="/courses">View All Courses</Link>
                </li>
              )}
            </ul>
          </div>

          {/* Working Hours */}
          <div className={styles.footerColumn}>
            <h3 className={styles.columnTitle}>Working Hours</h3>
            <p className={styles.workingHours}>Mon - Sat</p>
            <p className={styles.workingHours}>9:00 AM - 7:00 PM</p>
          </div>
        </div>

        {/* Copyright Row */}
        <div className={styles.copyrightRow}>
          <p className={styles.copyrightText}>
            Copyright © {new Date().getFullYear()} Sashainfinity. All rights
            reserved.
          </p>
          <div className={styles.copyrightLinks}>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms & Conditions</Link>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default PublicFooter;
