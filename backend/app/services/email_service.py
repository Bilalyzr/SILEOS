"""
Email Service - Email notifications for SashaInfinity LMS
Supports both SMTP (production) and mock mode (development)
"""

from datetime import datetime
from html import escape as html_escape
from typing import List, Dict, Optional, Sequence, Tuple
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Email service for sending notifications via SMTP or mock mode"""

    @staticmethod
    def _send_smtp_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """
        Send email via SMTP server

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body

        Returns:
            bool: True if sent successfully
        """
        # Check if SMTP is configured
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("SMTP not configured, falling back to mock mode")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = subject

            # Attach plain text
            msg.attach(MIMEText(body, 'plain'))

            # Attach HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            # Connect to SMTP server
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                # Enable TLS encryption
                server.starttls()

                # Login
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

                # Send email
                server.send_message(msg)

            logger.info(f"✅ Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    def send_course_deletion_notification(
        student_email: str,
        student_name: str,
        course_title: str,
        course_id: int,
        deleted_by: str = "Administrator"
    ) -> bool:
        """
        Send notification to student about course deletion

        Args:
            student_email: Student's email address
            student_name: Student's display name
            course_title: Title of the deleted course
            course_id: ID of the deleted course
            deleted_by: Name of the admin who deleted the course

        Returns:
            bool: True if email was sent successfully
        """
        subject = f"Course Removed - {course_title}"

        # Plain text version
        text_body = f"""
Dear {student_name},

We regret to inform you that the course you were enrolled in has been removed from our platform.

Course Details:
- Title: {course_title}
- Course ID: {course_id}
- Deleted on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
- Action taken by: {deleted_by}

What this means for you:
- Your enrollment has been terminated
- You will no longer have access to course materials
- Your progress and certificates (if any) have been archived
- If you paid for this course, please contact support for refund information

We apologize for any inconvenience this may cause. If you have any questions or concerns,
please don't hesitate to reach out to our support team.

Best regards,
SashaInfinity LMS Team
        """

        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #f44336; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Course Deletion Notification</h1>
        </div>
        <div class="content">
            <p>Dear {student_name},</p>
            <p>We regret to inform you that the course you were enrolled in has been removed from our platform.</p>

            <div class="details">
                <h3>Course Details:</h3>
                <ul>
                    <li><strong>Title:</strong> {course_title}</li>
                    <li><strong>Course ID:</strong> {course_id}</li>
                    <li><strong>Deleted on:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</li>
                    <li><strong>Action taken by:</strong> {deleted_by}</li>
                </ul>
            </div>

            <h3>What this means for you:</h3>
            <ul>
                <li>Your enrollment has been terminated</li>
                <li>You will no longer have access to course materials</li>
                <li>Your progress and certificates (if any) have been archived</li>
                <li>If you paid for this course, please contact support for refund information</li>
            </ul>

            <p>We apologize for any inconvenience this may cause. If you have any questions or concerns,
            please don't hesitate to reach out to our support team.</p>

            <p>Best regards,<br>
            <strong>SashaInfinity LMS Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} SashaInfinity. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

        # Try SMTP first, fall back to mock if not configured
        if settings.SMTP_HOST and settings.SMTP_USER:
            return EmailService._send_smtp_email(student_email, subject, text_body, html_body)
        else:
            # Mock mode - log to console
            logger.info(f"📧 [MOCK EMAIL] Sending course deletion notification:")
            logger.info(f"   To: {student_email}")
            logger.info(f"   Subject: {subject}")
            logger.info(text_body)
            return True

    @staticmethod
    def send_bulk_course_deletion_notifications(
        notifications: List[Dict[str, any]]
    ) -> Dict[str, int]:
        """
        Send course deletion notifications to multiple students

        Args:
            notifications: List of dicts with keys: student_email, student_name,
                          course_title, course_id, deleted_by

        Returns:
            Dict with 'sent' and 'failed' counts
        """
        sent_count = 0
        failed_count = 0

        logger.info(f"📧 [BULK EMAIL] Sending {len(notifications)} course deletion notifications")

        for notification in notifications:
            try:
                success = EmailService.send_course_deletion_notification(
                    student_email=notification['student_email'],
                    student_name=notification['student_name'],
                    course_title=notification['course_title'],
                    course_id=notification['course_id'],
                    deleted_by=notification.get('deleted_by', 'Administrator')
                )
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to send notification to {notification.get('student_email')}: {e}")
                failed_count += 1

        logger.info(f"✅ Bulk email complete: {sent_count} sent, {failed_count} failed")

        return {
            'sent': sent_count,
            'failed': failed_count,
            'total': len(notifications)
        }

    @staticmethod
    def send_enrollment_termination_notice(
        student_email: str,
        student_name: str,
        course_title: str,
        reason: str = "Course has been removed"
    ) -> bool:
        """
        Send enrollment termination notice to student

        Args:
            student_email: Student's email
            student_name: Student's name
            course_title: Course title
            reason: Reason for termination

        Returns:
            bool: True if sent successfully
        """
        email_content = f"""
