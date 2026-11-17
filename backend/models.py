"""
Gastro IA Backend - SQLAlchemy Models
"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, Date, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from database import Base


class Source(Base):
    __tablename__ = "sources"
    
    source_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500))
    source_type = Column(String(50), nullable=False)
    license = Column(String(100))
    update_frequency = Column(String(50))
    last_updated = Column(Date)
    reliability = Column(String(30), nullable=False)
    notes = Column(Text)
    fetched_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Restaurant(Base):
    __tablename__ = "restaurants"
    
    restaurant_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False)
    province = Column(String(100), nullable=False)
    city = Column(String(200), nullable=False)
    neighborhood = Column(String(200))
    region = Column(String(20))        # CABA, GBA o Sin confirmar
    district = Column(String(100))     # partido de GBA (ej.: Lomas de Zamora)
    zone_macro = Column(String(50))    # CABA, GBA Norte, GBA Oeste, GBA Sur
    address = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    geom = Column(Geometry("POINT", 4326))
    cuisine_type = Column(ARRAY(Text))
    category = Column(String(50))
    phone = Column(String(50))
    email = Column(String(300))
    website = Column(String(300))
    social_media = Column(JSONB)
    opening_hours = Column(Text)
    price_range = Column(Integer)
    rating = Column(Float)
    review_count = Column(Integer)
    source_id = Column(Integer, ForeignKey("sources.source_id"))
    source_type = Column(String(50))
    confidence_level = Column(String(30), nullable=False, default="no_verified")
    data_date = Column(Date)
    fetched_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class RestaurantFeature(Base):
    __tablename__ = "restaurant_features"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.restaurant_id"))
    has_gluten_free_options = Column(Boolean)
    has_vegetarian_options = Column(Boolean)
    has_vegan_options = Column(Boolean)
    has_lactose_free_options = Column(Boolean)
    celiac_certified = Column(Boolean, default=False)
    source_id = Column(Integer, ForeignKey("sources.source_id"))
    confidence_level = Column(String(30), default="no_verified")
    created_at = Column(DateTime, server_default=func.now())


class Menu(Base):
    __tablename__ = "menus"
    
    menu_id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.restaurant_id"))
    dish_name = Column(String(300), nullable=False)
    category = Column(String(100))
    description = Column(Text)
    price = Column(Float)
    currency = Column(String(3), default="ARS")
    ingredients = Column(ARRAY(Text))
    source_id = Column(Integer, ForeignKey("sources.source_id"))
    confidence_level = Column(String(30), default="no_verified")
    data_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
