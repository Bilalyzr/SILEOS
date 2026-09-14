"""
Email utilities for sending notifications and verification emails
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


def _smtp_tls_context() -> ssl.SSLContext:
    """
    TLS context for STARTTLS.

    mail.sashainfinity.com presents a self-signed certificate, so verification
    is disabled. This used to be implicit: on Python <= 3.11 a bare
    `starttls()` builds a non-verifying stdlib context, which is why sending
    worked. Python 3.12 changed that default to `ssl.create_default_context()`,
    which verifies — so a routine base-image bump from python:3.11-slim would
    have silently broken every outgoing email with a CERTIFICATE_VERIFY_FAILED
    that the old `except Exception` swallowed.

    Making it explicit pins today's behaviour. The right long-term fix is a
    real certificate on the mail host, after which this should become
    `ssl.create_default_context()`.
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

class EmailService:
    """Email service for sending emails"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM

    def _create_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> MIMEMultipart:
        """Create email message"""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = to_email

        # Add text version if provided
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)

        # Add HTML version
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        return message

    def _send_email_sync(self, message: MIMEMultipart, to_email: str):
        """
        Send email synchronously.

        Every failure here is logged at ERROR with a traceback and the SMTP
        stage that failed. It used to `print()` a single line, which meant a
        bounced or rejected verification email left no usable trace: the caller
        backgrounds this task and ignores the return value, so a False was
        indistinguishable from a success. If mail is not arriving, this log is
        the first place to look.
        """
        subject = message['Subject']

        if not self.smtp_host or not self.smtp_user:
            # Deliberately returns True: in dev with no SMTP configured we do
            # not want registration to look broken. Loud enough to notice if it
            # ever happens in production.
            logger.warning(
                "SMTP not configured (SMTP_HOST/SMTP_USER empty) — email to %s "
                "was NOT sent, only logged. Subject: %s",
                to_email, subject,
            )
            return True

        stage = "connect"
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
                stage = "starttls"
                server.starttls(context=_smtp_tls_context())
                server.ehlo()
                stage = "login"
                server.login(self.smtp_user, self.smtp_password)
                stage = "send"
                refused = server.send_message(message)

            # send_message returns a dict of per-recipient refusals. A non-empty
            # dict means the server accepted the session but rejected the
            # recipient — previously indistinguishable from success.
            if refused:
                logger.error(
                    "SMTP accepted the session but REFUSED recipient(s) for %s: %r "
                    "(subject: %s)", to_email, refused, subject,
                )
                return False

            logger.info("Email sent to %s (subject: %s)", to_email, subject)
            return True

        except Exception as e:
            logger.error(
                "Failed to send email to %s at SMTP stage '%s' via %s:%s — %s: %s "
                "(subject: %s)",
                to_email, stage, self.smtp_host, self.smtp_port,
                type(e).__name__, e, subject,
                exc_info=True,
            )
            return False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email asynchronously"""
        message = self._create_message(to_email, subject, html_content, text_content)

        # Run email sending in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(
                executor, self._send_email_sync, message, to_email
            )