========================================
ENROLLMENT TERMINATION NOTICE
========================================

Dear {student_name},

Your enrollment in "{course_title}" has been terminated.

Reason: {reason}

If you believe this is an error or have questions, please contact our support team.

Best regards,
SashaInfinity LMS Team
========================================
        """

        logger.info(f"📧 [MOCK EMAIL] Enrollment termination notice:")
        logger.info(f"   To: {student_email}")
        logger.info(f"   Subject: Enrollment Terminated - {course_title}")
        logger.info(email_content)

        return True

    @staticmethod
    def send_enrollment_suspension_notice(
        student_email: str,
        student_name: str,
        course_title: str,
        reason: str = "Administrative action"
    ) -> bool:
        """
        Send enrollment suspension notice to student

        Args:
            student_email: Student's email address
            student_name: Student's display name
            course_title: Title of the course
            reason: Reason for the suspension

        Returns:
            bool: True if email was sent successfully
        """
        subject = f"Enrollment Suspended - {course_title}"

        # Plain text version
        text_body = f"""
Dear {student_name},

Your enrollment in "{course_title}" has been suspended.

Reason: {reason}

What this means for you:
- You will temporarily lose access to course materials
- Your progress is preserved and will be restored if the suspension is lifted

If you believe this is an error or have questions, please contact our support team.

Best regards,
SashaInfinity LMS Team
        """

        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #ff9800; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #ff9800; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Enrollment Suspension Notice</h1>
        </div>
        <div class="content">
            <p>Dear {student_name},</p>
            <p>Your enrollment in <strong>"{course_title}"</strong> has been suspended.</p>

            <div class="details">
                <h3>Suspension Details:</h3>
                <ul>
                    <li><strong>Course:</strong> {course_title}</li>
                    <li><strong>Reason:</strong> {reason}</li>
                    <li><strong>Suspended on:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</li>
                </ul>
            </div>

            <h3>What this means for you:</h3>
            <ul>
                <li>You will temporarily lose access to course materials</li>
                <li>Your progress is preserved and will be restored if the suspension is lifted</li>
            </ul>

            <p>If you believe this is an error or have questions, please contact our support team.</p>

            <p>Best regards,<br>
            <strong>SashaInfinity LMS Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} SashaInfinity. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

        return EmailService._send_or_mock(student_email, subject, text_body, html_body)

    @staticmethod
    def send_enrollment_completion_notification(
        student_email: str,
        student_name: str,
        course_title: str,
        course_id: int,
        completed_by: str = "Administrator",
        reason: str = "Administrative action"
    ) -> bool:
        """
        Send enrollment completion notification to student

        Args:
            student_email: Student's email address
            student_name: Student's display name
            course_title: Title of the completed course
            course_id: ID of the course
            completed_by: Name of the admin who marked the enrollment complete
            reason: Reason recorded for the completion

        Returns:
            bool: True if email was sent successfully
        """
        subject = f"Course Completed - {course_title}"

        # Plain text version
        text_body = f"""
