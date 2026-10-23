import React, { useState } from "react";
import {
  ArrowUpRight,
  Clock,
  ExternalLink,
  Mail,
  MapPin,
  Phone,
  Send,
} from "lucide-react";
import {
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

interface FormData {
  name: string;
  email: string;
  phone: string;
  subject: string;
  message: string;
}

const ADDRESS =
  "Ward 1, Uthayapuri Colony, Narasothipatti, Salem, Tamil Nadu 636004";
const PLACE_QUERY = `Sashainfinity, ${ADDRESS}`;
const mapSrc = `https://www.google.com/maps/embed?origin=mfe&pb=!1m3!2m1!1s${encodeURIComponent(
  PLACE_QUERY,
)}!6i16!3m1!1sen!5m1!1sen`;
const mapLink = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
  PLACE_QUERY,
)}`;

export function ContactPage() {
  const [formData, setFormData] = useState<FormData>({
    name: "",
    email: "",
    phone: "",
    subject: "",
    message: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<
    "idle" | "success" | "error"
  >("idle");
  const [submitMsg, setSubmitMsg] = useState("");
  const [errors, setErrors] = useState<Partial<FormData>>({});

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prevState) => ({ ...prevState, [name]: value }));
    setErrors((prev) =>
      prev[name as keyof FormData] ? { ...prev, [name]: undefined } : prev,
    );
  };

  const validate = () => {
    const e: Partial<FormData> = {};
    if (!formData.name.trim()) e.name = "Name is required";
    if (!formData.email.trim()) e.email = "Email is required";
    else if (!/^[^@]+@[^@]+\.[^@]+$/.test(formData.email))
      e.email = "Invalid email address";
    if (!formData.subject.trim()) e.subject = "Subject is required";
    if (!formData.message.trim() || formData.message.trim().length < 10)
      e.message = "Message must be at least 10 characters";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      const res = await fetch("/api/v1/blog/contact/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          message: `Subject: ${formData.subject}\n\n${formData.message}`,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSubmitStatus("success");
        setSubmitMsg("Message sent! We will get back to you within 24 hours.");
        setFormData({
          name: "",
          email: "",
          phone: "",
          subject: "",
          message: "",
        });
        setErrors({});
      } else {
        setSubmitStatus("error");
        setSubmitMsg(data.detail || "Failed to send. Please try again.");
      }
    } catch {
      setSubmitStatus("error");
      setSubmitMsg("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="sympho-scope rd-screen rd-screen-contact min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—CNT.01"
        category="COMMUNICATIONS & STUDIO DESK"
        code="SALEM HEADQUARTERS"
        title="Keep in touch with our studio."
        subtitle="Have a question about courses, Campus OS institutional licensing, or corporate internship partnerships? Reach our team directly in Salem or send a dispatch below."
        metrics={[
          {
            value: "< 24h",
            unit: "SLA",
            label: "Response Turnaround",
            code: "CNT—01",
          },
          {
            value: "636004",
            unit: "PIN",
            label: "Salem, Tamil Nadu",
            code: "CNT—02",
          },
          {
            value: "DIRECT",
            unit: "desk",
            label: "Academic & HR Support",
            code: "CNT—03",
          },
        ]}
      />

      {/* Contact Information + Dispatch Form */}
      <section className="border-b border-ink-900/10 py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="CNT—01"
            category="DIRECT CHANNELS"
            code="CORRESPONDENCE LEDGER"
            title="Get in Touch"
            subtitle="Our academic advisors, technical support engineers, and institutional partnerships desk are here to help."
          />

          <div className="mt-12 grid grid-cols-1 gap-10 lg:grid-cols-12">
            {/* Left Column: Architectural Contact Cards */}
            <div className="space-y-5 lg:col-span-5">
              <div className="sheet-frame bg-limestone-50 p-7">
                <div className="flex items-center justify-between border-b border-ink-900/10 pb-3">
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                    LOC—01 // PHYSICAL STUDIO
                  </span>
                  <MapPin className="h-4 w-4 text-copper-500" />
                </div>
                <h3 className="mt-4 font-display text-2xl font-light text-ink-900">
                  Salem Headquarters
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-600">
                  Ward 1, Uthayapuri Colony,
                  <br />
                  Narasothipatti,
                  <br />
                  Salem, Tamil Nadu 636004
                </p>
              </div>

              <div className="sheet-frame bg-limestone-50 p-7">
                <div className="flex items-center justify-between border-b border-ink-900/10 pb-3">
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                    TEL—02 // VOICE LINE
                  </span>
                  <Phone className="h-4 w-4 text-copper-500" />
                </div>
                <h3 className="mt-4 font-display text-2xl font-light text-ink-900">
                  Direct Telephone
                </h3>
                <a
                  href="tel:+918438740893"
                  className="mt-2 inline-flex items-center gap-1.5 font-mono text-sm text-ink-800 hover:text-copper-500"
                >
                  +91 8438740893
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </a>
                <div className="mt-3 flex items-center gap-2 font-mono text-[11px] text-ink-500">
                  <Clock className="h-3.5 w-3.5 text-copper-500" />
                  <span>Mon – Sat · 09:00 – 18:30 IST</span>
                </div>
              </div>

              <div className="sheet-frame bg-limestone-50 p-7">
                <div className="flex items-center justify-between border-b border-ink-900/10 pb-3">
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-copper-500">
                    EML—03 // ELECTRONIC MAIL
                  </span>
                  <Mail className="h-4 w-4 text-copper-500" />
                </div>
                <h3 className="mt-4 font-display text-2xl font-light text-ink-900">
                  Departmental Desks
                </h3>
                <div className="mt-3 space-y-2 font-mono text-xs">
                  <div>
                    <span className="block text-[10px] uppercase tracking-[0.14em] text-ink-400">
                      Learner & Technical Support
                    </span>
                    <a
                      href="mailto:support@sashainfinity.com"
                      className="text-ink-800 hover:text-copper-500"
                    >
                      support@sashainfinity.com
                    </a>
                  </div>
                  <div className="pt-2">
                    <span className="block text-[10px] uppercase tracking-[0.14em] text-ink-400">
                      Internships & Careers
                    </span>
                    <a
                      href="mailto:hr@sashainfinity.com"
                      className="text-ink-800 hover:text-copper-500"
                    >
                      hr@sashainfinity.com
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Contact Form */}
            <div className="lg:col-span-7">
              <div className="sheet-frame bg-limestone-50 p-8 sm:p-10">
                <div className="flex items-center justify-between border-b border-ink-900/10 pb-4">
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-copper-500">
                    FORM // DISPATCH TRANSMISSION
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
                    * REQUIRED FIELDS
                  </span>
                </div>

                <h3 className="mt-6 font-display text-3xl font-light text-ink-900">
                  Send a Message
                </h3>

                <form onSubmit={handleSubmit} noValidate className="mt-6">
                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="contact-name-input"
                        className="block font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700"
                      >
                        Full Name *
                      </label>
                      <input
                        id="contact-name-input"
                        type="text"
                        name="name"
                        placeholder="Name*"
                        value={formData.name}
                        onChange={handleChange}
                        aria-invalid={Boolean(errors.name)}
                        aria-describedby={
                          errors.name ? "contact-name-error" : undefined
                        }
                        className={`mt-2 w-full rounded-lg border bg-limestone-100 px-4 py-3 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none ${
                          errors.name
                            ? "border-red-500"
                            : "border-ink-900/15 focus:border-copper-500"
                        }`}
                      />
                      {errors.name && (
                        <span
                          id="contact-name-error"
                          className="mt-1.5 block font-mono text-[11px] text-red-600"
                        >
                          {errors.name}
                        </span>
                      )}
                    </div>

                    <div>
                      <label
                        htmlFor="contact-email-input"
                        className="block font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700"
                      >
                        Email Address *
                      </label>
                      <input
                        id="contact-email-input"
                        type="email"
                        name="email"
                        placeholder="Email*"
                        value={formData.email}
                        onChange={handleChange}
                        aria-invalid={Boolean(errors.email)}
                        aria-describedby={
                          errors.email ? "contact-email-error" : undefined
                        }
                        className={`mt-2 w-full rounded-lg border bg-limestone-100 px-4 py-3 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none ${
                          errors.email
                            ? "border-red-500"
                            : "border-ink-900/15 focus:border-copper-500"
                        }`}
                      />
                      {errors.email && (
                        <span
                          id="contact-email-error"
                          className="mt-1.5 block font-mono text-[11px] text-red-600"
                        >
                          {errors.email}
                        </span>
                      )}
                    </div>

                    <div>
                      <label
                        htmlFor="contact-phone-input"
                        className="block font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700"
                      >
                        Phone Number
                      </label>
                      <input
                        id="contact-phone-input"
                        type="tel"
                        name="phone"
                        placeholder="Phone"
                        value={formData.phone}
                        onChange={handleChange}
                        className="mt-2 w-full rounded-lg border border-ink-900/15 bg-limestone-100 px-4 py-3 text-sm text-ink-900 placeholder:text-ink-400 focus:border-copper-500 focus:outline-none"
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="contact-subject-input"
                        className="block font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700"
                      >
                        Subject *
                      </label>
                      <input
                        id="contact-subject-input"
                        type="text"
                        name="subject"
                        placeholder="Subject*"
                        value={formData.subject}
                        onChange={handleChange}
                        aria-invalid={Boolean(errors.subject)}
                        aria-describedby={
                          errors.subject ? "contact-subject-error" : undefined
                        }
                        className={`mt-2 w-full rounded-lg border bg-limestone-100 px-4 py-3 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none ${
                          errors.subject
                            ? "border-red-500"
                            : "border-ink-900/15 focus:border-copper-500"
                        }`}
                      />
                      {errors.subject && (
                        <span
                          id="contact-subject-error"
                          className="mt-1.5 block font-mono text-[11px] text-red-600"
                        >
                          {errors.subject}
                        </span>
                      )}
                    </div>

                    <div className="sm:col-span-2">
                      <label
                        htmlFor="contact-message-input"
                        className="block font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700"
                      >
                        Your Message *
                      </label>
                      <textarea
                        id="contact-message-input"
                        name="message"
                        placeholder="Your Message*"
                        rows={6}
                        value={formData.message}
                        onChange={handleChange}
                        aria-invalid={Boolean(errors.message)}
                        aria-describedby={
                          errors.message ? "contact-message-error" : undefined
                        }
                        className={`mt-2 w-full rounded-lg border bg-limestone-100 px-4 py-3 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none ${
                          errors.message
                            ? "border-red-500"
                            : "border-ink-900/15 focus:border-copper-500"
                        }`}
                      />
                      {errors.message && (
                        <span
                          id="contact-message-error"
                          className="mt-1.5 block font-mono text-[11px] text-red-600"
                        >
                          {errors.message}
                        </span>
                      )}
                    </div>
                  </div>

                  {submitStatus === "error" && (
                    <div
                      role="alert"
                      className="mt-5 rounded-lg border border-red-500/40 bg-red-500/10 p-3 font-mono text-xs text-red-700"
                    >
                      {submitMsg}
                    </div>
                  )}
                  {submitStatus === "success" && (
                    <div
                      role="status"
                      className="mt-5 rounded-lg border border-sage-500/40 bg-sage-500/10 p-3 font-mono text-xs text-sage-700"
                    >
                      {submitMsg}
                    </div>
                  )}

                  <div className="mt-7">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="inline-flex items-center gap-2.5 rounded-pill bg-ink-900 px-8 py-3.5 font-mono text-xs uppercase tracking-[0.16em] text-limestone-100 transition-colors hover:bg-copper-500 disabled:opacity-50"
                    >
                      <Send className="h-3.5 w-3.5" />
                      {submitting ? "SENDING…" : "SEND MESSAGE"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Geodetic Map Plate */}
      <section className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <SymphoSectionHeader
              index="CNT—02"
              category="CARTOGRAPHIC PLATE"
              code="11.6643° N, 78.1460° E"
              title="Find Us in Salem"
              subtitle={ADDRESS}
            />
            <a
              href={mapLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-pill border border-ink-900/20 bg-limestone-50 px-5 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-ink-900 transition-colors hover:border-copper-500 hover:text-copper-500"
            >
              Open in Google Maps
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          </div>

          <div className="mt-8 sheet-frame overflow-hidden bg-limestone-50 p-2">
            <iframe
              src={mapSrc}
              className="h-[420px] w-full rounded border border-ink-900/10"
              allowFullScreen
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              title={`Sashainfinity — ${ADDRESS}`}
            />
          </div>
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—CNT // 03"
        eyebrow="CAMPUS & ENTERPRISE WALKTHROUGHS"
        title="Looking for an institutional or company demo?"
        description="Explore our dedicated portals for schools, colleges, and hiring partners."
        primaryLabel="Campus OS for Institutions"
        primaryTo="/for-institutions"
        secondaryLabel="For Hiring Companies"
        secondaryTo="/for-companies"
      />
    </div>
  );
}
