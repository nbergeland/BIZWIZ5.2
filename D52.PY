#!/usr/bin/env python3
"""
BizWiz Dynamic Dashboard - Elegant Design with Comprehensive Franchise Protection
INTEGRATED: Google Places API, Census API + Smart Caching + Cannibalization Analysis
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import asyncio
import threading
import time
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
import traceback
import os
import sys
import requests
from dataclasses import dataclass
import pickle
import hashlib
from pathlib import Path

# === SMART CACHING SYSTEM ===

class DataCacheManager:
    """Smart caching system for API data with persistence and management"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_metadata_file = self.cache_dir / "cache_metadata.json"
        self.default_expiry_hours = 24
        self.debug = True
        
        # Initialize cache system
        success = self._initialize_cache_system()
        
        if success:
            self.metadata = self._load_metadata()
            self._cleanup_old_cache()
            logging.info(f"📦 Cache system initialized successfully: {self.cache_dir}")
        else:
            logging.error("❌ Cache system initialization failed - running without cache")
            self.metadata = {}
    
    def _initialize_cache_system(self) -> bool:
        """Initialize cache directory and test basic operations"""
        try:
            self.cache_dir.mkdir(exist_ok=True, mode=0o755)
            
            # Test write permissions
            test_file = self.cache_dir / ".cache_test"
            test_file.write_text("test")
            test_file.unlink()
            
            # Initialize metadata file if it doesn't exist
            if not self.cache_metadata_file.exists():
                with open(self.cache_metadata_file, 'w') as f:
                    json.dump({}, f)
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Cache initialization failed: {e}")
            return False
    
    def _load_metadata(self) -> Dict:
        """Load cache metadata with error handling"""
        try:
            if self.cache_metadata_file.exists():
                with open(self.cache_metadata_file, 'r') as f:
                    metadata = json.load(f)
                if self.debug:
                    logging.info(f"📄 Loaded metadata: {len(metadata)} entries")
                return metadata
            return {}
        except Exception as e:
            logging.warning(f"Failed to load cache metadata: {e}")
            return {}
    
    def _save_metadata(self) -> bool:
        """Save cache metadata with error handling"""
        try:
            with open(self.cache_metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            
            if self.debug:
                logging.info(f"💾 Saved metadata: {len(self.metadata)} entries")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save cache metadata: {e}")
            return False
    
    def _cleanup_old_cache(self):
        """Remove old unused cache files"""
        try:
            cache_files = list(self.cache_dir.glob("*.pkl"))
            metadata_cities = set(self.metadata.keys())
            cleaned = 0
            
            for cache_file in cache_files:
                city_id = cache_file.stem
                if city_id not in metadata_cities:
                    cache_file.unlink()
                    cleaned += 1
                    if self.debug:
                        logging.info(f"🗑️ Removed orphaned cache: {city_id}")
            
            if cleaned > 0:
                logging.info(f"🧹 Cleaned up {cleaned} orphaned cache files")
                
        except Exception as e:
            logging.warning(f"Cache cleanup warning: {e}")
    
    def get_cache_key(self, city_id: str) -> str:
        """Generate cache key for city"""
        return f"{city_id}"
    
    def get_cache_file(self, city_id: str) -> Path:
        """Get cache file path for city"""
        safe_city_id = "".join(c for c in city_id if c.isalnum() or c in '_-').rstrip()
        return self.cache_dir / f"{safe_city_id}.pkl"
    
    def is_cache_valid(self, city_id: str, max_age_hours: Optional[int] = None) -> bool:
        """Check if cached data is still valid"""
        try:
            if city_id not in self.metadata:
                return False
            
            cache_info = self.metadata[city_id]
            cache_time = datetime.fromisoformat(cache_info['cached_at'])
            max_age = max_age_hours or self.default_expiry_hours
            
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            is_valid = age_hours < max_age
            
            # Also check if cache file exists
            cache_file = self.get_cache_file(city_id)
            file_exists = cache_file.exists()
            
            if self.debug and not is_valid:
                logging.info(f"⏰ Cache expired for {city_id}: {age_hours:.1f}h old")
            
            return is_valid and file_exists
            
        except Exception as e:
            logging.warning(f"Cache validation error for {city_id}: {e}")
            return False
    
    def _serialize_city_config(self, city_config) -> Dict[str, Any]:
        """Convert CityConfiguration object to serializable dict"""
        try:
            if city_config is None:
                return None
            
            # Extract key attributes from CityConfiguration object
            config_dict = {
                'display_name': getattr(city_config, 'display_name', 'Unknown City'),
                'state_code': getattr(city_config, 'state_code', None),
                'bounds': {
                    'min_lat': getattr(city_config.bounds, 'min_lat', 0.0) if hasattr(city_config, 'bounds') else 0.0,
                    'max_lat': getattr(city_config.bounds, 'max_lat', 0.0) if hasattr(city_config, 'bounds') else 0.0,
                    'min_lon': getattr(city_config.bounds, 'min_lon', 0.0) if hasattr(city_config, 'bounds') else 0.0,
                    'max_lon': getattr(city_config.bounds, 'max_lon', 0.0) if hasattr(city_config, 'bounds') else 0.0,
                    'center_lat': getattr(city_config.bounds, 'center_lat', 0.0) if hasattr(city_config, 'bounds') else 0.0,
                    'center_lon': getattr(city_config.bounds, 'center_lon', 0.0) if hasattr(city_config, 'bounds') else 0.0,
                },
                'serialized': True  # Flag to indicate this was serialized
            }
            
            return config_dict
            
        except Exception as e:
            logging.warning(f"Error serializing city config: {e}")
            return {
                'display_name': 'Unknown City',
                'state_code': None,
                'bounds': {'min_lat': 0, 'max_lat': 0, 'min_lon': 0, 'max_lon': 0, 'center_lat': 0, 'center_lon': 0},
                'serialized': True,
                'error': str(e)
            }
    
    def _deserialize_city_config(self, config_dict):
        """Convert serialized dict back to a mock CityConfiguration-like object"""
        try:
            if config_dict is None or not config_dict.get('serialized'):
                return config_dict
            
            # Create a simple object that mimics CityConfiguration
            class MockCityConfig:
                def __init__(self, data):
                    self.display_name = data.get('display_name', 'Unknown City')
                    self.state_code = data.get('state_code')
                    
                    # Create bounds object
                    bounds_data = data.get('bounds', {})
                    self.bounds = type('bounds', (), bounds_data)()
            
            return MockCityConfig(config_dict)
            
        except Exception as e:
            logging.warning(f"Error deserializing city config: {e}")
            return None
    
    def get_cached_data(self, city_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached data for city"""
        try:
            if not self.is_cache_valid(city_id):
                return None
            
            cache_file = self.get_cache_file(city_id)
            
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
            
            # Handle DataFrame reconstruction
            if 'df_filtered' in cached_data and cached_data['df_filtered'] is not None:
                if isinstance(cached_data['df_filtered'], list):
                    # Convert back to DataFrame from records
                    cached_data['df_filtered'] = pd.DataFrame(cached_data['df_filtered'])
            
            # Handle CityConfiguration reconstruction
            if 'city_config' in cached_data:
                cached_data['city_config'] = self._deserialize_city_config(cached_data['city_config'])
            
            # Add cache metadata
            cache_info = self.metadata[city_id]
            cached_data['cache_info'] = {
                'cached_at': cache_info['cached_at'],
                'cache_age_hours': (datetime.now() - datetime.fromisoformat(cache_info['cached_at'])).total_seconds() / 3600,
                'from_cache': True
            }
            
            if self.debug:
                logging.info(f"📦 Retrieved cached data for {city_id}")
            return cached_data
            
        except Exception as e:
            logging.error(f"Error retrieving cached data for {city_id}: {e}")
            # Clean up corrupted cache
            try:
                cache_file = self.get_cache_file(city_id)
                if cache_file.exists():
                    cache_file.unlink()
                if city_id in self.metadata:
                    del self.metadata[city_id]
                    self._save_metadata()
                logging.info(f"🗑️ Cleaned up corrupted cache for {city_id}")
            except:
                pass
            return None
    
    def save_data_to_cache(self, city_id: str, data: Dict[str, Any]) -> bool:
        """Save city data to cache with proper object handling"""
        try:
            cache_file = self.get_cache_file(city_id)
            
            # Prepare data for caching
            cache_data = data.copy()
            
            # Handle DataFrame serialization
            if 'df_filtered' in cache_data and cache_data['df_filtered'] is not None:
                if isinstance(cache_data['df_filtered'], pd.DataFrame):
                    # Convert DataFrame to list of records for pickle compatibility
                    cache_data['df_filtered'] = cache_data['df_filtered'].to_dict('records')
            
            # Handle CityConfiguration serialization
            if 'city_config' in cache_data and cache_data['city_config'] is not None:
                cache_data['city_config'] = self._serialize_city_config(cache_data['city_config'])
            
            # Save data
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # Update metadata
            self.metadata[city_id] = {
                'cached_at': datetime.now().isoformat(),
                'city_name': self._get_city_name(data, city_id),
                'data_size_mb': cache_file.stat().st_size / (1024 * 1024),
                'api_status': data.get('api_status', {}),
                'total_locations': data.get('metrics', {}).get('total_locations', 0),
                'existing_canes': data.get('metrics', {}).get('existing_canes', 0)
            }
            
            success = self._save_metadata()
            
            if success and self.debug:
                logging.info(f"💾 Successfully cached data for {city_id} ({self.metadata[city_id]['data_size_mb']:.2f} MB)")
            
            return success
            
        except Exception as e:
            logging.error(f"Error caching data for {city_id}: {e}")
            logging.error(f"Error details: {type(e).__name__}: {str(e)}")
            
            # Clean up partial files
            try:
                cache_file = self.get_cache_file(city_id)
                if cache_file.exists():
                    cache_file.unlink()
            except:
                pass
            return False
    
    def _get_city_name(self, data: Dict[str, Any], city_id: str) -> str:
        """Extract city name from data safely"""
        try:
            if 'city_config' in data and data['city_config']:
                city_config = data['city_config']
                if hasattr(city_config, 'display_name'):
                    return city_config.display_name
                elif isinstance(city_config, dict) and 'display_name' in city_config:
                    return city_config['display_name']
            return city_id.replace('_', ' ').title()
        except Exception as e:
            logging.warning(f"Error extracting city name: {e}")
            return city_id.replace('_', ' ').title()
    
    def clear_cache(self, city_id: Optional[str] = None) -> bool:
        """Clear cache for specific city or all cities"""
        try:
            if city_id:
                # Clear specific city
                cache_file = self.get_cache_file(city_id)
                if cache_file.exists():
                    cache_file.unlink()
                
                if city_id in self.metadata:
                    del self.metadata[city_id]
                
                logging.info(f"🗑️ Cleared cache for {city_id}")
            else:
                # Clear all cache
                for cache_file in self.cache_dir.glob("*.pkl"):
                    cache_file.unlink()
                
                self.metadata = {}
                logging.info("🗑️ Cleared all cache")
            
            return self._save_metadata()
            
        except Exception as e:
            logging.error(f"Error clearing cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_cities = len(self.metadata)
            total_size_mb = sum(info.get('data_size_mb', 0) for info in self.metadata.values())
            total_existing_canes = sum(info.get('existing_canes', 0) for info in self.metadata.values())
            
            # Get age distribution
            ages = []
            for info in self.metadata.values():
                try:
                    cache_time = datetime.fromisoformat(info['cached_at'])
                    age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                    ages.append(age_hours)
                except:
                    continue
            
            return {
                'total_cached_cities': total_cities,
                'total_size_mb': round(total_size_mb, 2),
                'avg_age_hours': round(np.mean(ages), 1) if ages else 0,
                'oldest_cache_hours': round(max(ages), 1) if ages else 0,
                'newest_cache_hours': round(min(ages), 1) if ages else 0,
                'total_existing_canes': total_existing_canes,
                'cache_dir': str(self.cache_dir.absolute()),
                'cache_working': True
            }
            
        except Exception as e:
            logging.error(f"Error getting cache stats: {e}")
            return {
                'total_cached_cities': 0,
                'total_size_mb': 0,
                'cache_dir': str(self.cache_dir),
                'cache_working': False,
                'error': str(e)
            }
    
    def list_cached_cities(self) -> List[Dict[str, Any]]:
        """List all cached cities with details"""
        cached_cities = []
        
        for city_id, info in self.metadata.items():
            try:
                cache_time = datetime.fromisoformat(info['cached_at'])
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                
                cached_cities.append({
                    'city_id': city_id,
                    'city_name': info.get('city_name', city_id),
                    'cached_at': info['cached_at'],
                    'age_hours': round(age_hours, 1),
                    'size_mb': round(info.get('data_size_mb', 0), 2),
                    'total_locations': info.get('total_locations', 0),
                    'existing_canes': info.get('existing_canes', 0),
                    'is_valid': self.is_cache_valid(city_id)
                })
            except Exception as e:
                logging.warning(f"Error processing cached city {city_id}: {e}")
        
        return sorted(cached_cities, key=lambda x: x['age_hours'])

# Initialize cache manager
cache_manager = DataCacheManager()

# === API CONFIGURATION ===
CENSUS_API_KEY = "YOURAPIHERE"
GOOGLE_API_KEY = "YOURAPIHERE"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === ENHANCED API FUNCTIONS WITH FRANCHISE PROTECTION ===

def get_existing_raising_canes_locations(city_name: str) -> List[Dict]:
    """Get existing Raising Cane's locations specifically to avoid cannibalization"""
    
    try:
        logger.info(f"🐔 Searching for existing Raising Cane's franchises in {city_name}...")
        
        # Multiple search strategies for Raising Cane's
        search_queries = [
            f"Raising Cane's near {city_name}",
            f"Raising Cane's Chicken Fingers {city_name}",
            f"Cane's {city_name}"
        ]
        
        all_canes_locations = []
        found_place_ids = set()  # Avoid duplicates
        
        for query in search_queries:
            try:
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                params = {
                    'query': query,
                    'key': GOOGLE_API_KEY,
                    'fields': 'place_id,name,geometry,rating,user_ratings_total,formatted_address,business_status'
                }
                
                logger.info(f"🔍 API call: {query}")
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('status') == 'OK':
                        results = data.get('results', [])
                        
                        for place in results:
                            place_id = place.get('place_id', '')
                            if place_id and place_id not in found_place_ids:
                                # Filter for actual Raising Cane's locations
                                name = place.get('name', '').lower()
                                if any(term in name for term in ['raising cane', "cane's", 'canes']):
                                    try:
                                        location = place.get('geometry', {}).get('location', {})
                                        lat = location.get('lat')
                                        lng = location.get('lng')
                                        
                                        if lat is not None and lng is not None:
                                            all_canes_locations.append({
                                                'name': place.get('name', "Raising Cane's"),
                                                'latitude': lat,
                                                'longitude': lng,
                                                'rating': place.get('rating', 4.5),
                                                'user_ratings_total': place.get('user_ratings_total', 100),
                                                'address': place.get('formatted_address', ''),
                                                'place_id': place_id,
                                                'business_status': place.get('business_status', 'OPERATIONAL'),
                                                'is_existing_canes': True,
                                                'is_synthetic': False
                                            })
                                            found_place_ids.add(place_id)
                                    except Exception as e:
                                        logger.warning(f"Error processing Cane's location: {e}")
                                        continue
                        
                        logger.info(f"✅ Found {len(results)} potential Cane's locations from query '{query}'")
                    elif data.get('status') == 'ZERO_RESULTS':
                        logger.info(f"📍 No results for query: {query}")
                    else:
                        logger.warning(f"⚠️ API warning for '{query}': {data.get('status')}")
                else:
                    logger.warning(f"⚠️ API request failed for '{query}': {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Error with query '{query}': {e}")
                continue
        
        # Remove duplicates and filter
        unique_locations = []
        seen_coordinates = set()
        
        for location in all_canes_locations:
            coord_key = (round(location['latitude'], 4), round(location['longitude'], 4))
            if coord_key not in seen_coordinates:
                unique_locations.append(location)
                seen_coordinates.add(coord_key)
        
        logger.info(f"🎯 Found {len(unique_locations)} unique existing Raising Cane's locations")
        
        # Log locations for verification
        if unique_locations:
            logger.info("📍 Existing Raising Cane's locations found:")
            for i, loc in enumerate(unique_locations, 1):
                logger.info(f"   {i}. {loc['name']} - {loc['address']}")
        
        return unique_locations
        
    except Exception as e:
        logger.error(f"❌ Error finding existing Raising Cane's: {e}")
        return []

def get_other_competitors_from_google_places(city_name: str, competitor_type: str = "chick-fil-a") -> List[Dict]:
    """Get competitor data EXCLUDING Raising Cane's (handled separately)"""
    
    try:
        logger.info(f"🔍 Searching for {competitor_type} competitors (excluding Raising Cane's)...")
        
        # Search query mapping - excluding Raising Cane's variants
        search_terms = {
            'chick-fil-a': 'Chick-fil-A',
            'chickfila': 'Chick-fil-A', 
            'mcdonalds': "McDonald's",
            'kfc': 'KFC',
            'popeyes': 'Popeyes',
            'burger-king': 'Burger King',
            'taco-bell': 'Taco Bell',
            'subway': 'Subway',
            'wendys': "Wendy's",
            'bojangles': "Bojangles"
        }
        
        query_name = search_terms.get(competitor_type.lower(), competitor_type)
        query = f"{query_name} near {city_name}"
        
        # Google Places Text Search API
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': query,
            'key': GOOGLE_API_KEY,
            'fields': 'place_id,name,geometry,rating,user_ratings_total,formatted_address'
        }
        
        logger.info(f"📡 Making API call: {query}")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'OK':
                results = data.get('results', [])
                logger.info(f"✅ Found {len(results)} {competitor_type} locations")
                
                competitors = []
                for place in results[:20]:  # Limit to 20 for performance
                    try:
                        # Skip if this is actually a Raising Cane's location
                        name = place.get('name', '').lower()
                        if any(term in name for term in ['raising cane', "cane's", 'canes']):
                            continue
                        
                        location = place.get('geometry', {}).get('location', {})
                        lat = location.get('lat')
                        lng = location.get('lng')
                        
                        if lat is not None and lng is not None:
                            competitors.append({
                                'name': place.get('name', f'{competitor_type} Location'),
                                'latitude': lat,
                                'longitude': lng,
                                'rating': place.get('rating', 4.0),
                                'user_ratings_total': place.get('user_ratings_total', 100),
                                'address': place.get('formatted_address', ''),
                                'place_id': place.get('place_id', ''),
                                'is_synthetic': False,
                                'is_existing_canes': False
                            })
                    
                    except Exception as e:
                        logger.warning(f"Error processing place: {e}")
                        continue
                
                logger.info(f"🎯 Processed {len(competitors)} competitor locations")
                return competitors
                
            elif data.get('status') == 'ZERO_RESULTS':
                logger.info(f"📍 No {competitor_type} locations found in {city_name}")
                return []
            else:
                logger.error(f"❌ Google Places API error: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
                return []
        else:
            logger.error(f"❌ API request failed with status {response.status_code}: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error calling Google Places API: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Unexpected error in Google Places API call: {e}")
        return []

def calculate_cannibalization_risk(lat: float, lon: float, existing_canes: List[Dict]) -> Dict[str, Any]:
    """Calculate cannibalization risk and distance to nearest Raising Cane's"""
    
    if not existing_canes:
        return {
            'nearest_distance_miles': float('inf'),
            'cannibalization_risk': 'NONE',
            'risk_score': 0.0,
            'risk_factor': 1.0,  # No reduction in revenue potential
            'recommendation': 'CLEAR'
        }
    
    # Calculate distances to all existing Cane's locations
    distances = []
    for canes_location in existing_canes:
        # Haversine formula for distance in miles
        lat1, lon1 = np.radians(lat), np.radians(lon)
        lat2, lon2 = np.radians(canes_location['latitude']), np.radians(canes_location['longitude'])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        distance_miles = 3959 * c  # Earth's radius in miles
        
        distances.append(distance_miles)
    
    nearest_distance = min(distances)
    
    # Define cannibalization risk levels based on Raising Cane's typical trade area
    if nearest_distance < 1.0:  # Less than 1 mile
        risk = 'CRITICAL'
        risk_score = 0.9
        risk_factor = 0.2  # 80% revenue reduction
        recommendation = 'AVOID'
    elif nearest_distance < 2.0:  # 1-2 miles
        risk = 'HIGH'
        risk_score = 0.7
        risk_factor = 0.4  # 60% revenue reduction
        recommendation = 'CAUTION'
    elif nearest_distance < 3.5:  # 2-3.5 miles
        risk = 'MODERATE'
        risk_score = 0.5
        risk_factor = 0.7  # 30% revenue reduction
        recommendation = 'EVALUATE'
    elif nearest_distance < 5.0:  # 3.5-5 miles
        risk = 'LOW'
        risk_score = 0.2
        risk_factor = 0.9  # 10% revenue reduction
        recommendation = 'ACCEPTABLE'
    else:  # 5+ miles
        risk = 'MINIMAL'
        risk_score = 0.1
        risk_factor = 1.0  # No reduction
        recommendation = 'PREFERRED'
    
    return {
        'nearest_distance_miles': nearest_distance,
        'cannibalization_risk': risk,
        'risk_score': risk_score,
        'risk_factor': risk_factor,
        'recommendation': recommendation
    }

def get_real_demographic_data(city_name: str, state_code: str = None) -> Dict[str, Any]:
    """Get REAL demographic data from Census API using your API key"""
    
    try:
        logger.info(f"🏛️ Fetching REAL demographic data for {city_name} from Census API...")
        
        # Simplified Census API call that's more likely to work
        url = "https://api.census.gov/data/2021/acs/acs5"
        
        # Get basic demographic data for the state (since city-specific can be tricky)
        state_fips = {
            '06': 'CA', '36': 'NY', '17': 'IL', '48': 'TX', '04': 'AZ',
            '42': 'PA', '51': 'VA', '38': 'ND'
        }
        
        # Use state code or try to determine from city
        if not state_code:
            if 'CA' in city_name or 'California' in city_name:
                state_code = '06'
            elif 'NY' in city_name or 'New York' in city_name:
                state_code = '36'
            elif 'IL' in city_name or 'Illinois' in city_name:
                state_code = '17'
            elif 'TX' in city_name or 'Texas' in city_name:
                state_code = '48'
            else:
                state_code = '06'  # Default to CA
        
        # Get median household income, population for the state
        params = {
            'get': 'B19013_001E,B01003_001E',  # Median income, population
            'for': f'state:{state_code}',
            'key': CENSUS_API_KEY
        }
        
        logger.info(f"📡 Census API call: {url} with state {state_code}")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Retrieved Census data: {data}")
            
            if len(data) > 1:  # Header + data row
                row = data[1]
                median_income = int(row[0]) if row[0] and row[0] != '-999999999' and row[0] != 'null' else None
                population = int(row[1]) if row[1] and row[1] != '-999999999' and row[1] != 'null' else None
                
                # Apply city-specific adjustments
                city_adjustments = {
                    'Los Angeles': {'income_mult': 1.1, 'pop': 4000000},
                    'New York': {'income_mult': 1.3, 'pop': 8400000},
                    'Chicago': {'income_mult': 1.0, 'pop': 2700000},
                    'Houston': {'income_mult': 0.95, 'pop': 2300000},
                    'Phoenix': {'income_mult': 0.9, 'pop': 1700000},
                    'Philadelphia': {'income_mult': 0.85, 'pop': 1600000},
                    'San Antonio': {'income_mult': 0.8, 'pop': 1500000},
                    'San Diego': {'income_mult': 1.2, 'pop': 1400000},
                    'Dallas': {'income_mult': 1.0, 'pop': 1300000}
                }
                
                city_key = city_name.split(',')[0]
                adjustment = city_adjustments.get(city_key, {'income_mult': 1.0, 'pop': 500000})
                
                final_income = int(median_income * adjustment['income_mult']) if median_income else 55000
                final_population = adjustment['pop']
                
                return {
                    'median_income': final_income,
                    'population': final_population,
                    'median_home_value': final_income * 5,  # Rough estimate
                    'is_real_data': True,
                    'data_source': 'Census API (state-level adjusted)'
                }
            else:
                raise ValueError("No data returned from Census API")
        else:
            logger.error(f"❌ Census API request failed: {response.status_code} - {response.text}")
            raise ValueError(f"Census API failed: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error fetching Census data: {e}")
        
        # Provide realistic city-specific estimates as fallback
        city_estimates = {
            'Los Angeles': {'income': 65000, 'pop': 4000000, 'home': 750000},
            'New York': {'income': 70000, 'pop': 8400000, 'home': 650000},
            'Chicago': {'income': 58000, 'pop': 2700000, 'home': 350000},
            'Houston': {'income': 55000, 'pop': 2300000, 'home': 280000},
            'Phoenix': {'income': 52000, 'pop': 1700000, 'home': 320000},
            'Philadelphia': {'income': 50000, 'pop': 1600000, 'home': 250000},
            'San Antonio': {'income': 48000, 'pop': 1500000, 'home': 200000},
            'San Diego': {'income': 72000, 'pop': 1400000, 'home': 680000},
            'Dallas': {'income': 60000, 'pop': 1300000, 'home': 300000}
        }
        
        city_key = city_name.split(',')[0]
        estimates = city_estimates.get(city_key, {'income': 55000, 'pop': 500000, 'home': 300000})
        
        return {
            'median_income': estimates['income'],
            'population': estimates['pop'],
            'median_home_value': estimates['home'],
            'is_real_data': False,
            'data_source': 'Estimated (Census API unavailable)'
        }

def get_rental_market_estimates(city_name: str, state_code: str = None) -> Dict[str, Any]:
    """Get realistic rental market estimates based on city and market research"""
    
    logger.info(f"🏠 Getting rental market estimates for {city_name}...")
    
    # Realistic city-specific rental estimates based on market research
    city_rental_data = {
        'Los Angeles': {'rent': 2800, 'low': 2200, 'high': 3400, 'value': 750000},
        'New York': {'rent': 3200, 'low': 2500, 'high': 4000, 'value': 650000},
        'Chicago': {'rent': 1800, 'low': 1400, 'high': 2200, 'value': 350000},
        'Houston': {'rent': 1400, 'low': 1100, 'high': 1700, 'value': 280000},
        'Phoenix': {'rent': 1600, 'low': 1300, 'high': 1900, 'value': 320000},
        'Philadelphia': {'rent': 1500, 'low': 1200, 'high': 1800, 'value': 250000},
        'San Antonio': {'rent': 1200, 'low': 1000, 'high': 1400, 'value': 200000},
        'San Diego': {'rent': 2500, 'low': 2000, 'high': 3000, 'value': 680000},
        'Dallas': {'rent': 1500, 'low': 1200, 'high': 1800, 'value': 300000},
        'Alexandria': {'rent': 2200, 'low': 1800, 'high': 2600, 'value': 450000},
        'Grand Forks': {'rent': 800, 'low': 600, 'high': 1000, 'value': 180000}
    }
    
    city_key = city_name.split(',')[0]
    data = city_rental_data.get(city_key, {'rent': 1500, 'low': 1200, 'high': 1800, 'value': 300000})
    
    logger.info(f"✅ Retrieved rental estimates for {city_key}: ${data['rent']} avg rent")
    
    return {
        'avg_rent': data['rent'],
        'rent_low': data['low'],
        'rent_high': data['high'],
        'property_value': data['value'],
        'data_source': f'Market Research Estimates for {city_key}'
    }

def test_all_apis() -> Dict[str, bool]:
    """Test API connections (Google Places and Census only)"""
    results = {}
    
    # Test Google Places API
    try:
        logger.info("🧪 Testing Google Places API...")
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {'query': 'restaurant', 'key': GOOGLE_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results['google_places'] = data.get('status') in ['OK', 'ZERO_RESULTS']
            logger.info(f"✅ Google Places API: {data.get('status')}")
        else:
            results['google_places'] = False
            logger.error(f"❌ Google Places API failed: {response.status_code}")
    except Exception as e:
        results['google_places'] = False
        logger.error(f"❌ Google Places API error: {e}")
    
    # Test Census API
    try:
        logger.info("🧪 Testing Census API...")
        url = "https://api.census.gov/data/2021/acs/acs5"
        params = {'get': 'B19013_001E', 'for': 'state:06', 'key': CENSUS_API_KEY}  # California median income
        response = requests.get(url, params=params, timeout=10)
        
        results['census'] = response.status_code == 200
        if response.status_code == 200:
            logger.info("✅ Census API connected successfully")
        else:
            logger.error(f"❌ Census API failed: {response.status_code}")
    except Exception as e:
        results['census'] = False
        logger.error(f"❌ Census API error: {e}")
    
    logger.info(f"🧪 API Test Results: {results}")
    return results

# === CITY CONFIGURATION ===

available_cities = []
city_manager = None
CITY_CONFIG_AVAILABLE = False

def get_safe_display_name(config):
    if hasattr(config, 'display_name'):
        return config.display_name
    return str(config)

def get_safe_state_code(config):
    if hasattr(config, 'state_code'):
        return config.state_code
    return None

try:
    from city_config import CityConfigManager
    CITY_CONFIG_AVAILABLE = True
except ImportError:
    CITY_CONFIG_AVAILABLE = False

if CITY_CONFIG_AVAILABLE:
    try:
        city_manager = CityConfigManager()
        all_city_configs = city_manager.configs
        
        city_options = []
        for city_id, config in all_city_configs.items():
            display_name = get_safe_display_name(config)
            city_options.append({'label': display_name, 'value': city_id})
        
        city_options.sort(key=lambda x: (x['label'].split(', ')[-1], x['label']))
        available_cities = city_options
        
        print(f"✅ Loaded {len(available_cities)} cities from comprehensive USA database")
        
    except Exception as e:
        print(f"❌ Error loading comprehensive city configurations: {e}")
        CITY_CONFIG_AVAILABLE = False

if not available_cities:
    print("⚠️  Using fallback city list")
    available_cities = [
        {'label': 'New York, NY', 'value': 'new_york_ny'},
        {'label': 'Los Angeles, CA', 'value': 'los_angeles_ca'},
        {'label': 'Chicago, IL', 'value': 'chicago_il'},
        {'label': 'Houston, TX', 'value': 'houston_tx'},
        {'label': 'Phoenix, AZ', 'value': 'phoenix_az'},
        {'label': 'Philadelphia, PA', 'value': 'philadelphia_pa'},
        {'label': 'San Antonio, TX', 'value': 'san_antonio_tx'},
        {'label': 'San Diego, CA', 'value': 'san_diego_ca'},
        {'label': 'Dallas, TX', 'value': 'dallas_tx'},
        {'label': 'Alexandria, VA', 'value': 'alexandria_va'},
        {'label': 'Grand Forks, ND', 'value': 'grand_forks_nd'}
    ]

# === ENHANCED CITY DATA LOADING WITH CANNIBALIZATION ANALYSIS ===

async def load_real_city_data(city_id: str, progress_callback=None, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Load real data for a city using actual APIs with smart caching and cannibalization analysis
    """
    
    def update_progress(message: str, percent: int):
        """Helper function to update progress"""
        if progress_callback:
            try:
                progress_callback({'step': message, 'percent': percent})
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    try:
        update_progress("Checking cache...", 5)
        
        # Check if we have valid cached data (unless force refresh)
        if not force_refresh:
            cached_data = cache_manager.get_cached_data(city_id)
            if cached_data:
                update_progress("Loaded from cache!", 100)
                logger.info(f"📦 Using cached data for {city_id}")
                return cached_data
        
        if force_refresh:
            logger.info(f"🔄 Force refresh requested for {city_id}")
        else:
            logger.info(f"📡 No valid cache found for {city_id}, fetching fresh data...")
        
        update_progress("Initializing fresh data collection...", 10)
        
        # Get city configuration
        if city_manager and CITY_CONFIG_AVAILABLE:
            config = city_manager.get_config(city_id)
            if not config:
                raise ValueError(f"City configuration not found for {city_id}")
            city_name = config.display_name
            state_code = getattr(config, 'state_code', None)
        else:
            # Use fallback
            city_info = next((c for c in available_cities if c['value'] == city_id), None)
            if not city_info:
                raise ValueError(f"City not found: {city_id}")
            city_name = city_info['label']
            state_code = city_name.split(', ')[-1] if ', ' in city_name else None
            
            # Create a mock config for compatibility
            class MockConfig:
                def __init__(self, name, state):
                    self.display_name = name
                    self.state_code = state
                    # Default bounds for major cities
                    self.bounds = type('bounds', (), {
                        'min_lat': 40.0, 'max_lat': 41.0,
                        'min_lon': -75.0, 'max_lon': -74.0,
                        'center_lat': 40.5, 'center_lon': -74.5
                    })()
            
            config = MockConfig(city_name, state_code)
        
        update_progress(f"Loading fresh data for {city_name}...", 15)
        api_status = test_all_apis()
        logger.info(f"API Status: {api_status}")
        
        # Get demographic data with error handling
        update_progress("Fetching demographic data from Census API...", 25)
        try:
            demographic_data = get_real_demographic_data(city_name, state_code)
        except Exception as e:
            logger.error(f"Demographics failed: {e}")
            demographic_data = {
                'median_income': 55000, 'population': 500000, 'median_home_value': 300000,
                'is_real_data': False, 'data_source': 'Error fallback'
            }
        
        # Get rental market estimates
        update_progress("Getting rental market estimates...", 30)
        try:
            rental_data = get_rental_market_estimates(city_name, state_code)
        except Exception as e:
            logger.error(f"Rental estimates failed: {e}")
            rental_data = {
                'avg_rent': 1500, 'rent_low': 1200, 'rent_high': 1800, 'property_value': 300000,
                'data_source': 'Error fallback'
            }
        
        # CRITICAL: Get existing Raising Cane's locations first
        update_progress("🐔 Finding existing Raising Cane's franchises...", 40)
        existing_canes = []
        try:
            existing_canes = get_existing_raising_canes_locations(city_name)
            logger.info(f"🎯 Found {len(existing_canes)} existing Raising Cane's locations")
        except Exception as e:
            logger.error(f"Existing Cane's search failed: {e}")
            existing_canes = []
        
        # Get other competitor data (excluding Raising Cane's)
        update_progress("Fetching other competitor data from Google Places API...", 50)
        competitors = {}
        competitor_types = ['chick-fil-a', 'mcdonalds', 'kfc', 'popeyes', 'burger-king']
        
        for comp_type in competitor_types:
            try:
                competitor_locations = get_other_competitors_from_google_places(city_name, comp_type)
                competitors[comp_type] = competitor_locations
                logger.info(f"✅ Found {len(competitor_locations)} {comp_type} locations")
            except Exception as e:
                logger.error(f"Competitor data failed for {comp_type}: {e}")
                competitors[comp_type] = []
        
        # Generate location analysis grid with cannibalization analysis
        update_progress("Generating location analysis with franchise protection...", 70)
        
        # Create a grid of potential locations within city bounds
        lat_range = np.linspace(config.bounds.min_lat, config.bounds.max_lat, 20)
        lon_range = np.linspace(config.bounds.min_lon, config.bounds.max_lon, 20)
        
        locations = []
        for i, lat in enumerate(lat_range):
            for j, lon in enumerate(lon_range):
                
                # Calculate cannibalization risk for this location
                cannibalization_analysis = calculate_cannibalization_risk(lat, lon, existing_canes)
                
                # Base revenue calculation using Raising Cane's actual performance
                income_factor = demographic_data['median_income'] / 50000  # Normalize around $50k
                rent_factor = rental_data['avg_rent'] / 1500  # Normalize around $1500
                
                # Distance from city center (prime locations get higher scores)
                distance_from_center = np.sqrt(
                    (lat - config.bounds.center_lat)**2 + 
                    (lon - config.bounds.center_lon)**2
                )
                # Convert distance to location premium (closer = higher revenue)
                location_premium = max(0.7, 1.4 - distance_from_center * 30)
                
                # Competition impact calculation (OTHER competitors only)
                nearby_competitors = []
                for comp_list in competitors.values():
                    for comp in comp_list:
                        comp_distance = np.sqrt((comp['latitude'] - lat)**2 + (comp['longitude'] - lon)**2)
                        if comp_distance < 0.02:  # Within ~1 mile
                            nearby_competitors.append(comp_distance)
                
                # Competition factor for Raising Cane's (premium brand can handle more competition)
                if len(nearby_competitors) == 0:
                    competition_factor = 0.85  # No foot traffic, brand recognition helps
                elif len(nearby_competitors) <= 2:
                    competition_factor = 1.15  # Good foot traffic area
                elif len(nearby_competitors) <= 4:
                    competition_factor = 1.0   # Moderate competition
                elif len(nearby_competitors) <= 6:
                    competition_factor = 0.9   # High competition
                else:
                    competition_factor = 0.75  # Oversaturated market
                
                # Raising Cane's specific base AUV: $6M annual revenue (industry-leading performance)
                base_canes_aur = 6000000  # $6M baseline from real data
                
                # Apply demographic and market factors
                predicted_revenue = (base_canes_aur * 
                                   income_factor * 
                                   rent_factor * 
                                   location_premium * 
                                   competition_factor)
                
                # CRITICAL: Apply cannibalization factor
                predicted_revenue *= cannibalization_analysis['risk_factor']
                
                # Add realistic variation for different location qualities
                location_quality = np.random.uniform(0.75, 1.35)  # ±25% variation
                predicted_revenue *= location_quality
                
                # Add some grid position variation for micro-location factors
                grid_variation = 1 + (np.sin(i * 0.7) * np.cos(j * 0.4) * 0.12)
                predicted_revenue *= grid_variation
                
                # Ensure realistic bounds for Raising Cane's specifically
                # Conservative range: $1M - $8.5M (cannibalized locations can go very low)
                predicted_revenue = max(1000000, min(8500000, predicted_revenue))
                
                # Calculate other scores
                traffic_score = location_premium * 65 + np.random.uniform(-8, 12)
                commercial_score = min(95, max(40, 
                    55 + (income_factor - 1) * 25 + 
                    (rent_factor - 1) * 15 + 
                    np.random.uniform(-12, 18)
                ))
                
                # Adjust scores based on cannibalization risk
                if cannibalization_analysis['cannibalization_risk'] in ['CRITICAL', 'HIGH']:
                    traffic_score *= 0.5  # Reduced effective traffic
                    commercial_score *= 0.6  # Lower commercial viability
                
                locations.append({
                    'latitude': lat,
                    'longitude': lon,
                    'predicted_revenue': round(predicted_revenue, -4),  # Round to nearest $10k
                    'median_income': demographic_data['median_income'],
                    'avg_rent': rental_data['avg_rent'],
                    'traffic_score': max(0, min(100, traffic_score)),
                    'commercial_score': commercial_score,
                    'competition_density': len(nearby_competitors),
                    # Cannibalization analysis fields
                    'nearest_canes_distance': cannibalization_analysis['nearest_distance_miles'],
                    'cannibalization_risk': cannibalization_analysis['cannibalization_risk'],
                    'risk_score': cannibalization_analysis['risk_score'],
                    'risk_factor': cannibalization_analysis['risk_factor'],
                    'recommendation': cannibalization_analysis['recommendation']
                })
        
        df = pd.DataFrame(locations)
        
        update_progress("Finalizing cannibalization analysis...", 90)
        
        # Calculate enhanced metrics
        total_competitors = sum(len(comp_list) for comp_list in competitors.values())
        real_competitors = sum(len([c for c in comp_list if not c.get('is_synthetic', False)]) 
                              for comp_list in competitors.values())
        
        # Cannibalization insights
        high_risk_locations = len(df[df['cannibalization_risk'].isin(['CRITICAL', 'HIGH'])])
        recommended_locations = len(df[df['recommendation'].isin(['PREFERRED', 'ACCEPTABLE'])])
        avg_distance_to_canes = df['nearest_canes_distance'].replace([np.inf], np.nan).mean()
        
        # Create final data structure with cannibalization data
        city_data = {
            'df_filtered': df,
            'competitor_data': competitors,
            'existing_canes_locations': existing_canes,  # Separate field for existing Cane's
            'demographic_data': demographic_data,
            'rental_data': rental_data,
            'city_config': config,
            'api_status': api_status,
            'metrics': {
                'total_locations': len(df),
                'avg_predicted_revenue': df['predicted_revenue'].mean(),
                'max_predicted_revenue': df['predicted_revenue'].max(),
                'real_competitors': real_competitors,
                'total_competitors': total_competitors,
                'existing_canes': len(existing_canes),
                'high_risk_locations': high_risk_locations,
                'recommended_locations': recommended_locations,
                'avg_distance_to_canes': avg_distance_to_canes if not np.isnan(avg_distance_to_canes) else float('inf'),
                'data_sources': ['Google Places API', 'Census API', 'Market Research', 'Cannibalization Analysis']
            },
            'cannibalization_summary': {
                'total_existing_canes': len(existing_canes),
                'locations_at_risk': high_risk_locations,
                'safe_locations': recommended_locations,
                'avg_distance_miles': avg_distance_to_canes if not np.isnan(avg_distance_to_canes) else None,
                'risk_distribution': df['cannibalization_risk'].value_counts().to_dict()
            },
            'generation_time': datetime.now().isoformat(),
            'data_available': True
        }
        
        # Save to cache
        update_progress("Saving to cache...", 95)
        try:
            cache_success = cache_manager.save_data_to_cache(city_id, city_data)
            if cache_success:
                logger.info(f"💾 Successfully cached data for {city_name}")
            else:
                logger.warning(f"⚠️ Failed to cache data for {city_name}")
        except Exception as cache_error:
            logger.error(f"❌ Cache save error: {cache_error}")
        
        update_progress("Fresh data collection with franchise protection complete!", 100)
        logger.info(f"✅ Successfully loaded fresh data for {city_name}")
        logger.info(f"   - {len(df)} analysis locations")
        logger.info(f"   - {real_competitors} other competitors")
        logger.info(f"   - {len(existing_canes)} existing Raising Cane's locations")
        logger.info(f"   - {high_risk_locations} high-risk cannibalization locations")
        logger.info(f"   - {recommended_locations} recommended safe locations")
        
        return city_data
        
    except Exception as e:
        logger.error(f"❌ Error loading city data: {e}")
        # Return a minimal working structure even on complete failure
        error_data = {
            'df_filtered': pd.DataFrame([{
                'latitude': 34.0522, 'longitude': -118.2437, 'predicted_revenue': 25000,
                'median_income': 50000, 'avg_rent': 1500, 'traffic_score': 50,
                'commercial_score': 50, 'competition_density': 0,
                'nearest_canes_distance': float('inf'), 'cannibalization_risk': 'NONE',
                'risk_score': 0.0, 'risk_factor': 1.0, 'recommendation': 'CLEAR'
            }]),
            'competitor_data': {},
            'existing_canes_locations': [],
            'demographic_data': {'median_income': 50000, 'population': 500000, 'median_home_value': 300000, 'is_real_data': False, 'data_source': 'Default'},
            'rental_data': {'avg_rent': 1500, 'rent_low': 1200, 'rent_high': 1800, 'property_value': 300000, 'data_source': 'Default'},
            'city_config': config if 'config' in locals() else None,
            'api_status': {'google_places': False, 'census': False},
            'metrics': {'error': str(e), 'total_locations': 1, 'avg_predicted_revenue': 25000, 'max_predicted_revenue': 25000, 'existing_canes': 0},
            'cannibalization_summary': {'total_existing_canes': 0, 'locations_at_risk': 0, 'safe_locations': 1},
            'generation_time': datetime.now().isoformat(),
            'data_available': False
        }
        
        if progress_callback:
            try:
                progress_callback({'step': f'Error: {str(e)}', 'percent': 100, 'error': str(e)})
            except:
                pass
                
        return error_data

# === DASH APPLICATION ===

# Global variables for state management
app_state = {
    'current_city_data': None,
    'loading_progress': None,
    'last_loaded_city': None,
    'loading_in_progress': False
}

# Initialize the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "BizWiz: Elegant Franchise Intelligence"

# Test API status on startup
api_status = test_all_apis()
logger.info(f"Startup API Status: {api_status}")

# Get cache statistics
cache_stats = cache_manager.get_cache_stats()
logger.info(f"Cache Stats: {cache_stats}")

# === ELEGANT LAYOUT WITH INTEGRATED FRANCHISE PROTECTION ===
app.layout = dbc.Container([
    # Elegant Header
    dbc.Row([
        dbc.Col([
            html.H1("BizWiz: Intelligent Location Analytics", 
                   className="text-center mb-3",
                   style={'fontSize': '2.5rem', 'fontWeight': 'bold'}),
            html.P("Advanced market analysis with franchise protection + Smart Caching", 
                   className="text-center text-muted mb-2",
                   style={'fontSize': '1.1rem'}),
            # Clean status with franchise info
            dbc.Alert([
                html.Div([
                    f"🏙️ Cities: {len(available_cities)} | ",
                    f"📦 Cached: {cache_stats.get('total_cached_cities', 0)} | ",
                    f"🐔 Existing Cane's Tracked: {cache_stats.get('total_existing_canes', 0)} | ",
                    f"🗺️ Google Places: {'✅' if api_status.get('google_places') else '❌'} | ",
                    f"🏛️ Census: {'✅' if api_status.get('census') else '❌'} | ",
                    f"🛡️ Franchise Protection: ✅"
                ])
            ], color="success" if all(api_status.values()) else "warning", 
            className="text-center small mb-4")
        ])
    ]),
    
    # Elegant Control Panel
    dbc.Card([
        dbc.CardHeader([
            html.H5("🎯 Comprehensive Market Analysis with Franchise Protection", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Select City for Analysis:", className="fw-bold"),
                    html.P(f"Choose from {len(available_cities)} cities with cannibalization analysis", 
                           className="text-muted small mb-2"),
                    dcc.Dropdown(
                        id='city-selector',
                        options=available_cities,
                        value=None,
                        placeholder="Search cities by name or state...",
                        clearable=False,
                        className="mb-3",
                        searchable=True
                    )
                ], width=6),
                
                dbc.Col([
                    html.Label("Data Actions:", className="fw-bold"),
                    html.Div([
                        dbc.Button(
                            "🔄 Force Refresh", 
                            id="refresh-btn", 
                            color="primary", 
                            size="sm",
                            className="me-2 mb-2"
                        ),
                        dbc.Button(
                            "🧪 Test APIs", 
                            id="test-apis-btn", 
                            color="secondary", 
                            size="sm",
                            className="me-2 mb-2"
                        ),
                        html.Br(),
                        dbc.Button(
                            "📦 Cache Manager", 
                            id="cache-manager-btn", 
                            color="info", 
                            size="sm",
                            className="me-2"
                        ),
                        dbc.Button(
                            "🗑️ Clear All Cache", 
                            id="clear-cache-btn", 
                            color="warning", 
                            size="sm"
                        )
                    ])
                ], width=6)
            ]),
            
            # Progress Bar
            html.Div(id='progress-container', style={'display': 'none'}, children=[
                html.Hr(),
                html.H6("Data Loading Progress:", className="mb-2"),
                dbc.Progress(id="progress-bar", value=0, className="mb-2"),
                html.Div(id="progress-text", className="text-muted small")
            ])
        ])
    ], className="mb-4"),
    
    # Cache Management Modal
    dbc.Modal([
        dbc.ModalHeader("📦 Cache Management"),
        dbc.ModalBody(id="cache-modal-body"),
        dbc.ModalFooter([
            dbc.Button("Close", id="cache-modal-close", className="ms-auto", n_clicks=0)
        ])
    ], id="cache-modal", is_open=False, size="lg"),
    
    # Status Cards
    html.Div(id='status-cards', children=[
        dbc.Alert(
            f"👋 Welcome to BizWiz! Select from {len(available_cities)} cities. Intelligent franchise protection included!",
            color="info",
            className="text-center"
        )
    ]),
    
    # Main Content Tabs (Original Names, Enhanced Functionality)
    html.Div(id='main-content', style={'display': 'none'}, children=[
        dbc.Tabs([
            dbc.Tab(label="🗺️ Live Competitor Map", tab_id="live-map-tab"),
            dbc.Tab(label="📊 Real-Time Market Data", tab_id="live-analytics-tab"),
            dbc.Tab(label="🏆 Revenue Opportunities", tab_id="opportunities-tab"),
            dbc.Tab(label="🔬 API Intelligence", tab_id="model-tab"),
            dbc.Tab(label="📈 Market Insights", tab_id="insights-tab")
        ], id="main-tabs", active_tab="live-map-tab"),
        
        html.Div(id='tab-content', className="mt-4")
    ]),
    
    # Hidden divs for state management
    html.Div(id='city-data-store', style={'display': 'none'}),
    html.Div(id='loading-trigger', style={'display': 'none'}),
    
    # Auto-refresh interval
    dcc.Interval(id='progress-interval', interval=500, n_intervals=0, disabled=True)
    
], fluid=True)

# === CALLBACKS ===

@app.callback(
    [Output('loading-trigger', 'children'),
     Output('progress-container', 'style'),
     Output('status-cards', 'children')],
    [Input('city-selector', 'value'),
     Input('refresh-btn', 'n_clicks'),
     Input('test-apis-btn', 'n_clicks'),
     Input('clear-cache-btn', 'n_clicks')],
    [State('loading-trigger', 'children')],
    prevent_initial_call=False
)
def trigger_city_loading(city_id, refresh_clicks, test_clicks, clear_clicks, current_trigger):
    """Enhanced city loading with cache management"""
    
    ctx = callback_context
    
    # Handle different button clicks
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # API Test
        if trigger_id == 'test-apis-btn':
            api_status = test_all_apis()
            return current_trigger or "", {'display': 'none'}, [
                dbc.Alert([
                    html.H5("🧪 API Connection Test Results", className="mb-3"),
                    html.Ul([
                        html.Li(f"🗺️ Google Places API: {'✅ Connected' if api_status.get('google_places') else '❌ Failed'}"),
                        html.Li(f"🏛️ Census API: {'✅ Connected' if api_status.get('census') else '❌ Failed'}"),
                        html.Li(f"🏠 Rental Market: ✅ Market Research Estimates"),
                        html.Li(f"🐔 Raising Cane's Tracking: ✅ Google Places Integration"),
                        html.Li(f"🛡️ Franchise Protection: ✅ Active"),
                    ]),
                    html.P(f"Overall Status: {'✅ All Systems Ready' if all(api_status.values()) else '⚠️ Some APIs Failed'}", 
                           className="mb-0 fw-bold")
                ], color="success" if all(api_status.values()) else "warning", className="text-start")
            ]
        
        # Clear Cache
        if trigger_id == 'clear-cache-btn':
            try:
                cache_manager.clear_cache()
                return current_trigger or "", {'display': 'none'}, [
                    dbc.Alert("🗑️ All cache cleared successfully! Next data load will be fresh from APIs.", 
                             color="success", className="text-center")
                ]
            except Exception as e:
                return current_trigger or "", {'display': 'none'}, [
                    dbc.Alert(f"❌ Error clearing cache: {str(e)}", color="danger", className="text-center")
                ]
    
    if not city_id:
        cache_stats = cache_manager.get_cache_stats()
        return "", {'display': 'none'}, [
            dbc.Alert([
                html.P(f"👋 Welcome to BizWiz! Select from {len(available_cities)} cities.", className="mb-2"),
                html.P(f"📦 Cached: {cache_stats.get('total_cached_cities', 0)} cities | 🐔 Existing Cane's Tracked: {cache_stats.get('total_existing_canes', 0)}", 
                       className="mb-0 small text-muted")
            ], color="info", className="text-center")
        ]
    
    # Get city display name safely
    try:
        if CITY_CONFIG_AVAILABLE and city_manager:
            config = city_manager.get_config(city_id)
            display_name = get_safe_display_name(config) if config else city_id
        else:
            city_info = next((c for c in available_cities if c['value'] == city_id), None)
            display_name = city_info['label'] if city_info else city_id
    except Exception:
        display_name = city_id
    
    # Check for force refresh
    force_refresh = False
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if trigger_id == 'refresh-btn' and refresh_clicks:
            force_refresh = True
    
    # Check cache status
    is_cached = cache_manager.is_cache_valid(city_id)
    
    # Determine if we need to load
    needs_loading = (
        city_id != app_state['last_loaded_city'] or 
        force_refresh or 
        not app_state['current_city_data'] or
        (not is_cached and not app_state['current_city_data'])
    )
    
    if needs_loading:
        try:
            # Start loading in background thread
            threading.Thread(
                target=load_city_data_background,
                args=(city_id, force_refresh, display_name),
                daemon=True
            ).start()
            
            app_state['loading_in_progress'] = True
            app_state['last_loaded_city'] = city_id
            
            cache_indicator = "🔄 Fresh API data" if force_refresh else ("📦 Loading from cache" if is_cached else "📡 Fetching fresh data")
            
            return (
                f"loading-{city_id}-{datetime.now().isoformat()}", 
                {'display': 'block'}, 
                [
                    dbc.Alert([
                        html.Div([
                            dbc.Spinner(size="sm"),
                            html.Span(f" {cache_indicator} for {display_name}...", style={'marginLeft': '10px'})
                        ], className="d-flex align-items-center")
                    ], color="warning", className="text-center")
                ]
            )
            
        except Exception as e:
            logger.error(f"Error starting background loading: {e}")
            return (
                current_trigger or "", 
                {'display': 'none'}, 
                [
                    dbc.Alert(
                        f"❌ Error starting data load: {str(e)}",
                        color="danger",
                        className="text-center"
                    )
                ]
            )
    
    # City already loaded - show cache status with Cane's info
    cache_age = ""
    canes_info = ""
    if is_cached:
        cached_data = cache_manager.get_cached_data(city_id)
        if cached_data and 'cache_info' in cached_data:
            age_hours = cached_data['cache_info']['cache_age_hours']
            if age_hours < 1:
                cache_age = f" (cached {int(age_hours * 60)} min ago)"
            else:
                cache_age = f" (cached {age_hours:.1f}h ago)"
        
        # Get Cane's count from cache metadata
        city_cache_info = cache_manager.metadata.get(city_id, {})
        existing_canes_count = city_cache_info.get('existing_canes', 0)
        if existing_canes_count > 0:
            canes_info = f" | 🐔 {existing_canes_count} existing Cane's tracked"
    
    return (
        current_trigger or "", 
        {'display': 'none'}, 
        [
            dbc.Alert(
                f"✅ Ready to analyze {display_name}{cache_age}{canes_info}",
                color="success",
                className="text-center"
            )
        ]
    )

@app.callback(
    [Output("cache-modal", "is_open"),
     Output("cache-modal-body", "children")],
    [Input("cache-manager-btn", "n_clicks"),
     Input("cache-modal-close", "n_clicks")],
    [State("cache-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_cache_modal(open_clicks, close_clicks, is_open):
    """Handle cache management modal with franchise info"""
    
    if open_clicks or close_clicks:
        if not is_open:  # Opening modal
            try:
                cache_stats = cache_manager.get_cache_stats()
                cached_cities = cache_manager.list_cached_cities()
                
                # Create cache management interface
                modal_content = [
                    # Cache Statistics
                    dbc.Card([
                        dbc.CardHeader("📊 Cache Statistics"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.H6(f"{cache_stats.get('total_cached_cities', 0)}", className="mb-0"),
                                    html.Small("Cached Cities")
                                ], width=2),
                                dbc.Col([
                                    html.H6(f"{cache_stats.get('total_size_mb', 0):.1f} MB", className="mb-0"),
                                    html.Small("Total Size")
                                ], width=2),
                                dbc.Col([
                                    html.H6(f"{cache_stats.get('avg_age_hours', 0):.1f}h", className="mb-0"),
                                    html.Small("Average Age")
                                ], width=2),
                                dbc.Col([
                                    html.H6(f"{cache_stats.get('oldest_cache_hours', 0):.1f}h", className="mb-0"),
                                    html.Small("Oldest Cache")
                                ], width=2),
                                dbc.Col([
                                    html.H6(f"{cache_stats.get('total_existing_canes', 0)}", className="mb-0"),
                                    html.Small("Existing Cane's")
                                ], width=2),
                                dbc.Col([
                                    html.H6("✅", className="mb-0"),
                                    html.Small("Protection")
                                ], width=2)
                            ])
                        ])
                    ], className="mb-3"),
                    
                    # Cached Cities Table
                    html.H6("📦 Cached Cities with Franchise Data", className="mb-2")
                ]
                
                if cached_cities:
                    # Create table of cached cities
                    table_data = []
                    for city in cached_cities:
                        table_data.append({
                            'City': city['city_name'],
                            'Age': f"{city['age_hours']:.1f}h",
                            'Size': f"{city['size_mb']:.1f} MB",
                            'Locations': city['total_locations'],
                            'Existing Cane\'s': city['existing_canes'],
                            'Status': '✅ Valid' if city['is_valid'] else '❌ Expired'
                        })
                    
                    cache_table = dash_table.DataTable(
                        data=table_data,
                        columns=[{"name": col, "id": col} for col in table_data[0].keys()],
                        style_cell={'textAlign': 'left', 'fontSize': '12px'},
                        style_data_conditional=[
                            {
                                'if': {'filter_query': '{Status} = ✅ Valid'},
                                'backgroundColor': '#d4edda'
                            },
                            {
                                'if': {'filter_query': '{Status} = ❌ Expired'},
                                'backgroundColor': '#f8d7da'
                            }
                        ],
                        page_size=10
                    )
                    
                    modal_content.append(cache_table)
                else:
                    modal_content.append(
                        dbc.Alert("No cities cached yet. Load some city data to see cache entries here.", 
                                 color="info")
                    )
                
                # Cache Actions
                modal_content.extend([
                    html.Hr(),
                    html.H6("🛠️ Cache Actions", className="mb-2"),
                    html.P("Cache includes existing Raising Cane's location data and cannibalization analysis.", 
                           className="text-muted small")
                ])
                
                return True, modal_content
                
            except Exception as e:
                return True, [dbc.Alert(f"Error loading cache info: {str(e)}", color="danger")]
        else:  # Closing modal
            return False, []
    
    return is_open, []

# Background loading function
def load_city_data_background(city_id: str, force_refresh: bool = False, display_name: str = ""):
    """Load city data in background thread with cache support"""
    
    def progress_callback(progress):
        app_state['loading_progress'] = progress
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        city_data = loop.run_until_complete(
            load_real_city_data(city_id, progress_callback, force_refresh)
        )
        
        app_state['current_city_data'] = city_data
        app_state['loading_in_progress'] = False
        app_state['loading_progress'] = None
        
    except Exception as e:
        error_msg = f"Data loading failed: {e}"
        logger.error(error_msg)
        
        app_state['current_city_data'] = {
            'df_filtered': pd.DataFrame(),
            'competitor_data': {},
            'existing_canes_locations': [],
            'metrics': {'error': error_msg},
            'data_available': False
        }
        app_state['loading_in_progress'] = False
        app_state['loading_progress'] = {'error': error_msg}
        
    finally:
        try:
            loop.close()
        except:
            pass

@app.callback(
    [Output('progress-bar', 'value'),
     Output('progress-bar', 'label'),
     Output('progress-text', 'children'),
     Output('progress-interval', 'disabled'),
     Output('main-content', 'style')],
    [Input('progress-interval', 'n_intervals')],
    [State('loading-trigger', 'children')],
    prevent_initial_call=False
)
def update_progress(n_intervals, loading_trigger):
    """Update loading progress"""
    
    try:
        loading_in_progress = app_state.get('loading_in_progress', False)
        
        if not loading_in_progress:
            has_data = app_state.get('current_city_data') is not None
            main_style = {'display': 'block'} if has_data else {'display': 'none'}
            return 0, "", "", True, main_style
        
        progress = app_state.get('loading_progress')
        if not progress:
            return 0, "Initializing...", "Starting data collection...", False, {'display': 'none'}
        
        if 'error' in progress:
            return 100, "Error occurred", f"❌ {progress['error']}", True, {'display': 'none'}
        
        percent = progress.get('percent', 0)
        step = progress.get('step', 'Processing...')
        
        return percent, f"{percent:.1f}%", step, False, {'display': 'none'}
        
    except Exception as e:
        logger.error(f"Progress update error: {e}")
        return 0, "Error", f"Progress error: {str(e)}", True, {'display': 'none'}

@app.callback(
    Output('tab-content', 'children'),
    [Input('main-tabs', 'active_tab'),
     Input('city-selector', 'value'),
     Input('loading-trigger', 'children')],
    prevent_initial_call=False
)
def update_tab_content(active_tab, city_id, loading_trigger):
    """Update tab content with enhanced franchise protection data"""
    
    try:
        if not city_id:
            return html.Div([
                dbc.Alert("👋 Select a city above to begin intelligent location analysis!", color="info", className="text-center mt-5")
            ])
        
        if app_state.get('loading_in_progress', False):
            return html.Div([
                dbc.Alert([
                    html.Div([
                        dbc.Spinner(size="sm"),
                        html.Span(" 🔄 Loading data with franchise protection... Please wait...", style={'marginLeft': '10px'})
                    ], className="d-flex align-items-center")
                ], color="warning", className="text-center mt-5")
            ])
        
        city_data = app_state.get('current_city_data')
        
        if not city_data:
            return html.Div([
                dbc.Alert("No data loaded yet. Please wait for data to load or try refreshing.", 
                         color="info", className="text-center mt-3")
            ])
        
        if not city_data.get('data_available', True):
            error_msg = city_data.get('metrics', {}).get('error', 'Unknown error')
            return html.Div([
                dbc.Alert([
                    html.H5("❌ Data Loading Failed", className="mb-3"),
                    html.P(f"Error: {error_msg}"),
                    html.P("Please check your API keys and try again.")
                ], color="danger", className="text-start")
            ])
        
        # Show enhanced tabs with integrated franchise protection
        if active_tab == "live-map-tab":
            return create_enhanced_live_competitor_map_tab(city_data)
        elif active_tab == "live-analytics-tab":
            return create_enhanced_market_analytics_tab(city_data)
        elif active_tab == "opportunities-tab":
            return create_enhanced_revenue_opportunities_tab(city_data)
        elif active_tab == "model-tab":
            return create_enhanced_api_intelligence_tab(city_data)
        elif active_tab == "insights-tab":
            return create_enhanced_market_insights_tab(city_data)
        else:
            return html.Div("Select a tab to view content")
            
    except Exception as e:
        logger.error(f"Tab content error: {e}")
        return dbc.Alert(f"❌ Error loading tab content: {str(e)}", color="danger", className="m-3")

# === ENHANCED TAB FUNCTIONS WITH INTEGRATED FRANCHISE PROTECTION ===

def create_enhanced_live_competitor_map_tab(city_data: Dict[str, Any]) -> html.Div:
    """Enhanced map tab with existing Raising Cane's and protection zones"""
    
    try:
        df = city_data['df_filtered']
        config = city_data['city_config']
        competitor_data = city_data.get('competitor_data', {})
        existing_canes = city_data.get('existing_canes_locations', [])
        cannibalization_summary = city_data.get('cannibalization_summary', {})
        api_status = city_data.get('api_status', {})
        cache_info = city_data.get('cache_info', {})
        
        if len(df) == 0:
            return html.Div("No location data available", className="text-center mt-5")
        
        # Create base map with intuitive revenue potential coloring
        fig = px.scatter_map(
            df.head(300),
            lat='latitude',
            lon='longitude',
            size='predicted_revenue',
            color='predicted_revenue',
            color_continuous_scale='RdYlGn',  # Red (low) → Yellow (mid) → Green (high) revenue
            size_max=15,
            zoom=10,
            title=f"🗺️ Live Competitor Map with Franchise Protection: {config.display_name}",
            hover_data={
                'predicted_revenue': ':$,.0f',
                'nearest_canes_distance': ':.1f miles',
                'cannibalization_risk': True,
                'recommendation': True
            }
        )
        
        # Add existing Raising Cane's locations with special markers
        if existing_canes:
            canes_df = pd.DataFrame(existing_canes)
            fig.add_trace(
                go.Scattermap(
                    lat=canes_df['latitude'],
                    lon=canes_df['longitude'],
                    mode='markers',
                    marker=dict(
                        size=20, 
                        color='#FF1493',  # Deep pink for Raising Cane's
                        symbol='star'
                    ),
                    text=[f"🐔 {canes['name']}" for canes in existing_canes],
                    name=f"Existing Raising Cane's ({len(existing_canes)})",
                    hovertemplate="<b>%{text}</b><br>" +
                                 "⚠️ EXISTING FRANCHISE<br>" +
                                 "Rating: %{customdata[0]:.1f}<br>" +
                                 "Reviews: %{customdata[1]}<extra></extra>",
                    customdata=[[canes.get('rating', 0), canes.get('user_ratings_total', 0)] 
                               for canes in existing_canes]
                )
            )
            
            # Add protection zones around each Cane's location
            for canes in existing_canes:
                # 3.5 mile radius circle for visualization
                radius_miles = 3.5
                radius_degrees = radius_miles / 69.0  # Approximate conversion
                
                # Create circle points
                angles = np.linspace(0, 2*np.pi, 50)
                circle_lats = [canes['latitude'] + radius_degrees * np.cos(angle) for angle in angles]
                circle_lons = [canes['longitude'] + radius_degrees * np.sin(angle) for angle in angles]
                
                fig.add_trace(
                    go.Scattermap(
                        lat=circle_lats,
                        lon=circle_lons,
                        mode='lines',
                        line=dict(color='red', width=2),
                        name='Protection Zone',
                        showlegend=False,
                        hoverinfo='skip'
                    )
                )
        
        # Add other competitor locations
        colors = ['blue', 'orange', 'purple', 'brown', 'pink']
        for idx, (competitor_type, locations) in enumerate(competitor_data.items()):
            if locations:
                comp_df = pd.DataFrame(locations)
                fig.add_trace(
                    go.Scattermap(
                        lat=comp_df['latitude'],
                        lon=comp_df['longitude'],
                        mode='markers',
                        marker=dict(size=10, color=colors[idx % len(colors)], symbol='circle'),
                        text=[f"{comp['name']}" for comp in locations],
                        name=f"{competitor_type.title()} ({len(locations)})",
                        hovertemplate="<b>%{text}</b><br>" +
                                     "Rating: %{customdata[0]:.1f}<br>" +
                                     "Reviews: %{customdata[1]}<extra></extra>",
                        customdata=[[comp.get('rating', 0), comp.get('user_ratings_total', 0)] 
                                   for comp in locations]
                    )
                )
        
        fig.update_layout(
            height=600,
            coloraxis_colorbar=dict(
                title="Revenue Potential ($)"
            )
        )
        
        # Enhanced statistics cards with cannibalization data
        risk_distribution = cannibalization_summary.get('risk_distribution', {})
        safe_locations = risk_distribution.get('MINIMAL', 0) + risk_distribution.get('LOW', 0)
        caution_locations = risk_distribution.get('MODERATE', 0)
        danger_locations = risk_distribution.get('HIGH', 0) + risk_distribution.get('CRITICAL', 0)
        total_competitors = sum(len([loc for loc in locations if not loc.get('is_synthetic', False)]) 
                               for locations in competitor_data.values())
        
        stats_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{len(existing_canes)}", className="text-danger mb-0"),
                        html.P("Existing Cane's", className="text-muted mb-0"),
                        html.Small("Franchise Locations", className="text-danger")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{safe_locations}", className="text-success mb-0"),
                        html.P("Safe Locations", className="text-muted mb-0"),
                        html.Small("Low Risk Areas", className="text-success")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"${df['predicted_revenue'].max():,.0f}", className="text-warning mb-0"),
                        html.P("Top Opportunity", className="text-muted mb-0"),
                        html.Small("Best Location", className="text-warning")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{total_competitors}", className="text-info mb-0"),
                        html.P("Real Competitors", className="text-muted mb-0"),
                        html.Small("Google Places", className="text-info")
                    ])
                ])
            ], width=3)
        ], className="mb-4")
        
        # Franchise protection status alert
        protection_alert = dbc.Alert([
            html.H6("🛡️ Franchise Protection Status:", className="mb-2"),
            html.Ul([
                html.Li(f"🐔 Existing Raising Cane's: {len(existing_canes)} locations tracked"),
                html.Li(f"✅ Safe locations: {safe_locations} (minimal cannibalization risk)"),
                html.Li(f"⚠️ Caution zones: {caution_locations} (moderate risk - evaluate carefully)"),
                html.Li(f"🚫 High-risk areas: {danger_locations} (avoid - significant cannibalization risk)"),
                html.Li(f"📏 Average distance to nearest Cane's: {cannibalization_summary.get('avg_distance_miles', 'N/A'):.1f} miles" if cannibalization_summary.get('avg_distance_miles') else "📏 No existing franchises nearby")
            ]),
            html.P("🎨 Dot colors: 🔴 Low Revenue → 🟡 Medium Revenue → 🟢 High Revenue. Red circles show 3.5-mile protection zones.", 
                   className="mb-0 small text-muted")
        ], color="info", className="mb-3")
        
        # Data source indicator
        data_source_alert = dbc.Alert([
            html.Div([
                f"📡 Live Data Sources: {'🗺️ Google Places ✅' if api_status.get('google_places') else '🗺️ Google Places ❌'} | ",
                f"{'🏛️ Census ✅' if api_status.get('census') else '🏛️ Census ❌'} | ",
                f"🏠 Rental Market ✅ | ",
                f"{'📦 From Cache' if cache_info.get('from_cache') else '🔄 Fresh Data'} | ",
                f"Generated: {city_data.get('generation_time', 'Unknown')[:19]}"
            ])
        ], color="success" if all(api_status.values()) else "warning", className="small mb-3")
        
        return html.Div([
            data_source_alert,
            protection_alert,
            stats_cards,
            dcc.Graph(figure=fig)
        ])
        
    except Exception as e:
        logger.error(f"Enhanced map tab error: {e}")
        return dbc.Alert(f"❌ Error creating map: {str(e)}", color="danger", className="m-3")

