import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useEffect, useState } from "react";
import { DigiLockerButton } from "@/components/flywheel/DigiLockerButton";
import { useParams } from "react-router-dom";
import { Download, Award, ExternalLink, Linkedin, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ShareButton } from "@/components/ui/share-button";
import { LinkedInShareDialog } from "@/components/certificate/LinkedInShareDialog";
import { useAuth } from "@/hooks/use-auth";
import { useSEO } from "@/hooks/use-seo";
import { api } from "@/api/axios";
import {
  buildCertificateCaption,
  SASHA_LINKEDIN_PAGE,
} from "@/utils/certificate-share";

// Sharing is handled by LinkedInShareDialog: it previews the post, pre-fills an
// editable caption, and shares the backend's Open-Graph share page so the
// certificate itself becomes the preview image. See utils/certificate-share.ts
// for why share-offsite alone can't do that.
const SASHA_LINKEDIN = SASHA_LINKEDIN_PAGE;

interface CertificateData {
  id: number;
  course_id: number;
  course_title: string;
  student_name: string;
  instructor_name: string;
  issue_date: string;
  verification_code: string;
  secure_certificate_id: string;
  certificate_hash: string;
}

export const CertificatePage: React.FC = () => {
  const { courseId } = useParams();
  useAuth();
  const [certificate, setCertificate] = useState<CertificateData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showLinkedInShare, setShowLinkedInShare] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);

  useEffect(() => {
    const fetchCertificate = async () => {
      try {
        const res = await api.get(`/certificates/course/${courseId}`);
        setCertificate(res.data);
      } catch (err) {
        console.error("Failed to load certificate:", err);
      } finally {
        setIsLoading(false);
      }
    };
    if (courseId) fetchCertificate();
  }, [courseId]);

  // SEO / Open Graph meta tags for certificates. The preview image is the
  // rendered certificate itself — not the site logo — so any crawler that
  // reaches this page shows the credential.
  useSEO(
    certificate
      ? {
          title: `Certificate: ${certificate.course_title}`,
          description: `Course completion certificate for ${certificate.course_title} issued to ${certificate.student_name}`,
          image:
            certificate.secure_certificate_id && certificate.certificate_hash
              ? // `.png` because this is og:image — crawlers render it server-side
                // and WebP support across them is unreliable.
                `/api/v1/certificates/image/${certificate.secure_certificate_id}/${certificate.certificate_hash}.png`
              : "https://res.cloudinary.com/dkjvfskhn/image/upload/v1759753621/cropped-sasha-logo-small_ejpceq.png",
          url: `${window.location.origin}/certificates/${courseId}`,
          type: "website",
        }
      : {},
  );

  const handleDownload = () => {
    if (!certificate) return;
    const downloadUrl =
      certificate.secure_certificate_id && certificate.certificate_hash
        ? `/api/v1/certificates/download-html-pdf/${certificate.secure_certificate_id}/${certificate.certificate_hash}.pdf`
        : `/api/v1/certificates/download/${certificate.id}`;
    window.open(downloadUrl, "_blank");
  };

  const handleViewOriginal = () => {
    if (!certificate) return;
    const verifyUrl = `/api/v1/certificates/verify-certificate?id=${certificate.secure_certificate_id}&hash=${certificate.certificate_hash}`;
    window.open(verifyUrl, "_blank");
  };

  if (isLoading)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading certificate...</p>
        </div>
      </div>
    );

  if (!certificate)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center p-8">
          <p className="text-gray-600 mb-4">Certificate not found.</p>
          <Button onClick={() => (window.location.href = "/dashboard")}>
            Go to Dashboard
          </Button>
        </div>
      </div>
    );

  // Public verification portal link — resolves to the React verify page which
  // looks the certificate up by hash.
  const verificationUrl = `${window.location.origin}/verify-certificate/${certificate.certificate_hash}`;
  // The Open-Graph share page — its og:image is the rendered certificate, so
  // social previews show the credential rather than the site logo. This is what
  // gets shared, whereas verificationUrl is what humans are pointed at.
  const shareUrl = `${window.location.origin}/api/v1/certificates/share/${certificate.secure_certificate_id}/${certificate.certificate_hash}`;

  // Issue 4: copy the public verification URL (the clean, ID-based public
  // link anyone can open to view/verify this credential) to the clipboard.
  const handleCopyPublicLink = async () => {
    try {
      await navigator.clipboard.writeText(verificationUrl);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    } catch {
      // clipboard may be unavailable (e.g. insecure context) — silently no-op
    }
  };
  // Preview source. The cached PNG is the same render the download and the
  // social card use, and it is served from disk in ~0.1s. Embedding the verify
  // page instead used to boot a second copy of the whole React app inside the
  // iframe, which then fetched and JS-unpacked the ~1.1MB interactive bundle —
  // seconds of blank frame for an image we had already rendered.
  // `.webp` is ~100KB against the PNG's 1.36MB for the same 1800x1158 render,
  // and the extension is what gets it into Cloudflare's cache at all — the
  // extensionless route came back cf-cache-status: DYNAMIC on every request.
  const previewImageUrl = `/api/v1/certificates/image/${certificate.secure_certificate_id}/${certificate.certificate_hash}.webp`;

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
              Certificate of Completion
            </h1>
            <p className="text-gray-500 text-sm">
              Congratulations on completing your course!
            </p>
          </div>
          <div className="flex flex-wrap gap-2 sm:gap-3">
            <ShareButton
              url={shareUrl}
              title={`Certificate: ${certificate.course_title}`}
              description="Certificate of Completion from SashaInfinity"
              caption={buildCertificateCaption({
                courseTitle: certificate.course_title,
                shareUrl,
              })}
            />
            <Button
              onClick={handleCopyPublicLink}
              variant="outline"
              title="Copy public verification link"
            >
              <Copy className="h-4 w-4 mr-2" />{" "}
              {linkCopied ? "Copied!" : "Copy Link"}
            </Button>
            <Button onClick={handleViewOriginal} variant="outline">
              <ExternalLink className="h-4 w-4 mr-2" /> View Full Certificate
            </Button>
            <Button
              onClick={handleDownload}
              className="bg-[#E8701A] hover:bg-[#c95d15] text-white"
            >
              <Download className="h-4 w-4 mr-2" /> Download PDF
            </Button>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-certificate"
    >
      <div className="max-w-5xl mx-auto mb-6">
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-[#0A66C2] to-[#004182] text-white p-5 sm:p-6 shadow-lg">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex items-start gap-3 flex-1">
              <div className="w-11 h-11 rounded-lg bg-white/15 flex items-center justify-center flex-shrink-0">
                <Linkedin className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold text-base sm:text-lg leading-tight">
                  Share your achievement on LinkedIn
                </h3>
                <p className="text-white/85 text-sm mt-1">
                  Post your certificate and tag{" "}
                  <a
                    href={SASHA_LINKEDIN}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold underline underline-offset-2 hover:text-white"
                  >
                    @SashaInfinity
                  </a>{" "}
                  to celebrate with us. Your certificate becomes the post image,
                  and we'll write the caption for you.
                </p>
              </div>
            </div>
            <div className="flex flex-col lg:flex-row flex-shrink-0 gap-2 [&>button]:w-full lg:[&>button]:w-auto">
              <Button
                onClick={() => setShowLinkedInShare(true)}
                className="bg-white text-[#0A66C2] hover:bg-white/90 font-semibold whitespace-nowrap"
              >
                <Linkedin className="h-4 w-4 mr-2" /> Share on LinkedIn
              </Button>
            </div>
          </div>
        </div>
      </div>
      <div
        className="max-w-6xl mx-auto bg-white rounded-lg shadow-lg overflow-hidden"
        data-glass="content"
      >
        <div className="bg-[#E8701A] text-white px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5" />
            <span className="font-medium">Official Certificate</span>
          </div>
          <a
            href={verificationUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-white hover:text-gray-200 text-sm flex items-center gap-1"
          >
            Open in new tab <ExternalLink className="w-3 h-3" />
          </a>
        </div>
        <img
          src={previewImageUrl}
          alt={`Certificate of completion for ${certificate.course_title}`}
          className="w-full h-auto block"
          loading="eager"
          // A cold certificate has to be rendered by headless Chrome first, so
          // keep the frame from collapsing while that request is in flight.
          style={{
            minHeight: "clamp(220px, 40vh, 420px)",
            background: "#f8fafc",
          }}
        />
      </div>
      <div
        className="max-w-5xl mx-auto mt-6 bg-white rounded-xl p-6 border border-gray-200"
        data-glass="content"
      >
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
            <span className="text-green-600 text-xl">✓</span>
          </div>
          <div className="flex-1">
            <p className="font-medium text-gray-900">
              This certificate is valid and verifiable
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Scan the QR code or visit the verification link to confirm
              authenticity
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">Certificate ID</p>
            <p className="font-mono text-sm text-orange-600">
              {certificate.secure_certificate_id}
            </p>
            <DigiLockerButton issuedId={certificate.id} />
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-2">
            Verification URL (for sharing):
          </p>
          <a
            href={verificationUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:text-blue-800 break-all"
          >
            {verificationUrl}
          </a>
        </div>
      </div>
      <LinkedInShareDialog
        open={showLinkedInShare}
        onClose={() => setShowLinkedInShare(false)}
        secureCertificateId={certificate.secure_certificate_id}
        certificateHash={certificate.certificate_hash}
        courseTitle={certificate.course_title}
      />
    </PageLayout>
  );
};
