"""
Financial Simulator
Simulates revenue cycle, claims processing, and financial workflows (Change Healthcare)
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ClaimStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DENIED = "denied"
    APPEALED = "appealed"
    PAID = "paid"


class PaymentStatus(Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    WRITTEN_OFF = "written_off"


@dataclass
class Claim:
    """Insurance claim representation"""
    claim_id: str
    patient_id: str
    service_date: float
    amount: float
    status: ClaimStatus
    submission_date: Optional[float] = None
    denial_reason: Optional[str] = None
    appeal_date: Optional[float] = None
    payment_date: Optional[float] = None
    paid_amount: float = 0.0
    cpt_codes: List[str] = field(default_factory=list)
    icd_codes: List[str] = field(default_factory=list)


@dataclass
class FinancialState:
    """Current financial state"""
    total_revenue: float
    accounts_receivable: float
    claims_pending: int
    claims_approved: int
    claims_denied: int
    denial_rate: float
    average_days_to_payment: float
    collection_rate: float
    revenue_leakage: float
    time: float = 0.0


class FinancialSimulator:
    """
    Simulates revenue cycle and financial operations
    Mimics Change Healthcare revenue cycle management
    """
    
    DENIAL_REASONS = [
        "missing_information",
        "duplicate_claim",
        "coverage_terminated",
        "prior_authorization_required",
        "incorrect_coding",
        "timely_filing",
        "medical_necessity"
    ]
    
    CPT_CODES = [
        "99213", "99214", "99215",  # Office visits
        "36415", "80053", "85025",  # Lab tests
        "70450", "72141", "73060",  # Imaging
        "27447", "29881", "45378"   # Procedures
    ]
    
    ICD_CODES = [
        "E11.9", "I10", "J44.9",  # Diabetes, Hypertension, COPD
        "A41.9", "I50.9", "N18.6"  # Sepsis, Heart failure, CKD
    ]
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed) if seed else np.random.default_rng()
        
        self.claims: Dict[str, Claim] = {}
        self.total_revenue = 0.0
        self.accounts_receivable = 0.0
        self.payment_history: List[Dict[str, Any]] = []
        
        self.time = 0.0
        
        # Denial rates by reason
        self.denial_probabilities = {
            "missing_information": 0.15,
            "duplicate_claim": 0.05,
            "coverage_terminated": 0.10,
            "prior_authorization_required": 0.20,
            "incorrect_coding": 0.25,
            "timely_filing": 0.10,
            "medical_necessity": 0.15
        }
    
    def create_claim(
        self,
        patient_id: str,
        amount: float,
        cpt_codes: Optional[List[str]] = None,
        icd_codes: Optional[List[str]] = None,
        service_date: Optional[float] = None
    ) -> Claim:
        """Create a new claim"""
        claim_id = f"CLM_{self.rng.integers(100000, 999999)}"
        
        claim = Claim(
            claim_id=claim_id,
            patient_id=patient_id,
            service_date=service_date or self.time,
            amount=amount,
            status=ClaimStatus.PENDING,
            cpt_codes=cpt_codes or self.rng.choice(self.CPT_CODES, size=1).tolist(),
            icd_codes=icd_codes or self.rng.choice(self.ICD_CODES, size=1).tolist()
        )
        
        self.claims[claim_id] = claim
        self.accounts_receivable += amount
        
        return claim
    
    def submit_claim(self, claim_id: str) -> bool:
        """Submit claim to insurance"""
        if claim_id not in self.claims:
            return False
        
        claim = self.claims[claim_id]
        if claim.status != ClaimStatus.PENDING:
            return False
        
        claim.status = ClaimStatus.SUBMITTED
        claim.submission_date = self.time
        
        # Simulate processing delay
        processing_delay = self.rng.exponential(7.0)  # Average 7 days
        
        # Determine if claim will be denied
        denial_prob = self._calculate_denial_probability(claim)
        if self.rng.random() < denial_prob:
            claim.status = ClaimStatus.DENIED
            claim.denial_reason = self.rng.choice(list(self.denial_probabilities.keys()))
        else:
            claim.status = ClaimStatus.APPROVED
        
        return True
    
    def _calculate_denial_probability(self, claim: Claim) -> float:
        """Calculate probability of claim denial"""
        base_prob = 0.15
        
        # Increase probability for certain conditions
        if len(claim.cpt_codes) > 3:
            base_prob += 0.1  # Multiple procedures
        
        if claim.amount > 10000:
            base_prob += 0.15  # High-value claims
        
        # Check for common denial reasons
        if "prior_authorization_required" in self.denial_probabilities:
            base_prob += self.denial_probabilities["prior_authorization_required"] * 0.3
        
        return min(0.8, base_prob)
    
    def appeal_claim(self, claim_id: str) -> bool:
        """Appeal a denied claim"""
        if claim_id not in self.claims:
            return False
        
        claim = self.claims[claim_id]
        if claim.status != ClaimStatus.DENIED:
            return False
        
        claim.status = ClaimStatus.APPEALED
        claim.appeal_date = self.time
        
        # Appeal success rate
        appeal_success = self.rng.random() < 0.4  # 40% success rate
        
        if appeal_success:
            claim.status = ClaimStatus.APPROVED
            claim.denial_reason = None
        
        return True
    
    def process_payment(self, claim_id: str) -> bool:
        """Process payment for approved claim"""
        if claim_id not in self.claims:
            return False
        
        claim = self.claims[claim_id]
        if claim.status != ClaimStatus.APPROVED:
            return False
        
        # Payment amount (may be less than claim amount)
        payment_amount = claim.amount * self.rng.uniform(0.85, 1.0)
        
        claim.paid_amount = payment_amount
        claim.payment_date = self.time
        claim.status = ClaimStatus.PAID
        
        self.total_revenue += payment_amount
        self.accounts_receivable -= claim.amount
        
        self.payment_history.append({
            "claim_id": claim_id,
            "amount": payment_amount,
            "date": self.time,
            "days_to_payment": self.time - claim.submission_date if claim.submission_date else 0
        })
        
        return True
    
    def detect_revenue_leakage(self) -> float:
        """Detect potential revenue leakage"""
        leakage = 0.0
        
        # Unsubmitted claims
        pending_claims = [c for c in self.claims.values() if c.status == ClaimStatus.PENDING]
        leakage += sum(c.amount for c in pending_claims) * 0.1
        
        # Denied claims not appealed
        denied_claims = [c for c in self.claims.values() 
                        if c.status == ClaimStatus.DENIED and c.appeal_date is None]
        leakage += sum(c.amount for c in denied_claims) * 0.3
        
        # Underpayments
        paid_claims = [c for c in self.claims.values() if c.status == ClaimStatus.PAID]
        for claim in paid_claims:
            if claim.paid_amount < claim.amount * 0.95:
                leakage += (claim.amount - claim.paid_amount) * 0.5
        
        return leakage
    
    def update(self, time_delta: float):
        """Update simulator state"""
        self.time += time_delta
        
        # Auto-process some claims
        for claim in self.claims.values():
            if claim.status == ClaimStatus.SUBMITTED:
                # Simulate processing
                if claim.submission_date and (self.time - claim.submission_date) > 7:
                    if claim.status == ClaimStatus.SUBMITTED:
                        # Already processed in submit_claim, but check for payment
                        if claim.status == ClaimStatus.APPROVED and not claim.payment_date:
                            # Process payment after approval delay
                            if (self.time - claim.submission_date) > 14:
                                self.process_payment(claim.claim_id)
    
    def get_state(self) -> FinancialState:
        """Get current financial state"""
        claims_pending = sum(1 for c in self.claims.values() 
                           if c.status == ClaimStatus.PENDING)
        claims_approved = sum(1 for c in self.claims.values() 
                            if c.status == ClaimStatus.APPROVED)
        claims_denied = sum(1 for c in self.claims.values() 
                          if c.status == ClaimStatus.DENIED)
        
        total_claims = len(self.claims)
        denial_rate = claims_denied / total_claims if total_claims > 0 else 0.0
        
        # Calculate average days to payment
        if self.payment_history:
            avg_days = np.mean([p["days_to_payment"] for p in self.payment_history])
        else:
            avg_days = 0.0
        
        # Collection rate
        total_claim_value = sum(c.amount for c in self.claims.values())
        collection_rate = self.total_revenue / total_claim_value if total_claim_value > 0 else 0.0
        
        revenue_leakage = self.detect_revenue_leakage()
        
        return FinancialState(
            total_revenue=self.total_revenue,
            accounts_receivable=self.accounts_receivable,
            claims_pending=claims_pending,
            claims_approved=claims_approved,
            claims_denied=claims_denied,
            denial_rate=denial_rate,
            average_days_to_payment=avg_days,
            collection_rate=collection_rate,
            revenue_leakage=revenue_leakage,
            time=self.time
        )
    
    def reset(self):
        """Reset simulator to initial state"""
        self.claims = {}
        self.total_revenue = 0.0
        self.accounts_receivable = 0.0
        self.payment_history = []
        self.time = 0.0
    
    def close(self):
        """Clean up resources"""
        pass

