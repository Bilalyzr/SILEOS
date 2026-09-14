import * as React from "react";
import { useLocation } from "react-router-dom";
import PublicHeader from "@/components/public/PublicHeader";
import PublicFooter from "@/components/public/PublicFooter";
import { ImpersonationBanner } from "@/components/admin/ImpersonationBanner";
interface MainLayoutProps {
  children: React.ReactNode;
}
export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const location = useLocation();
  const isHome = location.pathname === "/";
  return (
    <div className="astra-public-layout min-h-screen flex flex-col">
      {/* Global admin "View as Instructor" banner. Renders null when no
          impersonation session is active, so it's a zero-cost no-op on
          normal pageviews. */}
      <ImpersonationBanner />
      <PublicHeader />
      <main
        className={`rd-public-main flex-1 si-page-enter ${isHome ? "" : "pt-2 lg:pt-3"}`}
      >
        {children}
      </main>
      <PublicFooter />
    </div>
  );
};
