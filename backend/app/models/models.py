import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, Enum, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class Platform(str, enum.Enum):
    facebook = "facebook"
    instagram = "instagram"

class ContactType(str, enum.Enum):
    phone = "phone"
    telegram = "telegram"
    other = "other"

class ScamType(str, enum.Enum):
    ghost_seller = "ghost_seller"
    fake_product = "fake_product"
    advance_payment = "advance_payment"
    wrong_item = "wrong_item"
    no_response = "no_response"
    other = "other"

class SellerProfile(Base):
    __tablename__ = "seller_profiles"
    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_url       = Column(Text, unique=True, nullable=False)
    platform          = Column(Enum(Platform), nullable=False)
    display_name      = Column(Text, nullable=True)
    profile_photo_url = Column(Text, nullable=True)
    account_age_days  = Column(Integer, nullable=True)
    post_count        = Column(Integer, nullable=True)
    fb_fetched_at     = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at        = Column(TIMESTAMP(timezone=True), server_default=func.now())

class SellerContact(Base):
    __tablename__ = "seller_contacts"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id     = Column(UUID(as_uuid=True), ForeignKey("seller_profiles.id"), nullable=False)
    contact_type  = Column(Enum(ContactType), nullable=False)
    contact_value = Column(Text, nullable=False)

class Report(Base):
    __tablename__ = "reports"
    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id          = Column(UUID(as_uuid=True), ForeignKey("seller_profiles.id"), nullable=False)
    reporter_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    scam_type          = Column(Enum(ScamType), nullable=False)
    description        = Column(Text, nullable=True)
    screenshot_url     = Column(Text, nullable=False)
    credibility_score  = Column(Float, nullable=True)
    credibility_reason = Column(Text, nullable=True)
    created_at         = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Review(Base):
    __tablename__ = "reviews"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id       = Column(UUID(as_uuid=True), ForeignKey("seller_profiles.id"), nullable=False)
    reviewer_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    stars           = Column(Integer, nullable=False)
    product_matched = Column(Boolean, nullable=False)
    responded_fast  = Column(Boolean, nullable=False)
    item_received   = Column(Boolean, nullable=False)
    would_buy_again = Column(Boolean, nullable=False)
    comment         = Column(Text, nullable=True)
    created_at      = Column(TIMESTAMP(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())