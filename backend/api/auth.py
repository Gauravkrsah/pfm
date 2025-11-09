from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import random
import time

router = APIRouter()

# In-memory OTP storage with expiry (use Redis in production)
otp_store = {}  # {email: {otp: str, expires: timestamp}}

class SendOTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

@router.post("/send-reset-otp")
async def send_reset_otp(request: SendOTPRequest):
    """Generate and return OTP for password reset"""
    try:
        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Store OTP with 10 minute expiry
        otp_store[request.email] = {
            "otp": otp,
            "expires": time.time() + 600  # 10 minutes
        }
        
        # In production, send OTP via email service (SendGrid, AWS SES, etc.)
        # For now, return it in response for testing
        return {
            "message": "OTP generated successfully",
            "otp": otp,  # Remove in production
            "note": "In production, this will be sent via email"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-reset-otp")
async def verify_reset_otp(request: VerifyOTPRequest):
    """Verify OTP - returns success if valid"""
    try:
        # Check if OTP exists
        stored = otp_store.get(request.email)
        if not stored:
            raise HTTPException(status_code=400, detail="No OTP found for this email")
        
        # Check expiry
        if time.time() > stored["expires"]:
            del otp_store[request.email]
            raise HTTPException(status_code=400, detail="OTP has expired")
        
        # Verify OTP
        if stored["otp"] != request.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        # Clear OTP after successful verification
        del otp_store[request.email]
        
        return {"message": "OTP verified successfully", "verified": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
