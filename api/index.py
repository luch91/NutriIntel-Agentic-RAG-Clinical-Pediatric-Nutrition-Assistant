"""
Vercel Python serverless entry point for CPNA v1 backend.
Wraps the FastAPI app from app/api/router.py for Vercel deployment.
"""

from app.api.router import app

# Vercel expects a callable named 'app' or 'handler'
handler = app