# Email templates
class EmailTemplates:
    """Premium email template utilities with enhanced SashaInfinity branding and orange/navy theme"""

    @staticmethod
    def get_base_template() -> str:
        """Get base template styles and structure with Sasha's logo and orange/navy theme"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="X-UA-Compatible" content="ie=edge">
            <title>{{title}}</title>
            <style>
                /* Reset and Base Styles */
                * { margin: 0; padding: 0; box-sizing: border-box; }

                /* Custom Fonts */
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #374151;
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    font-size: 16px;
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                }

                /* Email Container */
                .email-container {
                    max-width: 680px;
                    margin: 40px auto;
                    background: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow:
                        0 20px 25px -5px rgba(15, 23, 42, 0.1),
                        0 10px 10px -5px rgba(15, 23, 42, 0.04),
                        0 0 0 1px rgba(251, 146, 60, 0.1);
                    border: 1px solid rgba(251, 146, 60, 0.2);
                }

                /* Header Styles with Navy Blue and Orange */
                .header {
                    background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 50%, #fb923c 100%);
                    padding: 40px;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }

                .header::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
                    opacity: 0.3;
                }

                .logo-container {
                    position: relative;
                    z-index: 1;
                    display: inline-block;
                    margin-bottom: 12px;
                }

                .logo {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 28px;
                    font-weight: 800;
                    color: #ffffff;
                    letter-spacing: -1px;
                    position: relative;
                    z-index: 1;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
                }

                .logo-icon {
                    width: 40px;
                    height: 40px;
                    background: linear-gradient(135deg, #fb923c, #f97316);
                    border-radius: 10px;
                    margin-right: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 900;
                    font-size: 18px;
                    color: #1e3a8a;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                }

                .logo-text {
                    background: linear-gradient(135deg, #ffffff 0%, #fbbf24 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .logo-infinity {
                    color: #fb923c;
                    font-weight: 900;
                    position: relative;
                }

                .tagline {
                    color: #e2e8f0;
                    font-size: 14px;
                    font-weight: 500;
                    letter-spacing: 0.5px;
                    position: relative;
                    z-index: 1;
                    text-transform: uppercase;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
                }

                /* Content Styles */
                .content {
                    padding: 48px 40px;
                    background: #ffffff;
                    position: relative;
                }

                .content h2 {
                    color: #1e3a8a;
                    font-size: 32px;
                    margin-bottom: 24px;
                    font-weight: 700;
                    line-height: 1.2;
                }

                .content p {
                    color: #475569;
                    font-size: 16px;
                    margin: 20px 0;
                    line-height: 1.7;
                }

                .content p:last-child { margin-bottom: 0; }

                /* Enhanced Button Styles with Orange/Navy Theme */
                .button {
                    display: inline-block;
                    background: linear-gradient(135deg, #fb923c 0%, #f97316 100%);
                    color: #ffffff;
                    padding: 16px 40px;
                    text-decoration: none;
                    border-radius: 12px;
                    margin: 32px 0 24px 0;
                    font-weight: 600;
                    font-size: 16px;
                    transition: all 0.3s ease;
                    border: 1px solid #fb923c;
                    box-shadow:
                        0 10px 15px -3px rgba(251, 146, 60, 0.2),
                        0 4px 6px -2px rgba(251, 146, 60, 0.1);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    position: relative;
                    overflow: hidden;
                }

                .button::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
                    transition: left 0.5s ease;
                }

                .button:hover::before {
                    left: 100%;
                }

                .button:hover {
                    transform: translateY(-2px);
                    box-shadow:
                        0 20px 25px -5px rgba(251, 146, 60, 0.3),
                        0 10px 10px -5px rgba(251, 146, 60, 0.2);
                }

                .button-blue {
                    background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
                    border-color: #1e40af;
                    box-shadow:
                        0 10px 15px -3px rgba(30, 64, 175, 0.2),
                        0 4px 6px -2px rgba(30, 64, 175, 0.1);
                }

                .button-green {
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    border-color: #10b981;
                    box-shadow:
                        0 10px 15px -3px rgba(16, 185, 129, 0.2),
                        0 4px 6px -2px rgba(16, 185, 129, 0.1);
                }

                .button-red {
                    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                    border-color: #ef4444;
                    box-shadow:
                        0 10px 15px -3px rgba(239, 68, 68, 0.2),
                        0 4px 6px -2px rgba(239, 68, 68, 0.1);
                }

                /* Enhanced Link Box */
                .link-box {
                    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                    padding: 20px;
                    border-radius: 12px;
                    border: 1px solid #e2e8f0;
                    margin: 24px 0;
                    word-break: break-all;
                    position: relative;
                }

                .link-box::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg, #fb923c, #f97316);
                    border-radius: 3px 3px 0 0;
                }

                .link-box-label {
                    font-size: 11px;
                    color: #64748b;
                    margin-bottom: 8px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }

                .link-box a {
                    color: #fb923c;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 500;
                    word-break: break-all;
                    transition: color 0.2s ease;
                }

                .link-box a:hover { color: #f97316; }

                /* Enhanced Info Box */
                .info-box {
                    background: linear-gradient(135deg, {{info_bg}} 0%, {{info_bg_light}} 100%);
                    border-left: 4px solid {{primary_color}};
                    padding: 20px;
                    margin: 24px 0;
                    border-radius: 0 8px 8px 0;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                }

                .info-box p {
                    margin: 0;
                    color: {{info_text}};
                    font-weight: 500;
                }

                /* Card Styles */
                .card {
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 24px;
                    margin: 24px 0;
                    box-shadow:
                        0 1px 3px 0 rgba(15, 23, 42, 0.1),
                        0 1px 2px 0 rgba(15, 23, 42, 0.06);
                }

                .card-navy {
                    background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
                    border: none;
                    color: white;
                }

                .card-orange {
                    background: linear-gradient(135deg, #fb923c 0%, #f97316 100%);
                    border: none;
                    color: white;
                }

                .card-title {
                    color: #1e3a8a;
                    font-size: 18px;
                    font-weight: 600;
                    margin-bottom: 8px;
                }

                .card-navy .card-title,
                .card-orange .card-title {
                    color: #ffffff;
                }

                /* Footer Styles */
                .footer {
                    padding: 40px;
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    border-top: 1px solid #e2e8f0;
                    position: relative;
                }

                .footer::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 40px;
                    right: 40px;
                    height: 1px;
                    background: linear-gradient(90deg, transparent, #fb923c, transparent);
                }

                .footer-content {
                    text-align: center;
                }

                .footer-logo {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    font-weight: 800;
                    color: #1e3a8a;
                    margin-bottom: 12px;
                    letter-spacing: -0.5px;
                }

                .footer-logo .logo-icon {
                    width: 30px;
                    height: 30px;
                    background: linear-gradient(135deg, #fb923c, #f97316);
                    border-radius: 8px;
                    margin-right: 10px;
                    font-size: 14px;
                }

                .footer-logo .logo-text {
                    background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .footer p {
                    color: #475569;
                    font-size: 14px;
                    margin: 8px 0;
                    line-height: 1.5;
                }

                .footer .legal {
                    font-size: 12px;
                    color: #64748b;
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                }

                .footer .social-links {
                    margin: 16px 0;
                }

                .footer .social-links a {
                    color: #475569;
                    margin: 0 8px;
                    font-size: 18px;
                    text-decoration: none;
                    transition: color 0.2s ease;
                    background: #f8fafc;
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    border: 1px solid #e2e8f0;
                }

                .footer .social-links a:hover {
                    color: #fb923c;
                    background: #ffffff;
                    border-color: #fb923c;
                }

                /* Special Elements */
                .badge {
                    display: inline-block;
                    background: {{primary_color}};
                    color: white;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 4px 12px;
                    border-radius: 20px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-left: 12px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }

                .badge-orange {
                    background: linear-gradient(135deg, #fb923c, #f97316);
                }

                .badge-blue {
                    background: linear-gradient(135deg, #1e40af, #1e3a8a);
                }

                .badge-green {
                    background: linear-gradient(135deg, #10b981, #059669);
                }

                .divider {
                    height: 1px;
                    background: linear-gradient(90deg, transparent, #fb923c, transparent);
                    margin: 32px 0;
                }

                .highlight {
                    color: #fb923c;
                    font-weight: 600;
                }

                .highlight-blue {
                    color: #1e40af;
                    font-weight: 600;
                }

                .highlight-green {
                    color: #10b981;
                    font-weight: 600;
                }

                .highlight-red {
                    color: #ef4444;
                    font-weight: 600;
                }

                /* Responsive Design */
                @media screen and (max-width: 768px) {
                    .email-container {
                        margin: 20px auto;
                        border-radius: 12px;
                    }

                    .header, .content, .footer {
                        padding: 32px 24px;
                    }

                    .logo {
                        font-size: 24px;
                    }

                    .logo-icon {
                        width: 36px;
                        height: 36px;
                        font-size: 16px;
                    }

                    .content h2 { font-size: 24px; }

                    .button {
                        padding: 14px 32px;
                        font-size: 14px;
                    }
                }

                @media screen and (max-width: 480px) {
                    .header, .content, .footer {
                        padding: 24px 20px;
                    }

                    .logo { font-size: 20px; }

                    .logo-icon {
                        width: 32px;
                        height: 32px;
                        font-size: 14px;
                    }

                    .content h2 { font-size: 20px; }
                }
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <div class="logo-container">
                        <div class="logo">
                            <div class="logo-icon">S</div>
                            <span class="logo-text">SashaInfinity<span class="logo-infinity">∞</span></span>
                        </div>
                    </div>
                    <div class="tagline">Learning Management System</div>
                </div>
                <div class="content">
                    {{content}}
                </div>
                <div class="footer">
                    <div class="footer-content">
                        <div class="footer-logo">
                            <div class="logo-icon">S</div>
                            <span class="logo-text">SashaInfinity</span>
                        </div>
                        <p>&copy; {{year}} SashaInfinity. All rights reserved.</p>
                        <div class="social-links">
                            <a href="#" title="Facebook">f</a>
                            <a href="#" title="Twitter">𝕏</a>
                            <a href="#" title="LinkedIn">in</a>
                            <a href="#" title="Instagram">📷</a>
                        </div>
                        <div class="legal">
                            This is an automated message. Please do not reply to this email.<br>
                            If you need assistance, please contact our support team at support@sashainfinity.com<br>
                            <a href="#" style="color: #64748b; text-decoration: none;">Privacy Policy</a> •
                            <a href="#" style="color: #64748b; text-decoration: none;">Terms of Service</a>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def get_verification_email(user_name: str, verification_link: str) -> tuple:
        """Get premium email verification template with Sasha's logo and orange/navy theme"""
        from datetime import datetime
        subject = "Verify Your Email Address - SashaInfinity"

        content = f"""
            <h2>Welcome to SashaInfinity, {user_name}</h2>
            <p>Thank you for joining <span class="highlight">SashaInfinity Learning Management System</span>, where excellence in education meets cutting-edge technology.</p>

            <p>To complete your registration and unlock full access to our premium learning platform, please verify your email address by clicking the button below:</p>

            <center>
                <a href="{verification_link}" class="button">Verify Email Address</a>
            </center>

            <p>If the button above doesn't work, you can use the secure link below:</p>
            <div class="link-box">
                <div class="link-box-label">Secure Verification Link</div>
                <a href="{verification_link}">{verification_link}</a>
            </div>

            <div class="info-box">
                <p><strong>🔒 Security Notice:</strong> This verification link will expire in <strong>24 hours</strong> for your account security.</p>
            </div>

            <p>Once verified, you'll gain access to:</p>
            <div class="card">
                <ul style="color: #475569; margin-left: 20px; margin-top: 16px;">
                    <li style="margin: 12px 0;">📚 Premium courses and learning materials</li>
                    <li style="margin: 12px 0;">🎓 Professional certification programs</li>
                    <li style="margin: 12px 0;">📊 Advanced progress tracking and analytics</li>
                    <li style="margin: 12px 0;">👥 Community collaboration and networking</li>
                    <li style="margin: 12px 0;">🏆 Achievement badges and certificates</li>
                </ul>
            </div>

            <div class="divider"></div>

            <p>If you did not create an account with SashaInfinity, please disregard this email. Your account security is our priority.</p>

            <p>Best regards,<br><strong>The SashaInfinity Team</strong></p>
        """

        # Style replacements for verification email (orange theme)
        template = EmailTemplates.get_base_template()
        template = template.replace("{{title}}", "Email Verification - SashaInfinity")
        template = template.replace("{{content}}", content)
        template = template.replace("{{primary_color}}", "#fb923c")
        template = template.replace("{{primary_dark}}", "#f97316")
        template = template.replace("{{primary_rgb}}", "251, 146, 60")
        template = template.replace("{{info_bg}}", "#fff7ed")
        template = template.replace("{{info_bg_light}}", "#fed7aa")
        template = template.replace("{{info_text}}", "#9a3412")
        template = template.replace("{{year}}", str(datetime.now().year))

        text_content = f"""
SashaInfinity - Email Verification

Hello {user_name},

Thank you for joining SashaInfinity Learning Management System, where excellence in education meets cutting-edge technology.

To complete your registration, please verify your email address by visiting:
{verification_link}

Security Notice: This verification link will expire in 24 hours for your account security.

Once verified, you'll gain access to:
• Premium courses and learning materials
• Professional certification programs
• Advanced progress tracking and analytics
• Community collaboration and networking
• Achievement badges and certificates

If you did not create an account with SashaInfinity, please disregard this email. Your account security is our priority.

Best regards,
The SashaInfinity Team

---
© {datetime.now().year} SashaInfinity. All rights reserved.
This is an automated email. Please do not reply to this message.
        """

        return subject, template, text_content

    @staticmethod
    def get_password_reset_email(user_name: str, reset_link: str) -> tuple:
        """Get premium password reset template with Sasha's logo and orange/navy theme"""
        from datetime import datetime
        subject = "Password Reset Request - SashaInfinity"

        content = f"""
            <h2>🔐 Password Reset Request</h2>
            <p>Hello {user_name},</p>

            <p>We received a secure request to reset your password for your <span class="highlight-red">SashaInfinity</span> account. To proceed with this security measure, please click the button below.</p>

            <center>
                <a href="{reset_link}" class="button button-red">Reset Password</a>
            </center>

            <p>If the button above doesn't work, you can use the secure link below:</p>
            <div class="link-box">
                <div class="link-box-label">Secure Reset Link</div>
                <a href="{reset_link}">{reset_link}</a>
            </div>

            <div class="info-box">
                <p><strong>⚠️ Critical Security Notice:</strong> This password reset link will expire in <strong>1 hour</strong> for your protection. Please act immediately.</p>
            </div>

            <p>If you did not request a password reset, please disregard this email. Your account remains secure, and no changes have been made.</p>

            <div class="card">
                <div class="card-title">🛡️ Security Best Practices</div>
                <ul style="color: #475569; margin-left: 20px; margin-top: 12px;">
                    <li style="margin: 8px 0;">Create a strong, unique password with at least 12 characters</li>
                    <li style="margin: 8px 0;">Use a combination of uppercase, lowercase, numbers, and symbols</li>
                    <li style="margin: 8px 0;">Enable two-factor authentication when available</li>
                    <li style="margin: 8px 0;">Never share your password with anyone</li>
                    <li style="margin: 8px 0;">Use a password manager to store your credentials securely</li>
                </ul>
            </div>

            <div class="divider"></div>

            <p>For additional security features and account management, visit your SashaInfinity dashboard.</p>

            <p>Best regards,<br><strong>The SashaInfinity Security Team</strong></p>
        """

        # Style replacements for password reset email (red theme for security)
        template = EmailTemplates.get_base_template()
        template = template.replace("{{title}}", "Password Reset - SashaInfinity")
        template = template.replace("{{content}}", content)
        template = template.replace("{{primary_color}}", "#ef4444")
        template = template.replace("{{primary_dark}}", "#dc2626")
        template = template.replace("{{primary_rgb}}", "239, 68, 68")
        template = template.replace("{{info_bg}}", "#fef2f2")
        template = template.replace("{{info_bg_light}}", "#fecaca")
        template = template.replace("{{info_text}}", "#991b1b")
        template = template.replace("{{year}}", str(datetime.now().year))

        text_content = f"""
SashaInfinity - Password Reset Request

Hello {user_name},

We received a secure request to reset your password for your SashaInfinity account.

To reset your password, please visit this link:
{reset_link}

Critical Security Notice: This password reset link will expire in 1 hour for your protection. Please act immediately.

If you did not request a password reset, please disregard this email. Your account remains secure, and no changes have been made.

Security Best Practices:
• Create a strong, unique password with at least 12 characters
• Use a combination of uppercase, lowercase, numbers, and symbols
• Enable two-factor authentication when available
• Never share your password with anyone
• Use a password manager to store your credentials securely

For additional security features and account management, visit your SashaInfinity dashboard.

Best regards,
The SashaInfinity Security Team

---
© {datetime.now().year} SashaInfinity. All rights reserved.
This is an automated email. Please do not reply to this message.
        """

        return subject, template, text_content

    @staticmethod
    def get_enrollment_confirmation_email(user_name: str, course_title: str, course_link: str) -> tuple:
        """Get premium enrollment confirmation template with Sasha's logo and orange/navy theme"""
        from datetime import datetime
        subject = f"🎓 Enrollment Confirmed - {course_title}"

        content = f"""
            <h2>🎉 Congratulations on Your Enrollment!</h2>
            <p>Hello {user_name},</p>

            <p>Welcome to your learning journey with <span class="highlight-green">SashaInfinity</span>! Your enrollment has been successfully processed and you're now ready to begin.</p>

            <div class="card card-orange">
                <div class="card-title">
                    {course_title} <span class="badge badge-orange">Enrolled</span>
                </div>
                <p style="color: #ffffff; font-size: 14px; margin-top: 8px;">
                    🎯 You now have full access to this premium course
                </p>
                <center>
                    <a href="{course_link}" class="button button-green">Start Learning Now</a>
                </center>
            </div>

            <div class="card card-navy">
                <div class="card-title">📚 Your Learning Journey Starts Here</div>
                <p style="color: #ffffff; font-size: 14px; margin-top: 8px;">
                    Access your course anytime, anywhere. Track your progress, earn certificates, and connect with a global community of learners.
                </p>
            </div>

            <div class="card">
                <div class="card-title">🌟 Tips for Learning Success</div>
                <ul style="color: #475569; margin-left: 20px; margin-top: 16px;">
                    <li style="margin: 12px 0;">📅 Create a consistent study schedule</li>
                    <li style="margin: 12px 0;">📝 Take detailed notes during lessons</li>
                    <li style="margin: 12px 0;">🎯 Set specific learning goals and milestones</li>
                    <li style="margin: 12px 0;">💬 Engage in course discussions and forums</li>
                    <li style="margin: 12px 0;">👨‍🏫 Connect with instructors for guidance</li>
                    <li style="margin: 12px 0;">📊 Track your progress regularly</li>
                    <li style="margin: 12px 0;">🏆 Complete all modules for certification</li>
                </ul>
            </div>

            <div class="divider"></div>

            <p>Our premium learning platform is designed to provide you with an engaging, effective, and transformative educational experience. You have lifetime access to this course materials.</p>

            <p>We're honored to be part of your educational journey and wish you tremendous success in your studies!</p>

            <p>Best regards,<br><strong>The SashaInfinity Learning Team</strong></p>
        """

        # Style replacements for enrollment email (green theme)
        template = EmailTemplates.get_base_template()
        template = template.replace("{{title}}", "Enrollment Confirmation - SashaInfinity")
        template = template.replace("{{content}}", content)
        template = template.replace("{{primary_color}}", "#10b981")
        template = template.replace("{{primary_dark}}", "#059669")
        template = template.replace("{{primary_rgb}}", "16, 185, 129")
        template = template.replace("{{info_bg}}", "#ecfdf5")
        template = template.replace("{{info_bg_light}}", "#d1fae5")
        template = template.replace("{{info_text}}", "#065f46")
        template = template.replace("{{year}}", str(datetime.now().year))

        text_content = f"""
SashaInfinity - Enrollment Confirmation

Congratulations on Your Enrollment!

Hello {user_name},

Welcome to your learning journey with SashaInfinity! Your enrollment has been successfully processed and you're now ready to begin.

Course: {course_title}
Status: Enrolled
Access: Full Lifetime Access

Access your course here: {course_link}

Your Learning Journey Starts Here
Access your course anytime, anywhere. Track your progress, earn certificates, and connect with a global community of learners.

Tips for Learning Success:
• Create a consistent study schedule
• Take detailed notes during lessons
• Set specific learning goals and milestones
• Engage in course discussions and forums
• Connect with instructors for guidance
• Track your progress regularly
• Complete all modules for certification

Our premium learning platform is designed to provide you with an engaging, effective, and transformative educational experience. You have lifetime access to this course materials.

We're honored to be part of your educational journey and wish you tremendous success in your studies!

Best regards,
The SashaInfinity Learning Team

---
© {datetime.now().year} SashaInfinity. All rights reserved.
This is an automated email. Please do not reply to this message.
        """

        return subject, template, text_content