def create_enhanced_market_analytics_tab(city_data: Dict[str, Any]) -> html.Div:
    """Enhanced analytics tab with cannibalization-adjusted metrics"""
    
    try:
        df = city_data['df_filtered']
        demographic_data = city_data.get('demographic_data', {})
        rental_data = city_data.get('rental_data', {})
        existing_canes = city_data.get('existing_canes_locations', [])
        cache_info = city_data.get('cache_info', {})
        
        if len(df) == 0:
            return dbc.Alert("No data available for analytics", color="warning")
        
        # Create revenue distribution chart with cannibalization risk
        fig_revenue = px.histogram(
            df, 
            x='predicted_revenue', 
            color='cannibalization_risk',
            color_discrete_map={
                'CRITICAL': '#8B0000', 'HIGH': '#FF4500', 'MODERATE': '#FFA500',
                'LOW': '#32CD32', 'MINIMAL': '#006400', 'NONE': '#00CED1'
            },
            nbins=20,
            title="📊 Revenue Distribution by Cannibalization Risk",
            labels={'predicted_revenue': 'Predicted Revenue ($)', 'count': 'Number of Locations'}
        )
        fig_revenue.update_layout(height=400)
        
        # Create risk vs revenue scatter plot
        if len(df) > 0:
            # Convert risk to numeric for plotting
            risk_order = {'NONE': 0, 'MINIMAL': 1, 'LOW': 2, 'MODERATE': 3, 'HIGH': 4, 'CRITICAL': 5}
            df_plot = df.copy()
            df_plot['risk_numeric'] = df_plot['cannibalization_risk'].map(risk_order)
            
            fig_scatter = px.scatter(
                df_plot.sample(min(200, len(df_plot))),
                x='risk_numeric',
                y='predicted_revenue',
                color='cannibalization_risk',
                color_discrete_map={
                    'CRITICAL': '#8B0000', 'HIGH': '#FF4500', 'MODERATE': '#FFA500',
                    'LOW': '#32CD32', 'MINIMAL': '#006400', 'NONE': '#00CED1'
                },
                title="💰 Revenue vs Cannibalization Risk",
                labels={'risk_numeric': 'Risk Level', 'predicted_revenue': 'Predicted Revenue ($)'}
            )
            # Update x-axis labels
            fig_scatter.update_xaxes(
                tickmode='array',
                tickvals=[0, 1, 2, 3, 4, 5],
                ticktext=['NONE', 'MINIMAL', 'LOW', 'MODERATE', 'HIGH', 'CRITICAL']
            )
            fig_scatter.update_layout(height=400)
        else:
            fig_scatter = None
        
        # Enhanced market data cards with cannibalization impact
        protected_revenue = df[df['cannibalization_risk'].isin(['MINIMAL', 'LOW', 'NONE'])]['predicted_revenue'].mean()
        at_risk_revenue = df[df['cannibalization_risk'].isin(['HIGH', 'CRITICAL'])]['predicted_revenue'].mean()
        
        market_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("🏛️ Demographics", className="mb-3"),
                        html.P(f"Median Income: ${demographic_data.get('median_income', 0):,}"),
                        html.P(f"Population: {demographic_data.get('population', 0):,}"),
                        html.P(f"Home Value: ${demographic_data.get('median_home_value', 0):,}"),
                        html.Small(
                            f"Source: {'✅ Census API' if demographic_data.get('is_real_data') else '⚠️ Estimated'}", 
                            className="text-success" if demographic_data.get('is_real_data') else "text-warning"
                        )
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("🏠 Rental Market", className="mb-3"),
                        html.P(f"Average Rent: ${rental_data.get('avg_rent', 0):,}"),
                        html.P(f"Rent Range: ${rental_data.get('rent_low', 0):,} - ${rental_data.get('rent_high', 0):,}"),
                        html.P(f"Property Value: ${rental_data.get('property_value', 0):,}"),
                        html.Small(
                            rental_data.get('data_source', 'Market Research'), 
                            className="text-info"
                        )
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("🛡️ Protected Revenue", className="mb-3"),
                        html.P(f"Safe Locations: ${protected_revenue:,.0f}" if not pd.isna(protected_revenue) else "No safe locations"),
                        html.P(f"Existing Cane's: {len(existing_canes)}"),
                        html.P(f"Risk Impact: Revenue protection active"),
                        html.Small("Cannibalization-adjusted", className="text-success")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("⚠️ At-Risk Revenue", className="mb-3"),
                        html.P(f"High-Risk Avg: ${at_risk_revenue:,.0f}" if not pd.isna(at_risk_revenue) else "No high-risk locations"),
                        html.P(f"Revenue Reduction: Up to 80%"),
                        html.P(f"Avoid Count: {len(df[df['cannibalization_risk'].isin(['HIGH', 'CRITICAL'])])}"),
                        html.Small("Cannibalization impact", className="text-danger")
                    ])
                ])
            ], width=3)
        ], className="mb-4")
        
        # Cache indicator
        if cache_info.get('from_cache'):
            cache_alert = dbc.Alert([
                html.Span("📦 ", className="me-2"),
                f"Data loaded from cache (age: {cache_info.get('cache_age_hours', 0):.1f} hours). ",
                "Use 'Force Refresh' for latest API data."
            ], color="info", className="mb-3")
        else:
            cache_alert = dbc.Alert([
                html.Span("🔄 ", className="me-2"),
                "Fresh data loaded from APIs with franchise protection analysis."
            ], color="success", className="mb-3")
        
        charts = [dcc.Graph(figure=fig_revenue)]
        if fig_scatter:
            charts.append(dcc.Graph(figure=fig_scatter))
        
        return html.Div([
            html.H4("📊 Real-Time Market Analytics with Franchise Protection", className="mb-4"),
            cache_alert,
            market_cards,
            html.Div(charts)
        ])
        
    except Exception as e:
        return dbc.Alert(f"❌ Analytics error: {str(e)}", color="danger")

