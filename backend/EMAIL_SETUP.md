# Email Server Integration Guide

This guide explains how to integrate your VPS email server (with RoundCube) with the SashaInfinity LMS.

## Overview

The application now supports real SMTP email sending for:
- Course deletion notifications
- Enrollment notifications
- Certificate issuance
- Other system notifications

## Prerequisites

1. **Email Server**: A working SMTP server on your VPS
2. **Email Account**: An email account (e.g., `noreply@yoursubdomain.yourdomain.com`)
3. **SMTP Credentials**: Username and password for authentication
4. **SMTP Details**: Host, port, and encryption type

## Configuration Steps

### 1. Locate Your Email Server Details

From your VPS email server (usually with RoundCube), you need:

- **SMTP Host**: Usually `mail.yourdomain.com` or `smtp.yourdomain.com`
- **SMTP Port**: 
  - Port `587` for STARTTLS (recommended)
  - Port `465` for SSL/TLS
  - Port `25` for non-encrypted (not recommended)
- **Username**: Your full email address (e.g., `noreply@yoursubdomain.yourdomain.com`)
- **Password**: Your email account password

### 2. Configure Environment Variables

Create or update the `.env` file in the `backend/` directory:

```bash
cd backend
cp .env.example .env
```

Edit the `.env` file and update these values:

```env
# Email / SMTP Configuration
SMTP_HOST=mail.yoursubdomain.yourdomain.com
SMTP_PORT=587
SMTP_USER=noreply@yoursubdomain.yourdomain.com
SMTP_PASSWORD=your_actual_password
EMAIL_FROM=SashaInfinity LMS <noreply@yoursubdomain.yourdomain.com>
```

### 3. Common SMTP Configurations

#### Using STARTTLS (Port 587) - Recommended
```env
SMTP_HOST=mail.yourdomain.com
SMTP_PORT=587
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=your_password
EMAIL_FROM=SashaInfinity LMS <noreply@yourdomain.com>
```

#### Using SSL/TLS (Port 465)
If your server uses port 465, you'll need to modify the email service code to use `SMTP_SSL` instead of `SMTP` with `starttls()`.

The current implementation uses STARTTLS (port 587). If you need port 465, update `email_service.py`:

```python
# Change this line:
with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
    server.starttls()

# To this:
with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
    # No starttls() needed for SSL
```

### 4. Testing the Configuration

#### Method 1: Using Python Script

Create a test script `test_email.py`:

```python
import os
import sys
sys.path.insert(0, '/app')

from app.services.email_service import EmailService

# Test sending an email
result = EmailService.send_course_deletion_notification(
    student_email="your-test-email@example.com",
    student_name="Test User",
    course_title="Test Course",
    course_id=1,
    deleted_by="Test Admin"
)

if result:
    print("✅ Email sent successfully!")
else:
    print("❌ Email sending failed. Check logs.")
```

Run the test:
```bash
docker-compose exec backend python test_email.py
```

#### Method 2: Test via Backend Logs

1. Restart the backend to load new environment variables:
```bash
docker-compose restart backend
```

2. Try force-deleting a course with enrollments (as admin)
3. Check backend logs for email sending:
```bash
docker-compose logs backend --tail=50 | grep -i email
```

### 5. Verify Email Delivery

1. **Check Backend Logs**: Look for success/failure messages
   ```bash
   docker-compose logs backend | grep "Email sent"
   ```

2. **Check Your Email**: Verify the email arrived in the recipient's inbox

3. **Check Spam Folder**: First emails may land in spam

### 6. Troubleshooting

#### Issue: Connection Refused
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solutions**:
- Verify SMTP_HOST is correct
- Check if your firewall allows outbound connections on SMTP_PORT
- Ensure the SMTP server is running

#### Issue: Authentication Failed
```
SMTPAuthenticationError: Username and Password not accepted
```

**Solutions**:
- Verify SMTP_USER is the full email address
- Check SMTP_PASSWORD is correct
- Some servers require app-specific passwords

#### Issue: TLS/SSL Errors
```
ssl.SSLError: [SSL: WRONG_VERSION_NUMBER]
```

**Solutions**:
- Wrong port/encryption combination
- If using port 465, modify code to use `SMTP_SSL`
- If using port 587, ensure STARTTLS is supported

#### Issue: Email in Spam
**Solutions**:
- Configure SPF records for your domain
- Set up DKIM signing
- Configure DMARC policy
- Ensure reverse DNS is configured

### 7. Production Best Practices

1. **Use App-Specific Passwords**: If available, create app-specific passwords instead of using your main email password

2. **Enable SPF, DKIM, DMARC**: Configure these DNS records to improve deliverability

3. **Monitor Email Logs**: Regularly check logs for failed emails

4. **Rate Limiting**: Consider implementing rate limiting for bulk emails

5. **Use Queue System**: For production, consider using a queue system (Celery + Redis) for asynchronous email sending

6. **Dedicated Email Account**: Use a dedicated email like `noreply@` or `notifications@` instead of personal emails

## Email Templates

The system includes professional HTML email templates with:
- Responsive design
- Plain text fallback
- Branded headers and footers
- Clear call-to-action sections

You can customize email templates in:
```
backend/app/services/email_service.py
```

## Supported Email Types

Currently implemented:
- ✅ Course deletion notifications
- ✅ Enrollment termination notices

To be implemented:
- Welcome emails
- Password reset emails
- Certificate issuance notifications
- Assignment submission confirmations
- Course completion congratulations

## Support

For issues with email integration, check:
1. Backend logs: `docker-compose logs backend`
2. Email service code: `backend/app/services/email_service.py`
3. Configuration: `backend/app/core/config.py`

## Example RoundCube Configuration

If using RoundCube, your typical settings might be:

```
Incoming (IMAP):
- Server: mail.yourdomain.com
- Port: 993 (SSL/TLS) or 143 (STARTTLS)

Outgoing (SMTP):
- Server: mail.yourdomain.com
- Port: 587 (STARTTLS) or 465 (SSL/TLS)
- Authentication: Required
- Username: Full email address
```

Use the same SMTP settings in your `.env` file.
