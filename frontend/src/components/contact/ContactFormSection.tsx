import React, { useState } from 'react';
import { MapPin, Phone, Mail } from 'lucide-react';
import styles from './ContactFormSection.module.css';

interface FormData {
  name: string;
  email: string;
  phone: string;
  subject: string;
  message: string;
}

const InfoItem: React.FC<{ icon: React.ReactNode; children: React.ReactNode }> = ({ icon, children }) => (
  <div className={styles.infoItem}>
    <div className={styles.iconWrapper}>{icon}</div>
    <div className={styles.infoContent}>{children}</div>
  </div>
);

/**
 * One form control plus its own error slot. Errors used to be rendered as a
 * single stack under the textarea, so "Name is required" appeared far away from
 * the name box; each message now sits under the field it belongs to.
 */
const Field: React.FC<{
  error?: string
  fullWidth?: boolean
  children: (props: { className: string; 'aria-invalid': boolean; 'aria-describedby'?: string }) => React.ReactNode
  id: string
}> = ({ error, fullWidth, children, id }) => (
  <div className={`${styles.field} ${fullWidth ? styles.fieldFull : ''}`}>
    {children({
      className: error ? styles.inputError : '',
      'aria-invalid': Boolean(error),
      'aria-describedby': error ? `${id}-error` : undefined,
    })}
    {error && <span id={`${id}-error`} className={styles.fieldError}>{error}</span>}
  </div>
);

const ContactFormSection = () => {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    phone: '',
    subject: '',
    message: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prevState => ({ ...prevState, [name]: value }));
    // Clear a field's error as soon as the user edits it, instead of leaving
    // stale red text under a box that has since been filled in.
    setErrors(prev => (prev[name as keyof FormData] ? { ...prev, [name]: undefined } : prev));
  };

  const [submitting, setSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle'|'success'|'error'>('idle');
  const [submitMsg, setSubmitMsg] = useState('');
  const [errors, setErrors] = useState<Partial<FormData>>({});

  const validate = () => {
    const e: Partial<FormData> = {};
    if (!formData.name.trim()) e.name = 'Name is required';
    if (!formData.email.trim()) e.email = 'Email is required';
    else if (!/^[^@]+@[^@]+\.[^@]+$/.test(formData.email)) e.email = 'Invalid email address';
    // Subject is marked with * and carries the `required` attribute, but was
    // never checked here — so it was enforced by the browser only.
    if (!formData.subject.trim()) e.subject = 'Subject is required';
    if (!formData.message.trim() || formData.message.trim().length < 10) e.message = 'Message must be at least 10 characters';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      const res = await fetch('/api/v1/blog/contact/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: formData.name, email: formData.email, message: `Subject: ${formData.subject}\n\n${formData.message}` })
      });
      const data = await res.json();
      if (res.ok) {
        setSubmitStatus('success');
        setSubmitMsg('Message sent! We will get back to you within 24 hours.');
        setFormData({ name: '', email: '', phone: '', subject: '', message: '' });
        setErrors({});
      } else {
        setSubmitStatus('error');
        setSubmitMsg(data.detail || 'Failed to send. Please try again.');
      }
    } catch {
      setSubmitStatus('error');
      setSubmitMsg('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className={styles.contactSection}>
      <div className="container">
        <div className={styles.grid}>
          {/* Left Column: Contact Info */}
          <div className={styles.infoColumn}>
            <h2 className={styles.title}>Keep In Touch With Us</h2>
            <p className={styles.subtitle}>We are here to help</p>

            <div className={styles.infoList}>
              <InfoItem icon={<MapPin />}>
                Ward 1, Uthayapuri Colony,
                <br />
                Narasothipatti,
                <br />
                Salem, Tamil Nadu 636004
              </InfoItem>
              <InfoItem icon={<Phone />}>
                <a href="tel:+918438740893">+91 8438740893</a>
              </InfoItem>
              <InfoItem icon={<Mail />}>
                <a href="mailto:support@sashainfinity.com">support@sashainfinity.com</a>
                <br />
                <a href="mailto:hr@sashainfinity.com">hr@sashainfinity.com</a>
              </InfoItem>
            </div>
          </div>

          {/* Right Column: Form */}
          <div className={styles.formColumn}>
            <div className={styles.formWrapper}>
              <h3 className={styles.formTitle}>Get in Touch</h3>
              <form onSubmit={handleSubmit} noValidate>
                <div className={styles.formGrid}>
                  <Field id="contact-name" error={errors.name}>
                    {p => (
                      <input
                        {...p}
                        type="text"
                        name="name"
                        placeholder="Name*"
                        value={formData.name}
                        onChange={handleChange}
                      />
                    )}
                  </Field>
                  <Field id="contact-email" error={errors.email}>
                    {p => (
                      <input
                        {...p}
                        type="email"
                        name="email"
                        placeholder="Email*"
                        value={formData.email}
                        onChange={handleChange}
                      />
                    )}
                  </Field>
                  <Field id="contact-phone">
                    {p => (
                      <input
                        {...p}
                        type="tel"
                        name="phone"
                        placeholder="Phone"
                        value={formData.phone}
                        onChange={handleChange}
                      />
                    )}
                  </Field>
                  <Field id="contact-subject" error={errors.subject}>
                    {p => (
                      <input
                        {...p}
                        type="text"
                        name="subject"
                        placeholder="Subject*"
                        value={formData.subject}
                        onChange={handleChange}
                      />
                    )}
                  </Field>
                  <Field id="contact-message" error={errors.message} fullWidth>
                    {p => (
                      <textarea
                        {...p}
                        name="message"
                        placeholder="Your Message*"
                        rows={6}
                        value={formData.message}
                        onChange={handleChange}
                      ></textarea>
                    )}
                  </Field>
                </div>
                {submitStatus === 'error' && (
                  <div className={styles.errorMessage} role="alert">
                    {submitMsg}
                  </div>
                )}
                {submitStatus === 'success' && (
                  <div className={styles.successMessage} role="status">
                    {submitMsg}
                  </div>
                )}
                <button type="submit" className={styles.submitButton} disabled={submitting}>
                  {submitting ? 'SENDING…' : 'SEND MESSAGE'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ContactFormSection;