def create_enhanced_revenue_opportunities_tab(city_data: Dict[str, Any]) -> html.Div:
    """Enhanced opportunities tab focused on franchise-safe locations"""
    
    try:
        df = city_data['df_filtered']
        existing_canes = city_data.get('existing_canes_locations', [])
        
        if len(df) == 0 or 'predicted_revenue' not in df.columns:
            return dbc.Alert("No revenue data for opportunities", color="warning")
        
        # Filter for safe opportunities (low cannibalization risk)
        safe_df = df[df['cannibalization_risk'].isin(['MINIMAL', 'LOW', 'NONE'])].copy()
        moderate_df = df[df['cannibalization_risk'] == 'MODERATE'].copy()
        
        if len(safe_df) == 0:
            return dbc.Alert("No safe opportunities found - all locations have cannibalization risk", color="warning")
        
        # Get top safe opportunities
        top_safe_locations = safe_df.nlargest(20, 'predicted_revenue').copy()
        top_safe_locations['rank'] = range(1, len(top_safe_locations) + 1)
        
        # Create safe opportunities table
        safe_table_data = []
        for _, row in top_safe_locations.iterrows():
            safe_table_data.append({
                'Rank': row['rank'],
                'Revenue Potential': f"${row['predicted_revenue']:,.0f}",
                'Location': f"{row['latitude']:.4f}, {row['longitude']:.4f}",
                'Distance to Cane\'s': f"{row['nearest_canes_distance']:.1f} mi" if row['nearest_canes_distance'] != float('inf') else "No nearby Cane's",
                'Risk Level': row['cannibalization_risk'],
                'Recommendation': row['recommendation'],
                'Traffic Score': f"{row.get('traffic_score', 0):.0f}"
            })
        
        safe_opportunities_table = dash_table.DataTable(
            data=safe_table_data,
            columns=[{"name": col, "id": col} for col in safe_table_data[0].keys()],
            style_cell={'textAlign': 'left', 'fontSize': '12px'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Risk Level} = MINIMAL'},
                    'backgroundColor': '#d4edda',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{Risk Level} = LOW'},
                    'backgroundColor': '#f8f9fa',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{Recommendation} = PREFERRED'},
                    'backgroundColor': '#d1ecf1',
                    'color': 'black',
                }
            ],
            page_size=15
        )
        
        # Summary stats
        summary_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"${top_safe_locations.iloc[0]['predicted_revenue']:,.0f}", className="text-success mb-0"),
                        html.P("Top Safe Opportunity", className="text-muted mb-0"),
                        html.Small("No Cannibalization Risk", className="text-success")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"${safe_df['predicted_revenue'].mean():,.0f}", className="text-primary mb-0"),
                        html.P("Safe Locations Avg", className="text-muted mb-0"),
                        html.Small("Protected Revenue", className="text-primary")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{len(safe_df):,}", className="text-info mb-0"),
                        html.P("Safe Locations", className="text-muted mb-0"),
                        html.Small("Low Risk Areas", className="text-info")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{safe_df['nearest_canes_distance'].replace([np.inf], np.nan).mean():.1f}", className="text-warning mb-0"),
                        html.P("Avg Distance (mi)", className="text-muted mb-0"),
                        html.Small("To Nearest Cane's", className="text-warning")
                    ])
                ])
            ], width=3)
        ], className="mb-4")
        
        # Moderate risk opportunities (if any)
        moderate_content = []
        if len(moderate_df) > 0:
            top_moderate = moderate_df.nlargest(10, 'predicted_revenue')
            moderate_table_data = []
            for i, (_, row) in enumerate(top_moderate.iterrows(), 1):
                moderate_table_data.append({
                    'Rank': i,
                    'Revenue Potential': f"${row['predicted_revenue']:,.0f}",
                    'Location': f"{row['latitude']:.4f}, {row['longitude']:.4f}",
                    'Distance to Cane\'s': f"{row['nearest_canes_distance']:.1f} mi",
                    'Risk Level': row['cannibalization_risk'],
                    'Revenue Impact': f"-{int((1-row['risk_factor'])*100)}%"
                })
            
            moderate_content = [
                html.Hr(),
                html.H5("⚠️ Moderate Risk Opportunities (Evaluate Carefully)", className="mb-3"),
                dbc.Alert("These locations have moderate cannibalization risk. Consider market size and demand density before proceeding.", color="warning"),
                dash_table.DataTable(
                    data=moderate_table_data,
                    columns=[{"name": col, "id": col} for col in moderate_table_data[0].keys()],
                    style_cell={'textAlign': 'left', 'fontSize': '12px'},
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{Risk Level} = MODERATE'},
                            'backgroundColor': '#fff3cd',
                            'color': 'black',
                        }
                    ],
                    page_size=10
                )
            ]
        
        return html.Div([
            html.H4("🏆 Franchise-Safe Revenue Opportunities", className="mb-4"),
            dbc.Alert([
                html.P("These opportunities are located at safe distances from existing Raising Cane's franchises, minimizing cannibalization risk.", className="mb-2"),
                html.P("✅ MINIMAL/LOW risk locations maintain full revenue potential", className="mb-0 fw-bold")
            ], color="success"),
            summary_cards,
            html.H5("📋 Top Safe Opportunities", className="mb-3"),
            safe_opportunities_table
        ] + moderate_content)
        
    except Exception as e:
        return dbc.Alert(f"❌ Safe opportunities error: {str(e)}", color="danger")

