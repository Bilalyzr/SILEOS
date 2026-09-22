#!/usr/bin/env python3
"""
Test script to send all email templates for verification
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.utils.email import (
    send_verification_email,
    send_password_reset_email,
    send_enrollment_confirmation_email,
    EmailService,
    EmailTemplates
)

async def send_all_test_emails():
    """Send all email templates for testing"""

    recipient_email = "ragavendratraders7480@gmail.com"

    print("🚀 Sending test emails to verify new professional designs...")
    print(f"📧 Recipient: {recipient_email}")
    print()

    try:
        # Test 1: Email Verification
        print("1️⃣ Sending Email Verification Template...")
        verification_success = await send_verification_email(
            email=recipient_email,
            token="test-verification-token-12345",
            user_name="Raghavendra"
        )
        print(f"   ✅ Verification email {'sent successfully' if verification_success else 'failed to send'}")

        # Test 2: Password Reset
        print("2️⃣ Sending Password Reset Template...")
        reset_success = await send_password_reset_email(
            email=recipient_email,
            token="test-reset-token-67890"
        )
        print(f"   ✅ Password reset email {'sent successfully' if reset_success else 'failed to send'}")

        # Test 3: Enrollment Confirmation
        print("3️⃣ Sending Enrollment Confirmation Template...")
        enrollment_success = await send_enrollment_confirmation_email(
            email=recipient_email,
            user_name="Raghavendra",
            course_title="Advanced Python Programming",
            course_id=1
        )
        print(f"   ✅ Enrollment confirmation email {'sent successfully' if enrollment_success else 'failed to send'}")

        print()
        print("🎉 All test emails have been processed!")
        print()
        print("📋 What to check in your inbox:")
        print("   • Clean, professional design with SashaInfinity branding")
        print("   • Proper color scheme (Blue, Red, Green for different email types)")
        print("   • Responsive layout on mobile and desktop")
        print("   • Professional typography and spacing")
        print("   • Working buttons and links")
        print()
        print("🔍 Note: If SMTP is not configured, emails will be logged in console")
        print("   In that case, copy the HTML content to test locally.")

        return verification_success and reset_success and enrollment_success

    except Exception as e:
        print(f"❌ Error sending test emails: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("📧 SashaInfinity LMS - Email Template Test")
    print("=" * 60)
    print()

    success = asyncio.run(send_all_test_emails())

    print()
    if success:
        print("✅ All emails processed successfully!")
    else:
        print("❌ Some emails failed to send. Check configuration above.")

    print("=" * 60)