from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="admin")
    name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Craftsman(Base):
    __tablename__ = "craftsmen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    language: Mapped[str] = mapped_column(String(32), default="uk")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    kvk: Mapped[str] = mapped_column(String(16), default="")
    btw: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    instagram: Mapped[str] = mapped_column(String(255), default="")
    facebook: Mapped[str] = mapped_column(String(255), default="")
    tiktok: Mapped[str] = mapped_column(String(255), default="")
    profession: Mapped[str] = mapped_column(String(128), default="")
    extra_work: Mapped[str] = mapped_column(Text, default="")
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hourly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    city: Mapped[str] = mapped_column(String(128), default="")
    radius_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    availability: Mapped[str] = mapped_column(String(64), default="")
    nationwide: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, default="")
    portfolio_url: Mapped[str] = mapped_column(String(512), default="")
    admin_comment: Mapped[str] = mapped_column(Text, default="")
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    kvk: Mapped[str] = mapped_column(String(16), default="")
    btw: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    contact_name: Mapped[str] = mapped_column(String(255), default="")
    contact_role: Mapped[str] = mapped_column(String(128), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    region: Mapped[str] = mapped_column(String(128), default="")
    desired_profession: Mapped[str] = mapped_column(String(128), default="")
    expected_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sna: Mapped[str] = mapped_column(String(32), default="")
    admin_comment: Mapped[str] = mapped_column(Text, default="")
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    requests: Mapped[list["Request"]] = relationship(back_populates="company")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(32))
    owner_id: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(64))
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128), default="")
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    craftsman_id: Mapped[int | None] = mapped_column(ForeignKey("craftsmen.id"), nullable=True)
    project: Mapped[str] = mapped_column(String(255), default="")
    site_address: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration: Mapped[str] = mapped_column(String(128), default="")
    schedule: Mapped[str] = mapped_column(String(255), default="")
    workers_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_description: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(64), default="submitted")
    admin_comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company: Mapped[Company | None] = relationship(back_populates="requests")
    craftsman: Mapped[Craftsman | None] = relationship()
    messages: Mapped[list["Message"]] = relationship(back_populates="request", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"))
    sender_role: Mapped[str] = mapped_column(String(32))
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[Request] = relationship(back_populates="messages")


class SiteText(Base):
    __tablename__ = "site_texts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site: Mapped[str] = mapped_column(String(32))
    page: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(128))
    locale: Mapped[str] = mapped_column(String(8), default="uk")
    label: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