Congratulations {student_name}!

Your enrollment in "{course_title}" has been marked as completed on SashaInfinity LMS.

Course Details:
- Title: {course_title}
- Course ID: {course_id}
- Completed on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
- Marked complete by: {completed_by}
- Note: {reason}

Well done on finishing the course — we wish you continued success in your learning journey!

Best regards,
SashaInfinity LMS Team
        """

        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #10b981; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #10b981; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Course Completed!</h1>
        </div>
        <div class="content">
            <p>Dear {student_name},</p>
            <p>Congratulations — your enrollment in <strong>"{course_title}"</strong> has been
            marked as completed on SashaInfinity LMS.</p>

            <div class="details">
                <h3>Course Details:</h3>
                <ul>
                    <li><strong>Title:</strong> {course_title}</li>
                    <li><strong>Course ID:</strong> {course_id}</li>
                    <li><strong>Completed on:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</li>
                    <li><strong>Marked complete by:</strong> {completed_by}</li>
                    <li><strong>Note:</strong> {reason}</li>
                </ul>
            </div>

            <p>Well done on finishing the course — we wish you continued success in your
            learning journey!</p>

            <p>Best regards,<br>
            <strong>SashaInfinity LMS Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} SashaInfinity. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

        return EmailService._send_or_mock(student_email, subject, text_body, html_body)

    @staticmethod
    def send_certificate_issued_notification(
        student_email: str,
        student_name: str,
        course_title: str,
        course_id: int,
        certificate_url: str,
        completion_date: str
    ) -> bool:
        """
        Send certificate issued notification to student

        Args:
            student_email: Student's email address
            student_name: Student's display name
            course_title: Title of the completed course
            course_id: ID of the course
            certificate_url: URL to download the certificate
            completion_date: Date when course was completed

        Returns:
            bool: True if email was sent successfully
        """
        subject = f"🎓 Certificate Issued - {course_title}"

        # Plain text version
        text_body = f"""
Congratulations {student_name}!

You have successfully completed "{course_title}" and your certificate has been issued!

Course Details:
- Title: {course_title}
- Course ID: {course_id}
- Completion Date: {completion_date}

Your certificate is now ready for download. You can download it using the link below:

{certificate_url}

This certificate verifies your successful completion of the course and can be shared on:
- LinkedIn
- Your resume/CV
- Your professional portfolio
- Social media

We're proud of your achievement and wish you continued success in your learning journey!

