import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="sf-auth">
      <aside className="sf-auth-story">
        <Link to="/">
          Sasha<span>Infinity</span>
        </Link>
        <span className="sf-eyebrow">
          A little curiosity. A world of possibility.
        </span>
        <h1>
          Your next discovery
          <br />
          starts here.
        </h1>
        <p>
          Learn with purpose. Build your skills through courses, hands-on
          experiments and guidance from your instructors.
        </p>
        <img src="/design/sasha-guide.png" alt="Sasha learning guide" />
        <Link
          className="sf-secondary"
          style={{
            position: "static",
            marginTop: 24,
            alignSelf: "start",
            fontSize: 13,
          }}
          to="/labs"
        >
          Explore the learning labs →
        </Link>
      </aside>
      <main className="sf-auth-content">{children}</main>
    </div>
  );
}