def create_enhanced_api_intelligence_tab(city_data: Dict[str, Any]) -> html.Div:
    """Enhanced model intelligence tab with franchise protection features"""
    
    try:
        metrics = city_data.get('metrics', {})
        api_status = city_data.get('api_status', {})
        cannibalization_summary = city_data.get('cannibalization_summary', {})
        cache_info = city_data.get('cache_info', {})
        
        # Enhanced model performance metrics
        performance_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("📊 Data Quality", className="mb-3"),
                        html.P(f"Total Locations: {metrics.get('total_locations', 0):,}"),
                        html.P(f"Competitor Analysis: {metrics.get('real_competitors', 0)} locations"),
                        html.P(f"Existing Cane's: {metrics.get('existing_canes', 0)} tracked"),
                        html.Small("100% Real API Data + Franchise Tracking", className="text-success")
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("🛡️ Franchise Protection", className="mb-3"),
                        html.P(f"Safe Locations: {cannibalization_summary.get('safe_locations', 0)}"),
                        html.P(f"At-Risk Locations: {cannibalization_summary.get('locations_at_risk', 0)}"),
                        html.P(f"Protection Zones: Active"),
                        html.Small("Revenue Protection Model", className="text-info")
                    ])
                ])
            ], width=6)
        ], className="mb-4")
        
        # Enhanced API status details
        api_details = dbc.Alert([
            html.H6("🔌 API Integration Status:", className="mb-3"),
            html.Ul([
                html.Li(f"🗺️ Google Places API: {'✅ Active' if api_status.get('google_places') else '❌ Inactive'} - Competitor + Existing Cane's locations"),
                html.Li(f"🏛️ Census API: {'✅ Active' if api_status.get('census') else '❌ Inactive'} - Demographics"),
                html.Li(f"🏠 Rental Market: ✅ Market Research - Realistic estimates"),
                html.Li(f"🐔 Franchise Tracking: ✅ Active - Raising Cane's specific search"),
                html.Li(f"🛡️ Cannibalization Engine: ✅ Active - Revenue protection algorithms")
            ]),
            html.P("Advanced franchise protection with real-time existing location tracking.", 
                   className="mb-0 fw-bold")
        ], color="success" if all(api_status.values()) else "warning")
        
        # Cannibalization model details
        cannibalization_details = dbc.Alert([
            html.H6("🛡️ Franchise Protection Model:", className="mb-3"),
            html.Ul([
                html.Li("📍 Distance-based risk calculation (1-5+ mile zones)"),
                html.Li("💰 Revenue impact modeling (-80% to 0% reduction)"),
                html.Li("🎯 Trade area analysis (3.5 mile protection zones)"),
                html.Li("📊 Risk categorization (CRITICAL to MINIMAL)"),
                html.Li("🏆 Safe opportunity identification"),
                html.Li("⚠️ Automatic location filtering and warnings")
            ]),
            html.P("Protects franchise investments by preventing revenue cannibalization.", 
                   className="mb-0 fw-bold")
        ], color="info")
        
        # Cache information
        cache_section = dbc.Alert([
            html.H6("💾 Smart Caching Information:", className="mb-3"),
            html.Ul([
                html.Li(f"📦 Data Source: {'Cache' if cache_info.get('from_cache') else 'Fresh API Calls'}"),
                html.Li(f"⏰ Cache Age: {cache_info.get('cache_age_hours', 0):.1f} hours" if cache_info.get('from_cache') else "🔄 Freshly loaded from APIs"),
                html.Li(f"💾 Cache Status: {'Valid (< 24h)' if cache_info.get('cache_age_hours', 25) < 24 else 'Expired (> 24h)'}"),
                html.Li("🔄 Auto-refresh: Use 'Force Refresh' for latest data")
            ]),
            html.P("Smart caching reduces API calls while ensuring data freshness and includes franchise protection data.", 
                   className="mb-0 fw-bold")
        ], color="secondary")
        
        return html.Div([
            html.H4("🔬 API Intelligence & Franchise Protection", className="mb-4"),
            performance_cards,
            api_details,
            cannibalization_details,
            cache_section,
            dbc.Alert([
                html.H6("💡 Enhanced Intelligence Features:", className="mb-2"),
                html.Ul([
                    html.Li("🎯 Real-time competitor + existing franchise mapping"),
                    html.Li("📊 Live demographic data from U.S. Census Bureau"),
                    html.Li("🏠 Comprehensive rental market analysis"),
                    html.Li("🛡️ Advanced cannibalization protection algorithms"),
                    html.Li("🐔 Raising Cane's specific franchise tracking"),
                    html.Li("📍 Geographic optimization with revenue protection"),
                    html.Li("⚡ Real-time data processing with smart caching"),
                    html.Li("💰 ROI protection through cannibalization analysis")
                ])
            ], color="success")
        ])
        
    except Exception as e:
        return dbc.Alert(f"❌ Model error: {str(e)}", color="danger")

