"""
Shared VerificationEngine singleton.
Both question_service and distractor_service import from here
to avoid creating duplicate stateless instances.
"""
from services.verification import VerificationEngine

engine = VerificationEngine()
