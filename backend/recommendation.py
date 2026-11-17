"""
Gastro IA - Recommendation Engine
Multi-criteria scoring system for restaurant recommendations.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class RecommendationResult:
    restaurant_id: int
    name: str
    final_score: float
    breakdown: Dict[str, float]
    compatible_features: List[str]
    warnings: List[str]


class RecommendationEngine:
    """Multi-criteria restaurant recommendation engine."""
    
    # Default weights
    DEFAULT_WEIGHTS = {
        "dietary_match": 0.30,
        "cuisine_match": 0.20,
        "proximity": 0.25,
        "rating": 0.15,
        "data_quality": 0.10,
    }
    
    # Medical restriction weights (higher dietary importance)
    MEDICAL_WEIGHTS = {
        "dietary_match": 0.40,
        "cuisine_match": 0.15,
        "proximity": 0.20,
        "rating": 0.15,
        "data_quality": 0.10,
    }
    
    # Confidence level multipliers
    CONFIDENCE_MULTIPLIERS = {
        "official": 1.0,
        "public_source": 0.95,
        "community": 0.90,
        "inferred": 0.80,
        "no_verified": 0.70,
    }
    
    def __init__(self, has_medical_restrictions: bool = False):
        self.weights = self.MEDICAL_WEIGHTS if has_medical_restrictions else self.DEFAULT_WEIGHTS
    
    def _calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        R = 6371  # Earth radius in km
        
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _score_dietary_match(self, restaurant: Dict, requirements: Dict) -> float:
        """Score how well restaurant meets dietary requirements."""
        score = 0.0
        checks = 0
        
        features = restaurant.get("features", {})
        
        if requirements.get("gluten_free"):
            checks += 1
            if features.get("has_gluten_free_options") == True:
                score += 1.0
            elif features.get("has_gluten_free_options") == False:
                score += 0.0
            else:
                score += 0.3  # Unknown, give partial credit
        
        if requirements.get("vegetarian"):
            checks += 1
            if features.get("has_vegetarian_options") == True:
                score += 1.0
            elif features.get("has_vegan_options") == True:
                score += 1.0
            else:
                score += 0.3
        
        if requirements.get("vegan"):
            checks += 1
            if features.get("has_vegan_options") == True:
                score += 1.0
            else:
                score += 0.2
        
        if requirements.get("lactose_free"):
            checks += 1
            if features.get("has_lactose_free_options") == True:
                score += 1.0
            else:
                score += 0.3
        
        if checks == 0:
            return 0.5  # No requirements = neutral score
        
        return score / checks
    
    def _score_cuisine_match(self, restaurant: Dict, preferred_cuisines: List[str]) -> float:
        """Score cuisine type match."""
        if not preferred_cuisines:
            return 0.5  # No preference = neutral
        
        restaurant_cuisines = restaurant.get("cuisine_type", []) or []
        if isinstance(restaurant_cuisines, str):
            restaurant_cuisines = [restaurant_cuisines]
        
        # Normalize
        restaurant_cuisines = [c.lower() for c in restaurant_cuisines]
        preferred_cuisines = [c.lower() for c in preferred_cuisines]
        
        matches = len(set(restaurant_cuisines) & set(preferred_cuisines))
        
        if matches > 0:
            return 1.0
        elif any(c in " ".join(restaurant_cuisines) for c in preferred_cuisines):
            return 0.7  # Partial match
        else:
            return 0.2  # No match
    
    def _score_proximity(self, restaurant: Dict, user_lat: float, user_lon: float, max_distance_km: float = 10.0) -> float:
        """Score based on distance (closer = higher score)."""
        rest_lat = restaurant.get("latitude")
        rest_lon = restaurant.get("longitude")
        
        if rest_lat is None or rest_lon is None:
            return 0.3  # No coordinates = low score
        
        distance = self._calculate_distance_km(user_lat, user_lon, rest_lat, rest_lon)
        
        if distance > max_distance_km:
            return 0.0
        
        # Linear decay
        return max(0, 1 - (distance / max_distance_km))
    
    def _score_rating(self, restaurant: Dict) -> float:
        """Score based on restaurant rating."""
        rating = restaurant.get("rating")
        
        if rating is None:
            return 0.5  # No rating = neutral
        
        # Normalize 0-5 to 0-1
        return min(rating / 5.0, 1.0)
    
    def _score_data_quality(self, restaurant: Dict) -> float:
        """Score based on data completeness and confidence."""
        confidence = restaurant.get("confidence_level", "no_verified")
        multiplier = self.CONFIDENCE_MULTIPLIERS.get(confidence, 0.7)
        
        # Bonus for having more data
        completeness = 0
        if restaurant.get("phone"): completeness += 0.2
        if restaurant.get("address"): completeness += 0.2
        if restaurant.get("opening_hours"): completeness += 0.2
        if restaurant.get("cuisine_type"): completeness += 0.2
        if restaurant.get("website"): completeness += 0.2
        
        return multiplier * (0.5 + completeness * 0.5)
    
    def _identify_compatible_features(self, restaurant: Dict, requirements: Dict) -> List[str]:
        """Identify which features are compatible with requirements."""
        features = restaurant.get("features", {})
        compatible = []
        
        if requirements.get("gluten_free") and features.get("has_gluten_free_options"):
            compatible.append("Opciones sin TACC disponibles")
        
        if requirements.get("vegetarian") and features.get("has_vegetarian_options"):
            compatible.append("Opciones vegetarianas")
        
        if requirements.get("vegan") and features.get("has_vegan_options"):
            compatible.append("Opciones veganas")
        
        if requirements.get("lactose_free") and features.get("has_lactose_free_options"):
            compatible.append("Opciones sin lactosa")
        
        if features.get("celiac_certified"):
            compatible.append("Certificado celíaco")
        
        return compatible
    
    def _generate_warnings(self, restaurant: Dict, requirements: Dict) -> List[str]:
        """Generate relevant warnings."""
        warnings = []
        confidence = restaurant.get("confidence_level", "no_verified")
        
        if requirements.get("gluten_free") and not restaurant.get("features", {}).get("has_gluten_free_options"):
            warnings.append("Sin información confirmada sobre opciones sin TACC")
        
        if confidence in ("no_verified", "inferred"):
            warnings.append("Información no verificada oficialmente")
        
        if not restaurant.get("phone"):
            warnings.append("Sin teléfono de contacto")
        
        return warnings
    
    def rank_restaurants(
        self,
        restaurants: List[Dict],
        requirements: Dict,
        preferred_cuisines: List[str] = None,
        user_lat: float = None,
        user_lon: float = None,
        max_distance_km: float = 10.0,
        limit: int = 10
    ) -> List[RecommendationResult]:
        """Rank restaurants based on multiple criteria."""
        
        results = []
        
        for restaurant in restaurants:
            # Calculate individual scores
            dietary_score = self._score_dietary_match(restaurant, requirements)
            cuisine_score = self._score_cuisine_match(restaurant, preferred_cuisines or [])
            
            if user_lat and user_lon:
                proximity_score = self._score_proximity(restaurant, user_lat, user_lon, max_distance_km)
            else:
                proximity_score = 0.5
            
            rating_score = self._score_rating(restaurant)
            quality_score = self._score_data_quality(restaurant)
            
            # Weighted sum
            final_score = (
                self.weights["dietary_match"] * dietary_score +
                self.weights["cuisine_match"] * cuisine_score +
                self.weights["proximity"] * proximity_score +
                self.weights["rating"] * rating_score +
                self.weights["data_quality"] * quality_score
            )
            
            # Build breakdown
            breakdown = {
                "dietary_match": round(dietary_score, 2),
                "cuisine_match": round(cuisine_score, 2),
                "proximity": round(proximity_score, 2),
                "rating": round(rating_score, 2),
                "data_quality": round(quality_score, 2),
            }
            
            compatible = self._identify_compatible_features(restaurant, requirements)
            warnings = self._generate_warnings(restaurant, requirements)
            
            results.append(RecommendationResult(
                restaurant_id=restaurant["restaurant_id"],
                name=restaurant["name"],
                final_score=round(final_score, 3),
                breakdown=breakdown,
                compatible_features=compatible,
                warnings=warnings,
            ))
        
        # Sort by score
        results.sort(key=lambda x: x.final_score, reverse=True)
        
        return results[:limit]
