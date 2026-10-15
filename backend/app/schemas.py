from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class StatusUpdate(BaseModel):
    status: Literal["pending", "clarification", "approved", "rejected"]
    comment: str = ""


class RequestStatusUpdate(BaseModel):
    status: Literal["draft", "submitted", "in_progress", "candidate", "confirmed", "done", "cancelled"]
    craftsman_id: int | None = None
    comment: str = ""


class MessageIn(BaseModel):
    request_id: int
    body: str = Field(min_length=1)


class TextItemIn(BaseModel):
    id: int
    value: str


class TextsPut(BaseModel):
    items: list[TextItemIn]


class SiteSettingsUpdate(BaseModel):
    is_open: bool


class CmsPageCreate(BaseModel):
    site: Literal["uhrbv", "ukrwerkspot"]
    locale: str = "nl"
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9/-]*$")
    title: str = Field(min_length=1, max_length=255)
    seo_title: str = ""
    seo_description: str = ""


class CmsPageSave(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    seo_title: str = ""
    seo_description: str = ""
    project_data: dict = Field(default_factory=dict)
    html: str = ""
    css: str = ""
    note: str = ""
    expected_version: int | None = None


class CmsMenuSave(BaseModel):
    items: list[dict]


class CmsPostSave(BaseModel):
    site: Literal["uhrbv", "ukrwerkspot"]
    locale: str = "nl"
    kind: Literal["news", "blog"]
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9/-]*$")
    title: str = Field(min_length=1, max_length=255)
    excerpt: str = ""
    cover_url: str = ""
    body: str = ""


class CmsCategorySave(BaseModel):
    site: Literal["uhrbv", "ukrwerkspot"]
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=255)
    profession: str = ""
    description: str = ""
    image_url: str = ""
    sort_order: int = 0
    is_visible: bool = True


class CraftsmanApplication(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=64)
    email: EmailStr
    works: str = ""
    experience_ua: str = Field(default="", max_length=255)
    experience_nl: str = Field(default="", max_length=255)
    language: str = "Українська"
    company_name: str = ""
    kvk: str = ""
    btw: str = ""
    address: str = ""
    website: str = ""
    instagram: str = ""
    facebook: str = ""
    tiktok: str = ""
    profession: str
    extra_work: str = ""
    experience_years: int | None = None
    hourly_rate: float | None = None
    city: str = ""
    radius_km: int | None = None
    availability: str = ""
    nationwide: bool = False
    description: str = ""
    portfolio_url: str = ""


class CompanyApplication(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    kvk: str = ""
    btw: str = ""
    address: str = ""
    website: str = ""
    description: str = ""
    contact_name: str
    contact_role: str = ""
    email: EmailStr
    phone: str
    region: str = ""
    desired_profession: str = ""
    expected_count: int | None = None
    sna: str = ""


class CompanySignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class EmailIn(BaseModel):
    email: EmailStr


class PasswordResetIn(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)


class CompanyProfileUpdate(BaseModel):
    contact_name: str = Field(min_length=1, max_length=255)
    contact_role: str = Field(default="", max_length=128)
    phone: str = Field(min_length=1, max_length=64)
    website: str = Field(default="", max_length=255)
    address: str = ""
    description: str = ""


class CompanyRequestIn(BaseModel):
    craftsman_id: int | None = None
    project: str = Field(min_length=1, max_length=255)
    site_address: str = ""
    start_date: date | None = None
    duration: str = Field(default="", max_length=128)
    schedule: str = Field(default="", max_length=255)
    workers_count: int | None = Field(default=None, ge=1, le=100)
    work_description: str = Field(default="", max_length=4000)
    requirements: str = Field(default="", max_length=4000)


class CompanyMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class SelectionContactIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    channel: str = "chat"


class CompanyRegistration(BaseModel):
    company_type: Literal["agency", "contractor"]
    company_name: str = Field(min_length=1, max_length=255)
    kvk: str = Field(pattern=r"^\d{8}$")
    address: str = ""
    contact_name: str = Field(min_length=1, max_length=255)
    contact_role: str = Field(default="", max_length=128)
    phone: str = Field(min_length=1, max_length=64)
    website: str = Field(default="", max_length=255)
    description: str = ""


class RequestApplication(BaseModel):
    company_id: int
    craftsman_id: int | None = None
    project: str
    site_address: str = ""
    start_date: date | None = None
    duration: str = ""
    schedule: str = ""
    workers_count: int | None = None
    work_description: str = ""
    requirements: str = ""


def dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def d(value: date | None) -> str | None:
    return value.isoformat() if value else None
