"""
Certificate Verification API - Endpoints for verifying certificates online
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.models.user import User

router = APIRouter(prefix="/certificate-verification", tags=["Certificate Verification"])

@router.get("/verify/{verification_code}")
async def verify_certificate(
    verification_code: str,
    request: Request,
    db: Session = Depends(get_db),
    ts: Optional[str] = Query(None, description="Timestamp for QR code security"),
    sig: Optional[str] = Query(None, description="Signature for QR code integrity")
) -> Dict[str, Any]:
    """
    Verify a certificate by its secure verification code
    Returns certificate details if valid, or error if invalid
    """
    try:
        # SECURITY: Only accept verification codes, not certificate IDs
        # This prevents certificate ID enumeration attacks

        # Validate verification code format (must be URL-safe base64, 12 chars min)
        import re
        if not re.match(r'^[A-Za-z0-9_-]{8,}$', verification_code):
            raise HTTPException(
                status_code=400,
                detail="Invalid verification code format. Please use the verification code from your certificate QR code."
            )

        # QR Code Security: Validate timestamp and signature if provided
        if ts and sig:
            from app.services.certificate_service import CertificateService

            if not CertificateService.verify_secure_verification_url(verification_code, ts, sig):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired QR code. Please scan the QR code again to get a fresh verification link."
                )

        # Find the issued certificate with this verification code
        from app.models.certificate import IssuedCertificate
        certificate = db.query(IssuedCertificate).filter(
            IssuedCertificate.certificate_hash == verification_code,
            IssuedCertificate.is_valid == True
        ).first()

        if not certificate:
            raise HTTPException(
                status_code=404,
                detail="Certificate not found. This verification code may be invalid, expired, or the certificate has been revoked."
            )

        # Check if certificate has been invalidated
        if certificate.invalidated_date:
            raise HTTPException(
                status_code=400,
                detail="This certificate has been invalidated and is no longer valid."
            )

        # Check if certificate has expired
        if certificate.expires_at and certificate.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="This certificate has expired and is no longer valid."
            )

        # Get related data using the IssuedCertificate relationships
        course = db.query(Course).filter(Course.id == certificate.course_id).first()
        student = db.query(User).filter(User.id == certificate.user_id).first()

        if not course or not student:
            raise HTTPException(
                status_code=404,
                detail="Certificate data not found"
            )

        # Get instructor (Course FK column is `post_author`, not `instructor_id`)
        instructor = db.query(User).filter(User.id == course.post_author).first()

        # Log verification attempt for security audit
        from app.models.certificate import CertificateVerification
        verification_log = CertificateVerification(
            certificate_id=certificate.id,
            certificate_hash=verification_code,
            verified_by_ip=request.client.host if request.client else "unknown",
            verified_by_user_agent=request.headers.get("user-agent", "unknown"),
            verification_result="valid",
        )
        db.add(verification_log)
        db.commit()

        # Return verification data with secure verification code
        return {
            "valid": True,
            "verification_code": verification_code,
            "certificate_id": certificate.id,
            "student_name": student.display_name or f"{student.first_name} {student.last_name}",
            # student_email intentionally omitted: this endpoint is public
            # (anyone with a verification code) and must not leak the holder's PII.
            "course_title": course.post_title,
            "course_description": course.post_excerpt or "",
            "instructor_name": instructor.display_name if instructor else "Unknown",
            "completion_date": certificate.completion_date.isoformat() if certificate.completion_date else None,
            "issue_date": certificate.created_at.isoformat() if certificate.created_at else None,
            "course_completion_percentage": certificate.course_completion_percentage,
            "verified_at": datetime.utcnow().isoformat(),
            "certificate_url": certificate.certificate_download_url,
            "verification_message": "This certificate has been verified as authentic and was issued by SashaInfinity Technology."
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Certificate verification error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while verifying the certificate"
        )

@router.get("/check/{verification_code}")
async def quick_check_certificate(
    verification_code: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Quick check if certificate exists (lightweight endpoint) - SECURE VERSION
    Only works with verification codes, not certificate IDs
    """
    try:
        # SECURITY: Only accept verification codes, not certificate IDs
        # This prevents certificate ID enumeration attacks

        # Validate verification code format
        import re
        if not re.match(r'^[A-Za-z0-9_-]{8,}$', verification_code):
            return {
                "exists": False,
                "verification_code": verification_code,
                "valid": False,
                "error": "Invalid verification code format"
            }

        # Quick check using IssuedCertificate
        from app.models.certificate import IssuedCertificate
        certificate = db.query(IssuedCertificate).filter(
            IssuedCertificate.certificate_hash == verification_code,
            IssuedCertificate.is_valid == True
        ).first()

        # Check certificate validity status
        is_valid = False
        status_reason = None

        if certificate:
            # Check if certificate has been invalidated
            if certificate.invalidated_date:
                is_valid = False
                status_reason = "Certificate has been invalidated"
            # Check if certificate has expired
            elif certificate.expires_at and certificate.expires_at < datetime.utcnow():
                is_valid = False
                status_reason = "Certificate has expired"
            else:
                is_valid = True
                status_reason = "Certificate is valid"

        return {
            "exists": certificate is not None,
            "verification_code": verification_code,
            "valid": is_valid,
            "status_reason": status_reason,
            "invalidated": certificate.invalidated_date if certificate else None,
            "expires_at": certificate.expires_at.isoformat() if certificate and certificate.expires_at else None
        }

    except Exception as e:
        print(f"Certificate check error: {str(e)}")
        return {
            "exists": False,
            "verification_code": verification_code,
            "valid": False,
            "error": "System error"
        }
