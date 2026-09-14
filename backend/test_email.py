#!/usr/bin/env python3
"""
Email Service Test Script
Run this to test your SMTP configuration
"""

import sys
import os

# Add app to path
sys.path.insert(0, '/app')

from app.services.email_service import EmailService
from app.core.config import get_settings

def test_email_configuration():
    """Test email service configuration"""
    settings = get_settings()
    
    print("=" * 50)
    print("Email Configuration Test")
    print("=" * 50)
    
    # Check configuration
    print(f"\n📋 Configuration:")
    print(f"  SMTP Host: {settings.SMTP_HOST or '❌ NOT SET'}")
    print(f"  SMTP Port: {settings.SMTP_PORT}")
    print(f"  SMTP User: {settings.SMTP_USER or '❌ NOT SET'}")
    print(f"  SMTP Password: {'✅ SET' if settings.SMTP_PASSWORD else '❌ NOT SET'}")
    print(f"  Email From: {settings.EMAIL_FROM}")
    
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        print("\n⚠️  SMTP not configured - running in MOCK mode")
        print("   Emails will be logged to console only")
    else:
        print("\n✅ SMTP configured - will attempt to send real emails")
    
    # Get test email
    print("\n" + "=" * 50)
    test_email = input("Enter test email address (or press Enter to skip): ").strip()
    
    if not test_email:
        print("Skipping email test")
        return
    
    print(f"\n📧 Sending test email to: {test_email}")
    print("=" * 50)
    
    # Send test email
    try:
        result = EmailService.send_course_deletion_notification(
            student_email=test_email,
            student_name="Test User",
            course_title="Introduction to Python Programming",
            course_id=999,
            deleted_by="System Administrator"
        )
        
        if result:
            print("\n✅ SUCCESS! Email sent successfully")
            if settings.SMTP_HOST and settings.SMTP_USER:
                print(f"   Check inbox at: {test_email}")
                print(f"   Also check spam folder if not in inbox")
            else:
                print(f"   Mock mode - check console logs above")
        else:
            print("\n❌ FAILED! Email sending failed")
            print("   Check the error logs above")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("  1. Check SMTP credentials in .env file")
        print("  2. Verify SMTP server is reachable")
        print("  3. Check if port is correct (587 for STARTTLS, 465 for SSL)")
        print("  4. Review backend logs: docker-compose logs backend")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_email_configuration()