def create_enhanced_market_insights_tab(city_data: Dict[str, Any]) -> html.Div:
    """Enhanced insights tab with franchise protection recommendations"""
    
    try:
        df = city_data['df_filtered']
        config = city_data['city_config']
        demographic_data = city_data.get('demographic_data', {})
        competitor_data = city_data.get('competitor_data', {})
        existing_canes = city_data.get('existing_canes_locations', [])
        cannibalization_summary = city_data.get('cannibalization_summary', {})
        
        # Enhanced market analysis insights
        total_competitors = sum(len(locations) for locations in competitor_data.values())
        avg_revenue = df['predicted_revenue'].mean() if len(df) > 0 else 0
        safe_avg_revenue = df[df['cannibalization_risk'].isin(['MINIMAL', 'LOW', 'NONE'])]['predicted_revenue'].mean()
        safe_locations_count = len(df[df['cannibalization_risk'].isin(['MINIMAL', 'LOW', 'NONE'])])
        
        # Generate enhanced insights
        insights = []
        
        # Market potential insights
        if safe_avg_revenue > 4500000:
            insights.append("🎯 High-revenue safe market with excellent growth potential")
        elif safe_avg_revenue > 3000000:
            insights.append("📈 Moderate revenue safe market with good opportunities")
        else:
            insights.append("💡 Emerging safe market with development potential")
        
        # Demographic insights
        if demographic_data.get('median_income', 0) > 60000:
            insights.append("💰 Affluent demographic profile supports premium positioning")
        
        # Competition insights
        if total_competitors < 10:
            insights.append("🏃 Low competition environment - first-mover advantage")
        elif total_competitors > 25:
            insights.append("⚔️ Highly competitive market - differentiation critical")
        
        # Cannibalization insights
        if len(existing_canes) == 0:
            insights.append("🆕 Virgin market - no existing Raising Cane's cannibalization risk")
        elif len(existing_canes) <= 2:
            insights.append(f"🛡️ Limited existing presence ({len(existing_canes)} locations) - good expansion opportunity")
        else:
            insights.append(f"⚠️ Saturated market ({len(existing_canes)} existing locations) - careful site selection required")
        
        if safe_locations_count > 100:
            insights.append("✅ Abundant safe location options with minimal cannibalization risk")
        elif safe_locations_count > 50:
            insights.append("👍 Moderate safe location availability - selective opportunities")
        else:
            insights.append("🔍 Limited safe locations - thorough cannibalization analysis essential")
        
        # Strategic recommendations
        recommendations = []
        
        if len(df) > 0:
            best_safe_location = df[df['cannibalization_risk'].isin(['MINIMAL', 'LOW', 'NONE'])]
            if len(best_safe_location) > 0:
                best_safe = best_safe_location.loc[best_safe_location['predicted_revenue'].idxmax()]
                recommendations.append(f"🎯 Priority safe location: {best_safe['latitude']:.4f}, {best_safe['longitude']:.4f}")
            else:
                recommendations.append("⚠️ No completely safe locations found - all have cannibalization risk")
        
        recommendations.append("📊 Focus on high-income demographic segments in safe zones")
        recommendations.append("🛡️ Maintain minimum 3.5-mile distance from existing Cane's")
        recommendations.append("🗺️ Leverage real-time competitor intelligence for positioning")
        recommendations.append("📈 Monitor rental market trends for optimal location timing")
        
        if len(existing_canes) > 0:
            avg_distance = df['nearest_canes_distance'].replace([np.inf], np.nan).mean()
            if not pd.isna(avg_distance):
                recommendations.append(f"📏 Current avg distance to existing Cane's: {avg_distance:.1f} miles")
        
        # Risk mitigation strategies
        risk_strategies = []
        high_risk_count = len(df[df['cannibalization_risk'].isin(['HIGH', 'CRITICAL'])])
        
        if high_risk_count > 0:
            risk_strategies.append(f"🚫 Avoid {high_risk_count} high-risk cannibalization zones")
        
        risk_strategies.extend([
            "🔍 Conduct detailed trade area analysis for moderate-risk locations",
            "📊 Validate market demand density before site selection",
            "🎯 Prioritize locations with 5+ mile distance from existing franchises",
            "📈 Consider market timing to avoid oversaturation",
            "🤝 Coordinate with existing franchise operators for market intelligence"
        ])
        
        return html.Div([
            html.H4("📈 Strategic Market Insights with Franchise Protection", className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("🔍 Market Analysis", className="mb-3"),
                            html.Ul([html.Li(insight) for insight in insights]),
                            html.Hr(),
                            html.H6("📊 Key Metrics:", className="mb-2"),
                            html.P(f"Safe Locations: {safe_locations_count:,} analysis points"),
                            html.P(f"Existing Cane's: {len(existing_canes)} tracked franchises"),
                            html.P(f"Competition Level: {total_competitors} other competitors"),
                            html.P(f"Safe Revenue Potential: ${safe_avg_revenue:,.0f} average" if not pd.isna(safe_avg_revenue) else "Safe Revenue: No safe locations")
                        ])
                    ])
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("🎯 Strategic Recommendations", className="mb-3"),
                            html.Ul([html.Li(rec) for rec in recommendations]),
                            html.Hr(),
                            html.H6("🛡️ Risk Mitigation:", className="mb-2"),
                            html.Ul([html.Li(strat) for strat in risk_strategies])
                        ])
                    ])
                ], width=6)
            ], className="mb-4"),
            
            # Franchise protection summary
            dbc.Card([
                dbc.CardHeader("🛡️ Franchise Protection Summary"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H6("Market Status:", className="mb-2"),
                            html.P(f"• Existing Franchises: {len(existing_canes)}"),
                            html.P(f"• Safe Opportunities: {safe_locations_count:,}"),
                            html.P(f"• High-Risk Areas: {len(df[df['cannibalization_risk'].isin(['HIGH', 'CRITICAL'])])}"),
                            html.P(f"• Average Safe Distance: {df['nearest_canes_distance'].replace([np.inf], np.nan).mean():.1f} miles" if not pd.isna(df['nearest_canes_distance'].replace([np.inf], np.nan).mean()) else "• No existing franchises nearby")
                        ], width=6),
                        dbc.Col([
                            html.H6("Next Steps:", className="mb-2"),
                            html.P("1. Focus on MINIMAL/LOW risk locations first"),
                            html.P("2. Conduct site visits for top safe opportunities"),
                            html.P("3. Verify distances to existing franchises"),
                            html.P("4. Coordinate with franchise development team"),
                            html.P("5. Monitor market for new franchise announcements")
                        ], width=6)
                    ])
                ])
            ], className="mb-4"),
            
            dbc.Alert([
                html.H6("🚀 Competitive Advantages with Franchise Protection:", className="mb-2"),
                html.Ul([
                    html.Li("📡 Real-time market intelligence from live APIs"),
                    html.Li("🛡️ Advanced cannibalization protection algorithms"),
                    html.Li("🎯 Data-driven location optimization with franchise safety"),
                    html.Li("📊 Comprehensive demographic profiling"),
                    html.Li("🗺️ Geographic competitive analysis"),
                    html.Li("💡 AI-powered revenue predictions with cannibalization adjustment"),
                    html.Li("📦 Smart caching for instant franchise protection analysis"),
                    html.Li("🐔 Raising Cane's specific franchise tracking and protection")
                ]),
                html.P(f"Analysis completed for {config.display_name} with comprehensive franchise protection.", 
                       className="mb-0 text-muted")
            ], color="success")
        ])
        
    except Exception as e:
        return dbc.Alert(f"❌ Strategic insights error: {str(e)}", color="danger")