Best regards,
SashaInfinity LMS Team
        """

        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 30px; background-color: #f9f9f9; }}
        .certificate-box {{ background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #667eea; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .download-btn {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
        .download-btn:hover {{ background: linear-gradient(135deg, #764ba2 0%, #667eea 100%); }}
        .achievement {{ text-align: center; font-size: 48px; margin: 20px 0; }}
        .details {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
        .share-icons {{ text-align: center; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="achievement">🎓</div>
            <h1>Congratulations!</h1>
            <h2>Your Certificate is Ready</h2>
        </div>
        <div class="content">
            <p>Dear {student_name},</p>
            <p style="font-size: 18px; color: #667eea;"><strong>You did it!</strong></p>
            <p>We're thrilled to inform you that you have successfully completed <strong>"{course_title}"</strong> and your certificate has been issued!</p>

            <div class="certificate-box">
                <h3>📋 Course Details:</h3>
                <ul style="list-style: none; padding: 0;">
                    <li>📚 <strong>Course:</strong> {course_title}</li>
                    <li>🆔 <strong>Course ID:</strong> {course_id}</li>
                    <li>📅 <strong>Completed on:</strong> {completion_date}</li>
                </ul>
            </div>

            <div style="text-align: center;">
                <a href="{certificate_url}" class="download-btn">📥 Download Your Certificate</a>
            </div>

            <div class="details">
                <h3>📢 Share Your Achievement:</h3>
                <p>Your certificate verifies your successful completion and can be shared on:</p>
                <ul>
                    <li>💼 LinkedIn</li>
                    <li>📄 Your resume/CV</li>
                    <li>🌐 Your professional portfolio</li>
                    <li>📱 Social media platforms</li>
                </ul>
            </div>

            <p style="margin-top: 30px;">We're incredibly proud of your dedication and achievement. Keep up the excellent work and continue your learning journey!</p>

            <p>Best regards,<br>
            <strong>SashaInfinity LMS Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} SashaInfinity. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

        # Try SMTP first, fall back to mock if not configured
        if settings.SMTP_HOST and settings.SMTP_USER:
            return EmailService._send_smtp_email(student_email, subject, text_body, html_body)
        else:
            # Mock mode - log to console
            logger.info(f"📧 [MOCK EMAIL] Sending certificate notification:")
            logger.info(f"   To: {student_email}")
            logger.info(f"   Subject: {subject}")
            logger.info(text_body)
            return True

    @staticmethod
    def send_order_confirmation(
        customer_email: str,
        customer_name: str,
        order_id: int,
        order_items: List[Dict],
        total_amount: float,
        transaction_id: str
    ) -> bool:
        """
        Send order confirmation and invoice email

        Args:
            customer_email: Customer's email address
            customer_name: Customer's name
            order_id: Order ID
            order_items: List of order items with course details
            total_amount: Total order amount
            transaction_id: Payment transaction ID

        Returns:
            bool: True if email was sent successfully
        """
        subject = f"Order Confirmation #{order_id} - SashaInfinity LMS"

        # Build course list
        courses_html = ""
        courses_text = ""
        for item in order_items:
            courses_html += f"""
                <tr>
                    <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{item['title']}</td>
                    <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">₹{item['price']:.2f}</td>
                </tr>
            """
            courses_text += f"\n- {item['title']}: ₹{item['price']:.2f}"

        # Plain text version
        text_body = f"""
Dear {customer_name},

Thank you for your purchase! Your order has been confirmed.

Order Details:
Order ID: #{order_id}
Transaction ID: {transaction_id}
Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

Courses Purchased:{courses_text}

Total Amount: ₹{total_amount:.2f}

You can now access your courses by logging into your account at:
{settings.FRONTEND_URL}/my-courses

If you have any questions, please don't hesitate to contact our support team.

