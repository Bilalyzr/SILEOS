import type { ReactNode } from "react";
import { BrandBanner } from "./BrandBanner";
import { ShareButton } from "@/components/ui/share-button";

interface PageBannerProps {
  title: string;
  description?: string;
  eyebrow?: string;
  image?: string;
  actions?: ReactNode;
  share?: boolean;
  shareUrl?: string;
  shareTitle?: string;
  shareDescription?: string;
}

/**
 * The illustrated page hero used on discovery and content surfaces.
 * Sharing opens the same artwork language and lets the user add a local cover.
 */
export function PageBanner({
  title,
  description,
  eyebrow,
  image,
  actions,
  share = false,
  shareUrl,
  shareTitle,
  shareDescription,
}: PageBannerProps) {
  return (
    <BrandBanner
      title={title}
      description={description}
      eyebrow={eyebrow}
      image={image}
      headingLevel="h1"
    >
      {actions}
      {share && (
        <ShareButton
          url={shareUrl}
          title={shareTitle || title}
          description={shareDescription || description}
          className="brand-banner-share"
        />
      )}
    </BrandBanner>
  );
}