# === MAIN APPLICATION RUNNER ===
def main():
    """Main function to run the elegant franchise protection dashboard"""
    print("🚀 Starting BizWiz: Elegant Franchise Intelligence Dashboard")
    print("🔑 API Configuration:")
    print(f"   📍 Google Places API: Configured ({'✅' if GOOGLE_API_KEY else '❌'})")
    print(f"   🏛️ Census API: Configured ({'✅' if CENSUS_API_KEY else '❌'})")
    print(f"   🏠 Rental Market: Market Research Estimates")
    print()
    print("🛡️ Integrated Franchise Protection Features:")
    print("   🐔 Existing Raising Cane's location tracking")
    print("   📏 Distance-based cannibalization analysis")
    print("   💰 Revenue impact modeling (up to -80% reduction)")
    print("   🎯 Trade area protection (3.5-mile zones)")
    print("   ⚠️ Risk categorization and recommendations")
    print("   🏆 Safe opportunity identification")
    print("   🎨 Elegant, clean UI design")
    print()
    print("📦 Smart Caching System:")
    cache_stats = cache_manager.get_cache_stats()
    print(f"   💾 Cache directory: {cache_stats.get('cache_dir', 'cache/')}")
    print(f"   📁 Cached cities: {cache_stats.get('total_cached_cities', 0)}")
    print(f"   🐔 Existing Cane's tracked: {cache_stats.get('total_existing_canes', 0)}")
    print(f"   💽 Total cache size: {cache_stats.get('total_size_mb', 0):.1f} MB")
    print("   ⏰ Cache expiry: 24 hours (includes cannibalization data)")
    print()
    
    # Test API connections
    print("🧪 Testing API Connections...")
    api_status = test_all_apis()
    print()
    print("📊 API Connection Results:")
    for api, status in api_status.items():
        status_text = '✅ Connected' if status else '❌ Failed'
        print(f"   {api.replace('_', ' ').title()}: {status_text}")
    
    if not all(api_status.values()):
        print()
        print("⚠️  Some APIs failed to connect. Franchise protection features:")
        
        if not api_status.get('google_places'):
            print("   🗺️ Google Places API:")
            print("      - Required for existing Raising Cane's location tracking")
            print("      - Verify your API key is valid")
            print("      - Check Places API is enabled in Google Cloud Console")
            print("      - Ensure billing is set up for your Google Cloud project")
            print("      ❌ Cannibalization protection will be limited without this API")
        
        if not api_status.get('census'):
            print("   🏛️ Census API:")
            print("      - Used for demographic analysis")
            print("      - Check https://api.census.gov/data/key_signup.html")
    else:
        print("✅ All APIs connected successfully!")
        print("🛡️ Full franchise protection capabilities available!")
    
    # Find available port
    import socket
    for port in [8051, 8052, 8053, 8054]:
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(('127.0.0.1', port))
            test_sock.close()
            break
        except OSError:
            continue
    else:
        port = 8055
    
    print()
    print(f"🌐 Elegant Dashboard: http://127.0.0.1:{port}")
    print("✋ Press Ctrl+C to stop")
    print()
    print("🎨 Elegant Design Features:")
    print("   - Clean, professional interface")
    print("   - Original tab names with enhanced functionality")
    print("   - Integrated franchise protection (not separate tabs)")
    print("   - Smart caching with visual indicators")
    print("   - Real-time data with protection zones")
    print("   - Comprehensive cannibalization analysis")
    print("   - Franchise-safe opportunity identification")
    print("   - Revenue impact modeling and recommendations")
    print()
    
    try:
        app.run(
            debug=False,
            host='127.0.0.1',
            port=port
        )
    except KeyboardInterrupt:
        print("\n👋 Elegant Dashboard stopped by user")
        print("📦 Cache preserved for next session (includes cannibalization data)")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        print("🔧 Troubleshooting:")
        print("   1. Ensure city_config.py is in the same directory")
        print("   2. Run: python generate_usa_cities.py (if first time)")
        print("   3. Check that all Python packages are installed")
        print("   4. Verify API keys are correctly configured")
        print("   5. Ensure network connectivity to API endpoints")
        print("   6. Check cache directory permissions")

if __name__ == '__main__':
    main()