Best regards,
The SashaInfinity LMS Team
        """

        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f3f4f6;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">Order Confirmed!</h1>
        </div>

        <!-- Content -->
        <div style="background-color: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <p style="font-size: 16px; color: #374151; margin-bottom: 20px;">
                Dear {customer_name},
            </p>

            <p style="font-size: 16px; color: #374151; margin-bottom: 20px;">
                Thank you for your purchase! Your order has been confirmed and you now have access to your courses.
            </p>

            <!-- Order Info -->
            <div style="background-color: #f9fafb; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: #1f2937; font-size: 18px; margin-top: 0;">Order Details</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #6b7280;">Order ID:</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: bold;">#{order_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6b7280;">Transaction ID:</td>
                        <td style="padding: 8px 0; text-align: right; font-weight: bold;">{transaction_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #6b7280;">Date:</td>
                        <td style="padding: 8px 0; text-align: right;">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</td>
                    </tr>
                </table>
            </div>

            <!-- Courses Table -->
            <h2 style="color: #1f2937; font-size: 18px; margin-bottom: 15px;">Courses Purchased</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px;">
                <thead>
                    <tr style="background-color: #f9fafb;">
                        <th style="padding: 12px; text-align: left; color: #6b7280; font-weight: 600; border-bottom: 2px solid #e5e7eb;">Course</th>
                        <th style="padding: 12px; text-align: right; color: #6b7280; font-weight: 600; border-bottom: 2px solid #e5e7eb;">Price</th>
                    </tr>
                </thead>
                <tbody>
                    {courses_html}
                </tbody>
                <tfoot>
                    <tr>
                        <td style="padding: 15px 12px; font-weight: bold; font-size: 18px; border-top: 2px solid #e5e7eb;">Total</td>
                        <td style="padding: 15px 12px; font-weight: bold; font-size: 18px; text-align: right; color: #10b981; border-top: 2px solid #e5e7eb;">₹{total_amount:.2f}</td>
                    </tr>
                </tfoot>
            </table>

            <!-- CTA Button -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{settings.FRONTEND_URL}/my-courses" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 15px 40px; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    Access My Courses
                </a>
            </div>

            <p style="font-size: 14px; color: #6b7280; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                If you have any questions, please contact our support team.
            </p>

            <p style="font-size: 14px; color: #374151; margin-bottom: 0;">
                Best regards,<br>
                <strong>The SashaInfinity LMS Team</strong>
            </p>
        </div>

        <!-- Footer -->
        <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
            <p>© {datetime.now().year} SashaInfinity LMS. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

        # Try SMTP first, fall back to mock if not configured
        if settings.SMTP_HOST and settings.SMTP_USER:
            return EmailService._send_smtp_email(customer_email, subject, text_body, html_body)
        else:
            # Mock mode - log to console
            logger.info(f"📧 [MOCK EMAIL] Sending order confirmation:")
            logger.info(f"   To: {customer_email}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Order ID: #{order_id}")
            logger.info(f"   Total: ₹{total_amount:.2f}")
            logger.info(text_body)
            return True

    # ------------------------------------------------------------------
    # SS3 — Company / internship marketplace emails
    # ------------------------------------------------------------------

    @staticmethod
    def _send_or_mock(to_email: str, subject: str, text_body: str, html_body: Optional[str] = None) -> bool:
        """Try SMTP; fall back to mock-log in dev."""
        if settings.SMTP_HOST and settings.SMTP_USER:
            return EmailService._send_smtp_email(to_email, subject, text_body, html_body)
        logger.info(f"📧 [MOCK EMAIL] {subject}")
        logger.info(f"   To: {to_email}")
        logger.info(text_body)
        return True

    @staticmethod
    def send_candidate_interest_email(candidate_user, company, message: str) -> bool:
        """Notify a candidate that a company has expressed interest."""
        to_email = getattr(candidate_user, "user_email", None) or ""
        candidate_name = getattr(candidate_user, "display_name", None) or to_email
        company_name = getattr(company, "name", "A company")
        subject = f"{company_name} is interested in hiring you"
        inbox_url = f"{settings.FRONTEND_URL}/dashboard/internship-inbox"

        text_body = f"""
Hi {candidate_name},

Good news — {company_name} has expressed interest in you for an internship/role opportunity.

Their message:
-----
{message}
-----

You can accept or decline from your internship inbox:
{inbox_url}

If you accept, {company_name} will see your email and phone number so they can reach out directly.

Best regards,
SashaInfinity LMS Team
"""
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2>{company_name} is interested in you</h2>
  <p>Hi {candidate_name},</p>
  <p><strong>{company_name}</strong> wants to connect with you about an opportunity.</p>
  <blockquote style="background:#f5f5f5;padding:12px;border-left:4px solid #667eea;">{message}</blockquote>
  <p><a href="{inbox_url}" style="display:inline-block;background:#667eea;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">Open your inbox</a></p>
  <p style="color:#666;font-size:12px;">If you accept, the company will see your contact details.</p>
</div></body></html>
"""
        return EmailService._send_or_mock(to_email, subject, text_body, html_body)

    @staticmethod
    def send_internship_voucher_email(buyer_user, internship, voucher_code: str) -> bool:
        """Notify a buyer that their internship voucher is ready to redeem."""
        to_email = getattr(buyer_user, "user_email", None) or ""
        buyer_name = getattr(buyer_user, "display_name", None) or to_email
        internship_title = getattr(internship, "title", "your internship program")
        subject = "Your internship voucher — use it on any course"
        courses_url = f"{settings.FRONTEND_URL}/courses"

        text_body = f"""
Hi {buyer_name},

Thank you for purchasing the "{internship_title}" internship program on
SashaInfinity LMS.

Here is your single-use voucher code:

    {voucher_code}

How to redeem:
  1. Go to the course catalogue: {courses_url}
  2. Pick any course you want to enrol in (free or paid — your voucher covers
     the full price).
  3. On the checkout / enrol screen, paste the voucher code above into the
     coupon / code field and submit.

Your voucher is single-use. Once redeemed against a course, it cannot be
used again.

Best regards,
SashaInfinity LMS Team
"""
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2>Your internship voucher is ready</h2>
  <p>Hi {buyer_name},</p>
  <p>Thank you for purchasing <strong>{internship_title}</strong>.</p>
  <p>Your single-use voucher code:</p>
  <div style="font-family:monospace;font-size:22px;background:#f5f5f5;border:1px dashed #667eea;padding:16px;text-align:center;border-radius:6px;letter-spacing:2px;">
    {voucher_code}
  </div>
  <p style="margin-top:16px;">Paste this code into the coupon field on any
  course checkout to enrol free of charge.</p>
  <p><a href="{courses_url}" style="display:inline-block;background:#667eea;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">Browse courses</a></p>
  <p style="color:#666;font-size:12px;">The voucher is single-use. Once redeemed on a course, it cannot be reused.</p>