# Convenience functions
async def send_verification_email(email: str, token: str, user_name: str = "User") -> bool:
    """Send email verification"""
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject, html_content, text_content = EmailTemplates.get_verification_email(user_name, verification_link)

    email_service = EmailService()
    return await email_service.send_email(email, subject, html_content, text_content)

async def send_password_reset_email(email: str, token: str) -> bool:
    """Send password reset email"""
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject, html_content, text_content = EmailTemplates.get_password_reset_email("User", reset_link)

    email_service = EmailService()
    return await email_service.send_email(email, subject, html_content, text_content)

async def send_enrollment_confirmation_email(email: str, user_name: str, course_title: str, course_id: int) -> bool:
    """Send enrollment confirmation email"""
    course_link = f"{settings.FRONTEND_URL}/courses/{course_id}/learn"
    subject, html_content, text_content = EmailTemplates.get_enrollment_confirmation_email(
        user_name, course_title, course_link
    )

    email_service = EmailService()
    return await email_service.send_email(email, subject, html_content, text_content)


async def send_welcome_email(email: str, user_name: str, role: str = "student") -> bool:
    """Send welcome email after successful signup"""
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
    courses_url = f"{settings.FRONTEND_URL}/courses"

    from datetime import datetime
    subject = f"Welcome to SashaInfinity, {user_name}!"

    # HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #fb923c 0%, #1e3a8a 100%); color: white; padding: 40px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ padding: 40px; background-color: #f9f9f9; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #fb923c, #f97316); color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
            .feature {{ background: white; padding: 20px; margin: 15px 0; border-left: 4px solid #fb923c; border-radius: 5px; }}
            .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to SashaInfinity! 🎉</h1>
                <p>Your learning journey starts now</p>
            </div>
            <div class="content">
                <p>Hi <strong>{user_name}</strong>,</p>
                <p>Welcome to <strong>SashaInfinity LMS</strong>! Your account has been successfully created, and you're ready to start learning.</p>
                <p>Your account type: <strong>{role.title()}</strong></p>

                <div class="feature">
                    <h3>🚀 Get Started</h3>
                    <p>Explore our catalog of premium courses and start your learning journey today.</p>
                </div>

                <div style="text-align: center;">
                    <a href="{courses_url}" class="button">Browse Courses</a>
                </div>

                <div class="feature">
                    <h3>📚 What You Can Do</h3>
                    <ul>
                        <li>Browse and enroll in courses</li>
                        <li>Track your progress and earn certificates</li>
                        <li>Connect with instructors and fellow learners</li>
                    </ul>
                </div>

                <p>Got questions? Our support team is here to help you succeed.</p>

                <p>Best regards,<br>
                <strong>The SashaInfinity Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} SashaInfinity. All rights reserved.</p>
                <p>This is an automated email. Please do not reply to this message.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
Welcome to SashaInfinity, {user_name}!

Hi {user_name},

Welcome to SashaInfinity LMS! Your account has been successfully created.

Your account type: {role.title()}

Get Started:
Explore our catalog of premium courses: {courses_url}

What You Can Do:
- Browse and enroll in courses
- Track your progress and earn certificates
- Connect with instructors and fellow learners

Got questions? Our support team is here to help you succeed.

Best regards,
The SashaInfinity Team

© {datetime.now().year} SashaInfinity. All rights reserved.
This is an automated email. Please do not reply to this message.
    """

    email_service = EmailService()
    return await email_service.send_email(email, subject, html_content, text_content)


async def send_login_notification_email(email: str, user_name: str, login_method: str = "Google") -> bool:
    """Send login notification email when user signs in with Google"""
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"

    from datetime import datetime
    from zoneinfo import ZoneInfo
    ist = ZoneInfo("Asia/Kolkata")
    login_time = datetime.now(ist).strftime("%B %d, %Y at %I:%M %p %Z")

    subject = f"Login Notification - SashaInfinity"

    # HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ padding: 30px; background-color: #f9f9f9; border-radius: 0 0 10px 10px; }}
            .info-box {{ background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #1e3a8a; border-radius: 5px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #1e3a8a, #1e40af); color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
            .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Login Notification</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{user_name}</strong>,</p>
                <p>This is to inform you that your SashaInfinity account was accessed using <strong>{login_method}</strong> sign-in.</p>

                <div class="info-box">
                    <h3>Login Details:</h3>
                    <p><strong>Date:</strong> {login_time}</p>
                    <p><strong>Method:</strong> {login_method}</p>
                    <p><strong>Email:</strong> {email}</p>
                </div>

                <p>If this was you, you can safely ignore this email.</p>
                <p style="color: #dc2626;"><strong>If you did not sign in to your account, please contact our support team immediately.</strong></p>

                <div style="text-align: center;">
                    <a href="{dashboard_url}" class="button">Go to Dashboard</a>
                </div>

                <p>Best regards,<br>
                <strong>The SashaInfinity Security Team</strong></p>
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} SashaInfinity. All rights reserved.</p>
                <p>This is an automated email. Please do not reply to this message.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
Login Notification - SashaInfinity

Hi {user_name},

This is to inform you that your SashaInfinity account was accessed using {login_method} sign-in.

Login Details:
Date: {login_time}
Method: {login_method}
Email: {email}

If this was you, you can safely ignore this email.

If you did not sign in to your account, please contact our support team immediately.

Go to dashboard: {dashboard_url}

Best regards,
The SashaInfinity Security Team

© {datetime.now().year} SashaInfinity. All rights reserved.
This is an automated email. Please do not reply to this message.
    """

    email_service = EmailService()
    return await email_service.send_email(email, subject, html_content, text_content)