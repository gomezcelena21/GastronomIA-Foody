"""
Gastro IA Backend - Pydantic Schemas
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


class SourceResponse(BaseModel):
    source_id: int
    name: str
    url: Optional[str]
    source_type: str
    license: Optional[str]
    reliability: str
    last_updated: Optional[date]
    
    class Config:
        from_attributes = True


class RestaurantResponse(BaseModel):
    restaurant_id: int
    name: str
    province: str
    city: str
    neighborhood: Optional[str]
    region: Optional[str] = None              # CABA, GBA, Interior o Sin confirmar
    district: Optional[str] = None            # partido de GBA
    zone_macro: Optional[str] = None          # CABA, GBA Norte/Oeste/Sur o la provincia
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    cuisine_type: Optional[List[str]]
    category: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    opening_hours: Optional[str]
    price_range: Optional[int]
    rating: Optional[float]
    review_count: Optional[int]
    source_type: Optional[str]
    confidence_level: str
    data_date: Optional[date]
    
    # Features
    has_gluten_free_options: Optional[bool] = None
    has_vegetarian_options: Optional[bool] = None
    has_vegan_options: Optional[bool] = None
    has_lactose_free_options: Optional[bool] = None
    celiac_certified: Optional[bool] = None
    
    # Source info
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_reliability: Optional[str] = None
    
    class Config:
        from_attributes = True


class SearchParams(BaseModel):
    province: Optional[str] = None
    city: Optional[str] = None
    cuisine_type: Optional[List[str]] = None
    price_range_max: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = 5.0
    requires_gluten_free: Optional[bool] = None
    requires_vegetarian: Optional[bool] = None
    requires_vegan: Optional[bool] = None
    order_by: Optional[str] = "relevance"
    limit: int = 20
    offset: int = 0


class RecommendationScore(BaseModel):
    restaurant_id: int
    name: str
    final_score: float
    breakdown: dict
    compatible_dishes: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


class SearchResponse(BaseModel):
    results: List[RestaurantResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