</div></body></html>
"""
        return EmailService._send_or_mock(to_email, subject, text_body, html_body)

    @staticmethod
    def send_company_approved_email(company) -> bool:
        """Notify a company that their account has been approved by an admin."""
        to_email = getattr(company, "contact_email", "") or ""
        company_name = getattr(company, "name", "your company")
        subject = f"Your {company_name} account is approved"
        dash_url = f"{settings.FRONTEND_URL}/company/dashboard"

        text_body = f"""
Hi {company_name} team,

Your company account on SashaInfinity LMS has been approved. You can now sign in
and start browsing candidates:

{dash_url}

Best regards,
SashaInfinity LMS Team
"""
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2>Welcome aboard, {company_name}!</h2>
  <p>Your company account has been approved. You can now browse candidates and express interest.</p>
  <p><a href="{dash_url}" style="display:inline-block;background:#10b981;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">Open company dashboard</a></p>
</div></body></html>
"""
        return EmailService._send_or_mock(to_email, subject, text_body, html_body)

    @staticmethod
    def send_company_setup_link_email(email: str, setup_token: str) -> bool:
        """Send admin-invited company a setup link to choose their password."""
        subject = "Complete your SashaInfinity company account setup"
        setup_url = f"{settings.FRONTEND_URL}/for-companies/signup?setup_token={setup_token}"

        text_body = f"""
Hello,

An administrator has pre-approved a company account for this email address on
SashaInfinity LMS. To complete setup and choose a password, use the link below
(valid for 48 hours):

{setup_url}

If you didn't expect this, you can safely ignore this email.

Best regards,
SashaInfinity LMS Team
"""
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2>Complete your company account setup</h2>
  <p>An administrator has invited your company to SashaInfinity LMS.</p>
  <p><a href="{setup_url}" style="display:inline-block;background:#667eea;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">Set your password</a></p>
  <p style="color:#666;font-size:12px;">This link is valid for 48 hours.</p>
</div></body></html>
"""
        return EmailService._send_or_mock(email, subject, text_body, html_body)

    @staticmethod
    def send_manager_setup_link_email(to_email: str, token: str) -> bool:
        """Send manager-setup email with the given token."""
        link = f"{settings.FRONTEND_URL}/company/managers/accept?token={token}"
        subject = "You've been invited as a company manager"
        text_body = f"""
Hello,

You've been invited to manage interns on the SashaInfinity LMS.

Open this link to set your password and log in (valid for 7 days):

{link}

If you didn't expect this, you can safely ignore this email.

