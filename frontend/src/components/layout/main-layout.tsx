import * as React from "react";
import PublicHeader from "@/components/public/PublicHeader";
import PublicFooter from "@/components/public/PublicFooter";
import { ImpersonationBanner } from "@/components/admin/ImpersonationBanner";
import { useSymphoAutoReveal } from "@/components/sympho/SymphoSystem";

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const rootRef = React.useRef<HTMLDivElement | null>(null);
  useSymphoAutoReveal(rootRef);

  return (
    <div
      ref={rootRef}
      className="sympho-scope astra-public-layout min-h-screen flex flex-col bg-limestone-100 text-ink-900"
    >
      <div
        aria-hidden="true"
        className="sympho-scroll-progress pointer-events-none fixed top-0 left-0 right-0 z-[70] h-[2.5px] origin-left"
      />
      <ImpersonationBanner />
      <PublicHeader />
      <main id="main" className="rd-public-main flex-1">
        {children}
      </main>
      <PublicFooter />
    </div>
  );
};
