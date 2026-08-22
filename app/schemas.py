from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    db: Literal["mongo", "memory"]
    tz: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class MeResponse(BaseModel):
    email: str
    role: str


class UtmFields(BaseModel):
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None


class LeadIncoming(UtmFields):
    phone: str
    email: EmailStr | None = None
    name: str | None = None
    grade: Literal["9", "10", "11"] | None = None
    subject_interest: str | None = None
    source: str = "landing"
    honeypot: str | None = None
    form_started_at: datetime | None = None
    telegram_id: str | None = None


class LeadResponse(BaseModel):
    id: str
    status: Literal["new", "quarantine"]
    quarantine_score: int
    phone: str
    telegram_queued: bool = False


class DiagnosticAttemptCreate(UtmFields):
    subject: Literal["ukr", "math", "history", "eng", "bio", "geo"]
    answers: dict[str, Any] = Field(default_factory=dict)
    contact_phone: str | None = None
    contact_email: EmailStr | None = None
    contact_name: str | None = None
    grade: Literal["9", "10", "11"] | None = None
    honeypot: str | None = None
    form_started_at: datetime | None = None


class DiagnosticAttemptResponse(BaseModel):
    id: str
    subject: str
    score: int
    percentile: int
    recommended_track: str
    offer_segment: str
    telegram_queued: bool = False


class StudentRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=2, max_length=120)
    phone: str
    grade: Literal["9", "10", "11"] = "11"
    subject_interest: str | None = "math"
    parent_name: str | None = None
    parent_phone: str | None = None
    telegram_id: str | None = None


class StudentLoginRequest(BaseModel):
    email: EmailStr
    password: str


class StudentTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student_id: str
    name: str


class StudentSubscriptionItem(BaseModel):
    id: str
    subject: str
    subject_label: str
    plan: str
    price_month: int
    status: Literal["trialing", "active", "past_due", "blocked", "cancelled"]
    next_payment_at: datetime | None = None
    current_period_end: datetime | None = None
    days_until_payment: int | None = None
    is_overdue: bool = False


class StudentMeResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: str | None = None
    grade: str | None = None
    subscriptions: list[StudentSubscriptionItem] = Field(default_factory=list)


class DemoAccessCreate(BaseModel):
    student_id: str | None = None
    phone: str | None = None
    course_ids: list[str] = Field(default_factory=list)
    days: int = Field(default=5, ge=3, le=14)


class DemoAccessResponse(BaseModel):
    id: str
    starts_at: datetime
    ends_at: datetime
    status: str


class SubscriptionCreate(BaseModel):
    student_id: str
    parent_id: str
    subject: str
    plan: Literal["standard", "premium"] = "standard"
    price_month: int
    cohort_id: str | None = None


class SubscriptionResponse(BaseModel):
    id: str
    status: Literal["trialing", "active", "past_due", "blocked", "cancelled"]
    subject: str
    plan: str
    price_month: int
    next_payment_at: datetime | None = None
    days_until_payment: int | None = None


class PaymentWebhook(BaseModel):
    subscription_id: str
    event: Literal["paid", "failed", "refunded"]
    amount: int | None = None
    provider: str = "stub"


class CohortEnrollRequest(BaseModel):
    student_id: str
    subscription_id: str


class CohortEnrollResponse(BaseModel):
    cohort_id: str
    enrolled: bool
    capacity_left: int


class CuratorAssignRequest(BaseModel):
    student_id: str
    subscription_id: str
    prefer_premium: bool = False


class CuratorAssignResponse(BaseModel):
    curator_id: str
    curator_name: str
    load: int


class SlaItem(BaseModel):
    homework_id: str
    student_id: str
    due_at: datetime
    breach: bool


NmtSubject = Literal["ukr", "math", "history", "eng", "bio", "geo"]
ConsultStatus = Literal["scheduled", "completed", "cancelled", "no_show"]


class TeacherResponse(BaseModel):
    id: str
    name: str
    subject: str
    subject_label: str
    role: str = "teacher"
    email: str | None = None
    zoom_url: str | None = None


class ConsultationCreate(BaseModel):
    teacher_id: str
    starts_at: datetime
    duration_min: int = Field(default=45, ge=15, le=180)
    subject: NmtSubject | None = None
    student_name: str = Field(min_length=2, max_length=120)
    student_phone: str | None = None
    student_id: str | None = None
    lead_id: str | None = None
    notes: str | None = None
    meeting_url: str | None = None


class ConsultationUpdate(BaseModel):
    teacher_id: str | None = None
    starts_at: datetime | None = None
    duration_min: int | None = Field(default=None, ge=15, le=180)
    subject: NmtSubject | None = None
    student_name: str | None = Field(default=None, min_length=2, max_length=120)
    student_phone: str | None = None
    student_id: str | None = None
    lead_id: str | None = None
    notes: str | None = None
    meeting_url: str | None = None
    status: ConsultStatus | None = None


class ConsultationResponse(BaseModel):
    id: str
    teacher_id: str
    teacher_name: str
    starts_at: datetime
    ends_at: datetime
    duration_min: int
    subject: str
    subject_label: str
    student_name: str
    student_phone: str | None = None
    student_id: str | None = None
    lead_id: str | None = None
    notes: str | None = None
    meeting_url: str | None = None
    status: ConsultStatus
    created_at: datetime | None = None


class ConsultStudentOption(BaseModel):
    id: str
    name: str
    phone: str | None = None
    grade: str | None = None


class ConsultLeadOption(BaseModel):
    id: str
    name: str | None = None
    phone: str | None = None
    subject_interest: str | None = None


class ConsultationMetaResponse(BaseModel):
    teachers: list[TeacherResponse]
    students: list[ConsultStudentOption]
    leads: list[ConsultLeadOption]