Best regards,
SashaInfinity LMS Team
"""
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2>You're invited as a company manager</h2>
  <p>You've been invited to manage interns on SashaInfinity LMS.</p>
  <p><a href="{link}" style="display:inline-block;background:#667eea;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">Set your password</a></p>
  <p style="color:#666;font-size:12px;">This link is valid for 7 days.</p>
</div></body></html>
"""
        return EmailService._send_or_mock(to_email, subject, text_body, html_body)

    @staticmethod
    def send_interest_accepted_email(company, candidate) -> bool:
        """Notify a company that the candidate has accepted their interest."""
        to_email = getattr(company, "contact_email", "") or ""
        company_name = getattr(company, "name", "your company")
        candidate_name = getattr(candidate, "display_name", None) or getattr(
            candidate, "user_email", "the candidate"
        )
        candidate_email = getattr(candidate, "user_email", "")
        pipeline_url = f"{settings.FRONTEND_URL}/company/dashboard"

        subject = f"{candidate_name} accepted your interest"
        text_body = f"""
Hi {company_name} team,

Great news — {candidate_name} accepted your expression of interest on
SashaInfinity LMS. You can now reach out directly:

Candidate: {candidate_name}
Email: {candidate_email}

See the full pipeline here:
{pipeline_url}

Best regards,
SashaInfinity LMS Team
"""
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2>{candidate_name} accepted your interest</h2>
  <p>You can now contact them directly at <a href="mailto:{candidate_email}">{candidate_email}</a>.</p>
  <p><a href="{pipeline_url}" style="display:inline-block;background:#10b981;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">View pipeline</a></p>
</div></body></html>
"""
        return EmailService._send_or_mock(to_email, subject, text_body, html_body)

    @staticmethod
    def send_internship_request_approved_email(to_email: str, title: str, slug: str) -> bool:
        """Notify a company that their internship request has been approved."""
        internship_url = f"{settings.FRONTEND_URL}/internships/{slug}"

        subject = f"Your internship request '{title}' has been approved"
        text_body = f"""
Hi,

Great news! Your internship request has been approved and is now live on SashaInfinity LMS.

Internship: {title}
You can view it here: {internship_url}

You can now start accepting student applications and vouchers.

Best regards,
SashaInfinity LMS Team
"""
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2>Your internship request has been approved</h2>
  <p>Your internship <strong>{title}</strong> is now live.</p>
  <p><a href="{internship_url}" style="display:inline-block;background:#10b981;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">View internship</a></p>
</div></body></html>
"""
        return EmailService._send_or_mock(to_email, subject, text_body, html_body)

    @staticmethod
    def send_internship_request_rejected_email(to_email: str, title: str, reason: str) -> bool:
        """Notify a company that their internship request has been rejected."""
        subject = f"Update on your internship request '{title}'"
        text_body = f"""
Hi,

Thank you for your interest in hosting an internship on SashaInfinity LMS.

After review, we regret to inform you that your request for '{title}' has not been approved at this time.

Reason: {reason}

You may submit a new request with modified details at any time.

Best regards,
SashaInfinity LMS Team
"""
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2>Update on your internship request</h2>
  <p>Your request for <strong>{title}</strong> has not been approved at this time.</p>
  <p><strong>Reason:</strong> {reason}</p>
  <p>You may submit a new request with modified details at any time.</p>
</div></body></html>
"""
        return EmailService._send_or_mock(to_email, subject, text_body, html_body)

    # ------------------------------------------------------------------
    # Admin → student direct messages (Admin dashboard ▸ Messages)
    # ------------------------------------------------------------------

    @staticmethod
    def is_smtp_configured() -> bool:
        """True when a real SMTP delivery is possible (otherwise: mock mode)."""
        return bool(settings.SMTP_HOST and settings.SMTP_USER)

    @staticmethod
    def _build_admin_message(
        recipient_name: str,
        subject: str,
        body: str,
        sender_name: str,
    ) -> Tuple[str, str]:
        """Render the plain-text and HTML bodies for an admin message."""
        dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
        greeting = recipient_name or "there"

        text_body = f"""
Hi {greeting},

{body}

—
{sender_name}
SashaInfinity LMS

