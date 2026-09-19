import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  CheckCircle,
  XCircle,
  Award,
  Calendar,
  User,
  BookOpen,
  Shield,
  Download,
  ExternalLink,
  Loader,
  Clock,
  TrendingUp,
  Globe,
  Lock,
  Eye,
  Copy,
  QrCode,
} from "lucide-react";
import { api } from "@/api/axios";
import { getBackendUrl } from "@/config/urls";
import { useSEO } from "@/hooks/use-seo";
import { ShareButton } from "@/components/ui/share-button";

interface CertificateData {
  valid: boolean;
  certificate_id: string;
  verification_code: string;
  student_name: string;
  student_email: string;
  course_title: string;
  course_description: string;
  instructor_name: string;
  completion_date: string;
  issue_date: string;
  progress: number;
  course_completion_percentage?: number;
  course_level: string;
  verified_at: string;
  certificate_url: string;
  verification_message: string;
}

const VerifyCertificate: React.FC = () => {
  const { certificateId } = useParams<{ certificateId: string }>();
  const navigate = useNavigate();

  const [searchId, setSearchId] = useState("");
  const [certificate, setCertificate] = useState<CertificateData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    if (certificateId) {
      verifyCertificate(certificateId);
    }
  }, [certificateId]);

  // SEO / Open Graph meta tags for certificate verification
  useSEO(
    certificate
      ? {
          title: `Certificate: ${certificate.course_title} - ${certificate.student_name}`,
          description: `Verified certificate for ${certificate.course_title} issued to ${certificate.student_name}. Verification code: ${certificate.verification_code}`,
          image:
            "/brand/sasha-logo-small.png",
          url: window.location.href,
          type: "website",
        }
      : {
          title: "Certificate Verification - SashaInfinity",
          description:
            "Verify SashaInfinity Technology certificates instantly with our secure verification portal",
          image:
            "/brand/sasha-logo-small.png",
          url: window.location.href,
          type: "website",
        },
  );

  const verifyCertificate = async (certId: string) => {
    setVerifying(true);
    setLoading(true);
    setError("");
    setCertificate(null);

    try {
      const response = await api.get(`/certificates/verify/${certId}`);

      if (response.data) {
        setCertificate(response.data);
      }
    } catch (err: any) {
      console.error("Certificate verification error:", err);
      if (err.response?.status === 404) {
        setError(
          "Certificate not found. This certificate may be invalid or has been revoked.",
        );
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError(
          "An error occurred while verifying the certificate. Please try again.",
        );
      }
    } finally {
      setLoading(false);
      setVerifying(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchId.trim()) {
      navigate(`/verify-certificate/${searchId.trim()}`);
    }
  };

  const copyToClipboard = (text: string, message: string) => {
    navigator.clipboard.writeText(text);
    alert(`${message} copied to clipboard!`);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-neutral-50 py-8 px-4">
      <PageLayout
        header={
          <PageHeader>
            <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-primary-500 to-secondary-900 rounded-3xl mb-6 shadow-lg">
              <Shield className="w-12 h-12 text-white" />
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold bg-gradient-to-r from-primary-600 to-secondary-900 bg-clip-text text-transparent mb-4">
              Certificate Verification Portal
            </h1>
            <p className="text-xl text-neutral-600 max-w-2xl mx-auto leading-relaxed">
              Authenticate and verify SashaInfinity Technology certificates with
              enterprise-grade security
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mt-6">
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <Lock className="w-4 h-4" />
                <span>Secured Verification</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <Globe className="w-4 h-4" />
                <span>Global Recognition</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <Clock className="w-4 h-4" />
                <span>Real-time Validation</span>
              </div>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-verify-certificate"
      >
        <div
          className="bg-white rounded-2xl shadow-xl border border-neutral-100 p-6 sm:p-8 mb-8"
          data-glass="work"
        >
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-neutral-900 mb-2">
              Verify Certificate
            </h2>
            <p className="text-neutral-600">
              Enter the verification code or scan the QR code from the
              certificate
            </p>
          </div>
          <form
            onSubmit={handleSearch}
            className="flex flex-col sm:flex-row gap-4"
          >
            <div className="flex-1 sm:flex-auto">
              <label
                htmlFor="certId"
                className="block text-sm font-semibold text-neutral-700 mb-3"
              >
                Certificate Verification Code
              </label>
              <div className="relative">
                <div className="absolute left-4 top-1/2 transform -translate-y-1/2 z-10">
                  <QrCode className="w-6 h-6 text-primary-500" />
                </div>
                <input
                  id="certId"
                  type="text"
                  value={searchId}
                  onChange={(e) => setSearchId(e.target.value.toUpperCase())}
                  placeholder="Enter verification code (e.g., ABC123XYZ789)"
                  className="input w-full pl-14 pr-4 py-3 sm:py-4 text-base sm:text-lg border-2 border-neutral-200 focus:border-primary-500 rounded-xl transition-all"
                  disabled={loading}
                />
              </div>
              <p className="text-xs text-neutral-500 mt-2">
                <AstraSymbol value="💡" /> Tip: You can find this code in the QR code on your
                certificate
              </p>
            </div>
            <div className="flex items-end w-full sm:w-auto">
              <button
                type="submit"
                disabled={loading || !searchId.trim()}
                className="btn w-full sm:w-auto bg-gradient-to-r from-primary-600 to-secondary-900 hover:from-primary-700 hover:to-secondary-900 text-white px-6 sm:px-8 py-3 sm:py-4 text-base sm:text-lg font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader className="w-6 h-6 mr-3 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <Shield className="w-6 h-6 mr-3" />
                    Verify Certificate
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
        {verifying && (
          <div
            className="bg-white rounded-2xl shadow-xl border border-neutral-100 p-8 sm:p-16 text-center"
            data-glass="content"
          >
            <div className="relative inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-primary-500 to-secondary-900 rounded-full mb-6">
              <Loader className="w-8 h-8 sm:w-10 sm:h-10 text-white animate-spin" />
            </div>
            <h3 className="text-xl sm:text-2xl font-bold text-neutral-900 mb-3">
              Verifying Certificate
            </h3>
            <p className="text-base sm:text-lg text-neutral-600 mb-4">
              Please wait while we authenticate the certificate...
            </p>
            <div className="flex items-center justify-center gap-2 text-sm text-neutral-500">
              <Shield className="w-4 h-4" />
              <span>Secure verification in progress</span>
            </div>
          </div>
        )}
        {error && !loading && (
          <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-6">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 sm:w-16 sm:h-16 bg-red-100 rounded-full flex items-center justify-center">
                  <XCircle className="w-6 h-6 sm:w-8 sm:h-8 text-red-600" />
                </div>
              </div>
              <div className="flex-1 text-center sm:text-left">
                <h3 className="text-xl sm:text-2xl font-bold text-red-900 mb-3">
                  Verification Failed
                </h3>
                <p className="text-red-700 text-base sm:text-lg mb-4 sm:mb-6">
                  {error}
                </p>
                <div className="flex flex-col sm:flex-row gap-3 justify-center sm:justify-start">
                  <button
                    onClick={() => {
                      setError("");
                      setSearchId("");
                    }}
                    className="btn bg-danger-600 hover:bg-danger-700 text-white px-6 py-3 rounded-lg font-semibold"
                  >
                    Try Another Certificate
                  </button>
                  <button
                    onClick={() => navigate("/")}
                    className="btn btn-outline border-danger-600 text-danger-600 hover:bg-danger-50 px-6 py-3 rounded-lg font-semibold"
                  >
                    Go Home
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        {certificate && !loading && (
          <div className="space-y-8">
            {/* Enhanced Verification Status Banner */}
            <div className="bg-gradient-to-r from-primary-500 via-primary-600 to-primary-700 rounded-3xl p-6 sm:p-10 text-white shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-32 -mt-32"></div>
              <div className="relative z-10">
                <div className="flex items-center gap-4 sm:gap-6 mb-6">
                  <div className="w-14 h-14 sm:w-20 sm:h-20 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center flex-shrink-0">
                    <CheckCircle className="w-7 h-7 sm:w-10 sm:h-10 text-white" />
                  </div>
                  <div>
                    <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-2">
                      Certificate Verified!
                    </h2>
                    <p className="text-primary-100 text-base sm:text-lg">
                      This certificate is authentic and has been validated
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6 flex-wrap">
                  <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm">
                      Verified at: {formatDate(certificate.verified_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full">
                    <Shield className="w-4 h-4" />
                    <span className="text-sm">Enterprise Security</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Enhanced Certificate Details Card */}
            <div
              className="bg-white rounded-3xl shadow-2xl overflow-hidden border border-neutral-100"
              data-glass="content"
            >
              {/* Certificate Header */}
              <div className="bg-gradient-to-r from-primary-600 via-secondary-900 to-primary-700 px-6 sm:px-10 py-6 sm:py-8 relative">
                <div className="absolute top-0 right-0 w-32 h-32 sm:w-48 sm:h-48 bg-white/10 rounded-full -mr-16 -mt-16 sm:-mr-24 sm:-mt-24"></div>
                <div className="relative z-10">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 sm:w-16 sm:h-16 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center">
                        <Award className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
                      </div>
                      <div>
                        <h3 className="text-xl sm:text-3xl font-bold text-white mb-2">
                          {certificate.student_name}
                        </h3>
                        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                          <div className="bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full">
                            <p className="text-white text-xs sm:text-sm font-medium text-center">
                              Code: {certificate.verification_code}
                            </p>
                          </div>
                          <button
                            onClick={() =>
                              copyToClipboard(
                                certificate.verification_code,
                                "Verification code",
                              )
                            }
                            className="bg-white/20 backdrop-blur-sm hover:bg-white/30 p-2 rounded-full transition-all"
                            title="Copy verification code"
                          >
                            <Copy className="w-4 h-4 text-white" />
                          </button>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <ShareButton
                        url={
                          typeof window !== "undefined"
                            ? window.location.href
                            : undefined
                        }
                        title="Certificate Verification"
                        description={`Verify certificate: ${certificate?.verification_code}`}
                        variant="ghost"
                        className="bg-white/20 backdrop-blur-sm hover:bg-white/30 p-3 text-white"
                        showLabel={false}
                      />
                      <button
                        onClick={() =>
                          copyToClipboard(
                            window.location.href,
                            "Verification link",
                          )
                        }
                        className="bg-white/20 backdrop-blur-sm hover:bg-white/30 p-3 rounded-full transition-all"
                        title="Copy verification link"
                      >
                        <ExternalLink className="w-5 h-5 text-white" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-6 sm:p-10 space-y-6 sm:space-y-8">
                {/* Course Information Section */}
                <div>
                  <h4 className="text-lg font-bold text-neutral-900 mb-6 flex items-center gap-2">
                    <BookOpen className="w-5 h-5 text-primary-600" />
                    Course Details
                  </h4>
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="bg-neutral-50 rounded-2xl p-6">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center flex-shrink-0">
                          <BookOpen className="w-6 h-6 text-primary-600" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-neutral-600 mb-1">
                            Course Title
                          </p>
                          <p className="font-bold text-neutral-900 text-lg">
                            {certificate.course_title}
                          </p>
                          {certificate.course_description && (
                            <p className="text-sm text-neutral-600 mt-2">
                              {certificate.course_description}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="bg-neutral-50 rounded-2xl p-6">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-neutral-100 rounded-xl flex items-center justify-center flex-shrink-0">
                          <User className="w-6 h-6 text-secondary-900" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-neutral-600 mb-1">
                            Certified Instructor
                          </p>
                          <p className="font-bold text-neutral-900 text-lg">
                            {certificate.instructor_name}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-neutral-50 rounded-2xl p-6">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center flex-shrink-0">
                          <Calendar className="w-6 h-6 text-primary-600" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-neutral-600 mb-1">
                            Completion Date
                          </p>
                          <p className="font-bold text-neutral-900 text-lg">
                            {formatDate(certificate.completion_date)}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-neutral-50 rounded-2xl p-6">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-warning-100 rounded-xl flex items-center justify-center flex-shrink-0">
                          <TrendingUp className="w-6 h-6 text-warning-600" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-neutral-600 mb-1">
                            Performance
                          </p>
                          <p className="font-bold text-neutral-900 text-lg">
                            {certificate.course_completion_percentage ||
                              certificate.progress}
                            % Complete
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Certificate Stats */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 pt-8 border-t border-neutral-200">
                  <div className="text-center bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl p-5 sm:p-6">
                    <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <TrendingUp className="w-8 h-8 text-primary-600" />
                    </div>
                    <p className="text-2xl sm:text-3xl font-bold text-primary-600">
                      {certificate.course_completion_percentage ||
                        certificate.progress}
                      %
                    </p>
                    <p className="text-sm text-neutral-600 font-medium">
                      Course Completion
                    </p>
                  </div>
                  <div className="text-center bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl p-5 sm:p-6">
                    <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <CheckCircle className="w-8 h-8 text-primary-600" />
                    </div>
                    <p className="text-2xl sm:text-3xl font-bold text-primary-600">
                      Valid
                    </p>
                    <p className="text-sm text-neutral-600 font-medium">
                      Certificate Status
                    </p>
                  </div>
                  <div className="text-center bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl p-5 sm:p-6">
                    <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <Award className="w-8 h-8 text-primary-600" />
                    </div>
                    <p className="text-2xl sm:text-3xl font-bold text-primary-600">
                      {certificate.course_level || "Professional"}
                    </p>
                    <p className="text-sm text-neutral-600 font-medium">
                      Course Level
                    </p>
                  </div>
                </div>

                {/* Enhanced Actions */}
                <div className="pt-8 border-t border-neutral-200">
                  <div className="flex flex-col sm:flex-row gap-4">
                    {certificate.certificate_url && (
                      <a
                        href={getBackendUrl(certificate.certificate_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 bg-gradient-to-r from-primary-600 to-secondary-900 hover:from-primary-700 hover:to-secondary-900 text-white px-8 py-4 rounded-xl font-semibold flex items-center justify-center gap-3 transition-all shadow-lg hover:shadow-xl"
                      >
                        <Eye className="w-5 h-5" />
                        View Original Certificate
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    {certificate.certificate_url && (
                      <a
                        href={getBackendUrl(certificate.certificate_url)}
                        download
                        className="flex-1 bg-gradient-to-r from-primary-600 to-secondary-900 hover:from-primary-700 hover:to-secondary-900 text-white px-8 py-4 rounded-xl font-semibold flex items-center justify-center gap-3 transition-all shadow-lg hover:shadow-xl"
                      >
                        <Download className="w-5 h-5" />
                        Download Certificate
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Enhanced Security Notice */}
            <div className="bg-gradient-to-r from-primary-50 via-neutral-50 to-primary-100 border border-primary-200 rounded-3xl p-8">
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-secondary-900 rounded-2xl flex items-center justify-center flex-shrink-0">
                  <Shield className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1">
                  <h4 className="text-2xl font-bold text-neutral-900 mb-4">
                    Security & Authenticity Guaranteed
                  </h4>
                  <div className="space-y-3 text-neutral-600">
                    <p className="leading-relaxed">
                      This certificate has been verified against SashaInfinity
                      Technology's secure blockchain-backed database. Each
                      certificate contains cryptographically secure verification
                      codes and QR codes for instant authentication.
                    </p>
                    <div className="grid sm:grid-cols-3 gap-4 mt-6">
                      <div className="flex items-center gap-2">
                        <Lock className="w-5 h-5 text-primary-600" />
                        <span className="text-sm font-medium">
                          256-bit Encryption
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Globe className="w-5 h-5 text-primary-600" />
                        <span className="text-sm font-medium">
                          Globally Recognized
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="w-5 h-5 text-primary-600" />
                        <span className="text-sm font-medium">
                          Real-time Validation
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-neutral-500 mt-4">
                      Any attempt to forge, modify, or duplicate this
                      certificate will immediately fail verification.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        {!certificate && !error && !loading && (
          <div
            className="bg-white rounded-3xl shadow-xl border border-neutral-100 p-6 sm:p-10"
            data-glass="content"
          >
            <div className="text-center mb-8 sm:mb-10">
              <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-primary-100 to-primary-200 rounded-3xl mb-6">
                <QrCode className="w-8 h-8 sm:w-10 sm:h-10 text-primary-600" />
              </div>
              <h3 className="text-2xl sm:text-3xl font-bold text-neutral-900 mb-4">
                How to Verify a Certificate
              </h3>
              <p className="text-base sm:text-lg text-neutral-600 max-w-2xl mx-auto">
                Follow these simple steps to verify the authenticity of any
                SashaInfinity Technology certificate
              </p>
            </div>
            <div className="grid md:grid-cols-3 gap-6 sm:gap-8">
              <div className="text-center">
                <div className="flex-shrink-0 w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-br from-primary-500 to-secondary-900 rounded-2xl flex items-center justify-center mx-auto mb-4 sm:mb-6 text-white font-bold text-lg sm:text-xl shadow-lg">
                  1
                </div>
                <h4 className="text-lg sm:text-xl font-bold text-neutral-900 mb-3">
                  Scan the QR Code
                </h4>
                <p className="text-neutral-600 leading-relaxed text-sm sm:text-base">
                  Use your smartphone camera to scan the QR code printed on the
                  certificate. This will automatically open this verification
                  page.
                </p>
              </div>
              <div className="text-center">
                <div className="flex-shrink-0 w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-br from-secondary-900 to-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4 sm:mb-6 text-white font-bold text-lg sm:text-xl shadow-lg">
                  2
                </div>
                <h4 className="text-lg sm:text-xl font-bold text-neutral-900 mb-3">
                  Enter Verification Code
                </h4>
                <p className="text-neutral-600 leading-relaxed">
                  Alternatively, manually enter the verification code shown on
                  the certificate in the search field above.
                </p>
              </div>
              <div className="text-center">
                <div className="flex-shrink-0 w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-br from-primary-500 to-secondary-900 rounded-2xl flex items-center justify-center mx-auto mb-4 sm:mb-6 text-white font-bold text-lg sm:text-xl shadow-lg">
                  3
                </div>
                <h4 className="text-lg sm:text-xl font-bold text-neutral-900 mb-3">
                  View Verification Results
                </h4>
                <p className="text-neutral-600 leading-relaxed text-sm sm:text-base">
                  Instantly see complete certificate details, authenticity
                  status, and download the verified certificate.
                </p>
              </div>
            </div>

            {/* Additional Features */}
            <div className="mt-8 sm:mt-12 p-6 sm:p-8 bg-gradient-to-r from-primary-50 via-neutral-50 to-primary-100 rounded-2xl">
              <h4 className="text-lg sm:text-xl font-bold text-neutral-900 mb-4 sm:mb-6 text-center">
                Advanced Security Features
              </h4>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                <div className="text-center">
                  <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center mx-auto mb-3 shadow-md">
                    <Lock className="w-6 h-6 text-primary-600" />
                  </div>
                  <p className="text-sm font-medium text-neutral-900">
                    256-bit Encryption
                  </p>
                </div>
                <div className="text-center">
                  <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center mx-auto mb-3 shadow-md">
                    <Clock className="w-6 h-6 text-secondary-900" />
                  </div>
                  <p className="text-sm font-medium text-neutral-900">
                    Real-time Verification
                  </p>
                </div>
                <div className="text-center">
                  <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center mx-auto mb-3 shadow-md">
                    <Globe className="w-6 h-6 text-primary-600" />
                  </div>
                  <p className="text-sm font-medium text-neutral-900">
                    Global Recognition
                  </p>
                </div>
                <div className="text-center">
                  <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center mx-auto mb-3 shadow-md">
                    <Shield className="w-6 h-6 text-red-600" />
                  </div>
                  <p className="text-sm font-medium text-neutral-900">
                    Fraud Prevention
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </PageLayout>
    </div>
  );
};

export default VerifyCertificate;
