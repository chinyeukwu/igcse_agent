"""
Offline cache manager for storing and retrieving cached responses.
Handles cache expiry, cleanup, and conflict resolution for sync operations.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from src.database.models import OfflineCache


class CacheManager:
    """Manages offline caching of responses for offline-first architecture."""

    DEFAULT_CACHE_TTL_DAYS = 7  # Cache expires after 7 days

    @staticmethod
    def generate_cache_key(query: str, subject: str, language_code: str = "en") -> str:
        """
        Generate a deterministic cache key from query content.
        
        Args:
            query: User's original query text
            subject: IGCSE subject (maths|english|french|science|finearts)
            language_code: Language code (default: en)
        
        Returns:
            SHA256 hash of the query components
        """
        # Normalize query for consistent hashing
        normalized_query = query.lower().strip()
        key_material = f"{normalized_query}_{subject}_{language_code}"
        return hashlib.sha256(key_material.encode()).hexdigest()

    @staticmethod
    def cache_response(
        db_session: Session,
        query: str,
        response: str,
        subject: str,
        language_code: str = "en",
        ttl_days: Optional[int] = None
    ) -> bool:
        """
        Store a response in offline cache.
        
        Args:
            db_session: SQLAlchemy session
            query: User's query
            response: Response to cache
            subject: IGCSE subject
            language_code: Language code
            ttl_days: Time-to-live in days (default: 7)
        
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            cache_key = CacheManager.generate_cache_key(query, subject, language_code)
            ttl = ttl_days or CacheManager.DEFAULT_CACHE_TTL_DAYS
            expires_at = datetime.utcnow() + timedelta(days=ttl)

            # Check if entry already exists
            existing = db_session.query(OfflineCache).filter_by(cache_key=cache_key).first()
            
            if existing:
                # Update existing cache entry
                existing.response_json = response
                existing.created_at = datetime.utcnow()
                existing.expires_at = expires_at
            else:
                # Create new cache entry
                cache_entry = OfflineCache(
                    cache_key=cache_key,
                    response_json=response,
                    subject=subject,
                    language_code=language_code,
                    created_at=datetime.utcnow(),
                    expires_at=expires_at
                )
                db_session.add(cache_entry)

            db_session.commit()
            return True

        except Exception as e:
            db_session.rollback()
            print(f"Cache storage error: {str(e)}")
            return False

    @staticmethod
    def get_cached_response(
        db_session: Session,
        query: str,
        subject: str,
        language_code: str = "en"
    ) -> Optional[str]:
        """
        Retrieve a cached response if available and not expired.
        
        Args:
            db_session: SQLAlchemy session
            query: User's query
            subject: IGCSE subject
            language_code: Language code
        
        Returns:
            Cached response string or None if not found/expired
        """
        try:
            cache_key = CacheManager.generate_cache_key(query, subject, language_code)
            cached = db_session.query(OfflineCache).filter_by(cache_key=cache_key).first()

            if cached and not cached.is_expired():
                return cached.response_json
            
            # Remove expired entry
            if cached and cached.is_expired():
                db_session.delete(cached)
                db_session.commit()

            return None

        except Exception as e:
            print(f"Cache retrieval error: {str(e)}")
            return None

    @staticmethod
    def cleanup_expired_cache(db_session: Session) -> int:
        """
        Remove all expired cache entries from database.
        
        Args:
            db_session: SQLAlchemy session
        
        Returns:
            Number of entries deleted
        """
        try:
            expired_entries = db_session.query(OfflineCache).filter(
                OfflineCache.expires_at < datetime.utcnow()
            ).all()

            count = len(expired_entries)
            for entry in expired_entries:
                db_session.delete(entry)
            
            db_session.commit()
            return count

        except Exception as e:
            db_session.rollback()
            print(f"Cache cleanup error: {str(e)}")
            return 0

    @staticmethod
    def get_cache_size_for_subject(db_session: Session, subject: str) -> int:
        """
        Get number of cached entries for a specific subject.
        
        Args:
            db_session: SQLAlchemy session
            subject: IGCSE subject
        
        Returns:
            Number of active (non-expired) cache entries
        """
        try:
            active_cache = db_session.query(OfflineCache).filter(
                OfflineCache.subject == subject,
                OfflineCache.expires_at > datetime.utcnow()
            ).count()
            return active_cache

        except Exception as e:
            print(f"Cache size query error: {str(e)}")
            return 0

    @staticmethod
    def clear_all_cache(db_session: Session) -> int:
        """
        Clear all cache entries (useful for testing or reset).
        
        Args:
            db_session: SQLAlchemy session
        
        Returns:
            Number of entries deleted
        """
        try:
            all_entries = db_session.query(OfflineCache).all()
            count = len(all_entries)
            
            for entry in all_entries:
                db_session.delete(entry)
            
            db_session.commit()
            return count

        except Exception as e:
            db_session.rollback()
            print(f"Cache clear error: {str(e)}")
            return 0

    @staticmethod
    def get_cache_statistics(db_session: Session) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics for monitoring.
        
        Args:
            db_session: SQLAlchemy session
        
        Returns:
            Dictionary with cache metrics
        """
        try:
            total_entries = db_session.query(OfflineCache).count()
            active_entries = db_session.query(OfflineCache).filter(
                OfflineCache.expires_at > datetime.utcnow()
            ).count()
            expired_entries = total_entries - active_entries
            
            # Count by subject
            subjects = db_session.query(OfflineCache.subject).distinct().all()
            subject_counts = {}
            for (subject,) in subjects:
                count = db_session.query(OfflineCache).filter(
                    OfflineCache.subject == subject,
                    OfflineCache.expires_at > datetime.utcnow()
                ).count()
                subject_counts[subject] = count
            
            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "by_subject": subject_counts,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Cache statistics error: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