You can also read this message in your dashboard:
{dashboard_url}
"""
        # The body is admin-authored free text from a textarea: escape it before
        # embedding in HTML and keep the author's line breaks.
        safe_body = html_escape(body).replace("\n", "<br>")
        html_body = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:24px;">
  <h2 style="margin-top:0;">{html_escape(subject)}</h2>
  <p>Hi {html_escape(greeting)},</p>
  <div style="background:#f8fafc;border-left:4px solid #667eea;padding:12px 16px;line-height:1.6;">{safe_body}</div>
  <p style="margin-top:24px;">— {html_escape(sender_name)}<br><span style="color:#666;">SashaInfinity LMS</span></p>
  <p><a href="{dashboard_url}" style="display:inline-block;background:#667eea;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">Open your dashboard</a></p>
</div></body></html>
"""
        return text_body, html_body

    @staticmethod
    def send_admin_message_email(
        to_email: str,
        recipient_name: str,
        subject: str,
        body: str,
        sender_name: str = "SashaInfinity Team",
    ) -> bool:
        """Deliver a single admin message by email."""
        if not to_email:
            return False
        text_body, html_body = EmailService._build_admin_message(
            recipient_name, subject, body, sender_name
        )
        return EmailService._send_or_mock(to_email, subject, text_body, html_body)

    @staticmethod
    def send_admin_message_emails(
        recipients: Sequence[Tuple[str, str]],
        subject: str,
        body: str,
        sender_name: str = "SashaInfinity Team",
    ) -> Dict[str, bool]:
        """
        Bulk-deliver an admin message over a single SMTP connection.

        `recipients` is a sequence of (email, display_name). Returns
        {email: delivered?} so the caller can report an honest per-recipient
        result instead of assuming every row was mailed. One reused connection
        matters here: admins routinely select dozens of students at once and a
        fresh SMTP handshake per student made the request time out.
        """
        results: Dict[str, bool] = {}
        targets = [(e, n) for e, n in recipients if e]
        if not targets:
            return results

        if not EmailService.is_smtp_configured():
            for email, name in targets:
                text_body, _ = EmailService._build_admin_message(name, subject, body, sender_name)
                logger.info(f"📧 [MOCK EMAIL] {subject}")
                logger.info(f"   To: {email}")
                logger.info(text_body)
                results[email] = True
            return results

        server = None
        try:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        except Exception as e:
            logger.error(f"❌ SMTP connection failed for bulk admin message: {e}")
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass
            return {email: False for email, _ in targets}

        try:
            for email, name in targets:
                text_body, html_body = EmailService._build_admin_message(
                    name, subject, body, sender_name
                )
                try:
                    msg = MIMEMultipart('alternative')
                    msg['From'] = settings.EMAIL_FROM
                    msg['To'] = email
                    msg['Subject'] = subject
                    msg.attach(MIMEText(text_body, 'plain'))
                    msg.attach(MIMEText(html_body, 'html'))
                    server.send_message(msg)
                    results[email] = True
                except Exception as e:
                    # One bad address must not abort the rest of the batch.
                    logger.error(f"❌ Failed to send admin message to {email}: {e}")
                    results[email] = False
        finally:
            try:
                server.quit()
            except Exception:
                pass

        delivered = sum(1 for ok in results.values() if ok)
        logger.info(f"✅ Admin message '{subject}' delivered to {delivered}/{len(targets)} recipients")
        return results

    @staticmethod
    def send_payment_alert(subject: str, body: str) -> bool:
        """Operational alert for the payment pipeline (reconciliation
        failures, unfixable orphaned captures). Falls back to logging when
        SMTP is unconfigured — the alert must never crash the caller."""
        to_email = getattr(settings, "ADMIN_EMAIL", "") or settings.EMAIL_FROM
        try:
            sent = EmailService._send_smtp_email(to_email, f"[LMS payments] {subject}", body)
        except Exception:
            logger.exception("payment alert email raised")
            sent = False
        if not sent:
            logger.error("PAYMENT ALERT (email not sent): %s — %s", subject, body)
        return sent
