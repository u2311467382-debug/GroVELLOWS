"""
Security Middleware for GroVELLOWS App
Implements data protection, rate limiting, and security headers
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import time
import hashlib
import re
from typing import Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Rate limiting storage
rate_limit_storage: Dict[str, list] = defaultdict(list)

# Security configuration
SECURITY_CONFIG = {
    "rate_limit_requests": 100,  # Max requests per window
    "rate_limit_window": 60,     # Window in seconds
    "max_request_size": 10 * 1024 * 1024,  # 10MB max request size
    "blocked_ips": set(),
    "allowed_origins": [
        "https://constructbid-6.preview.emergentagent.com",
        "http://localhost:3000",
        "http://localhost:8001",
        "exp://",  # Expo Go
    ]
}

# Input sanitization patterns
DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # XSS scripts
    r'javascript:',                  # JavaScript URLs
    r'on\w+\s*=',                    # Event handlers
    r'eval\s*\(',                    # Eval statements
    r'document\.cookie',             # Cookie theft
    r'window\.location',             # Redirect attacks
    r'\$\{.*\}',                     # Template injection
    r'{{.*}}',                       # Template injection
]


class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware implementing multiple protection layers"""
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)
        
        # 1. Check if IP is blocked
        if client_ip in SECURITY_CONFIG["blocked_ips"]:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"}
            )
        
        # 2. Rate limiting
        if not self.check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )
        
        # 3. Request size check
        content_length = request.headers.get("content-length", 0)
        if int(content_length) > SECURITY_CONFIG["max_request_size"]:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request too large"}
            )
        
        # 4. Process request
        response = await call_next(request)
        
        # 5. Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Check if client is within rate limits"""
        current_time = time.time()
        window_start = current_time - SECURITY_CONFIG["rate_limit_window"]
        
        # Clean old entries
        rate_limit_storage[client_ip] = [
            t for t in rate_limit_storage[client_ip] if t > window_start
        ]
        
        # Check limit
        if len(rate_limit_storage[client_ip]) >= SECURITY_CONFIG["rate_limit_requests"]:
            return False
        
        # Record request
        rate_limit_storage[client_ip].append(current_time)
        return True


def sanitize_input(data: str) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not isinstance(data, str):
        return data
    
    sanitized = data
    
    # Remove dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    
    # HTML entity encoding for special characters
    sanitized = sanitized.replace('<', '&lt;')
    sanitized = sanitized.replace('>', '&gt;')
    sanitized = sanitized.replace('"', '&quot;')
    sanitized = sanitized.replace("'", '&#x27;')
    
    return sanitized


def sanitize_dict(data: dict) -> dict:
    """Recursively sanitize all string values in a dictionary"""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_input(v) if isinstance(v, str) else v 
                for v in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging without exposing actual values"""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> dict:
    """Check password strength and return requirements status"""
    return {
        "min_length": len(password) >= 8,
        "has_uppercase": bool(re.search(r'[A-Z]', password)),
        "has_lowercase": bool(re.search(r'[a-z]', password)),
        "has_digit": bool(re.search(r'\d', password)),
        "has_special": bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
        "is_strong": len(password) >= 8 and 
                     bool(re.search(r'[A-Z]', password)) and 
                     bool(re.search(r'[a-z]', password)) and 
                     bool(re.search(r'\d', password))
    }


# Data breach potential list
DATA_BREACH_RISKS = """
## Potential Data Breach Risks for GroVELLOWS App

### 1. User Authentication Data
- **Email addresses** - Could be harvested for phishing attacks
- **Password hashes** - If weak hashing, passwords could be cracked
- **JWT tokens** - If stolen, could allow unauthorized access
- **Session data** - Could enable session hijacking

### 2. Personal Information
- **User names and roles** - Could be used for social engineering
- **Department information** - Reveals company structure
- **LinkedIn profile links** - External profile exposure
- **Notification preferences** - Behavioral data

### 3. Business Sensitive Data
- **Tender information viewed** - Reveals business interests
- **Application status on tenders** - Competitive intelligence
- **Internal chat messages** - Confidential discussions
- **Shared tender lists** - Shows internal collaboration patterns
- **Claimed tenders** - Reveals active pursuits

### 4. Device & Technical Data
- **Expo push tokens** - Could be used to send malicious notifications
- **Device identifiers** - Tracking potential
- **IP addresses from API logs** - Location and network info
- **App usage patterns** - Behavioral profiling

### 5. Cloud Storage Risks
- **MongoDB connection strings** - Database access if exposed
- **API keys** - Service access if leaked
- **Backup data** - Historical data exposure

### 6. Network Transmission Risks
- **Man-in-the-middle attacks** - Data interception if HTTPS bypassed
- **API request/response data** - Could be logged by intermediaries

### Mitigation Measures Implemented:
✅ HTTPS enforcement (Strict-Transport-Security)
✅ XSS protection headers
✅ Content Security Policy
✅ Rate limiting
✅ Input sanitization
✅ Secure password hashing (bcrypt)
✅ JWT token expiration
✅ CORS restrictions
✅ Request size limits
"""


def get_data_breach_risks() -> str:
    """Return the data breach risk documentation"""
    return DATA_BREACH_RISKS
