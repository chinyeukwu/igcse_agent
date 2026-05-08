"""
Online/offline status detector for determining connectivity.
Provides network status detection for offline-first architecture decisions.
"""

import socket
from typing import Tuple


class StatusDetector:
    """Detects and tracks online/offline status with configurable checks."""

    # Default hosts to check connectivity (primary + fallback)
    DEFAULT_CHECK_HOSTS = [
        ("8.8.8.8", 53),          # Google DNS
        ("1.1.1.1", 53),          # Cloudflare DNS
        ("208.67.222.222", 53)    # OpenDNS
    ]

    @staticmethod
    def is_online(
        timeout_seconds: int = 3,
        check_hosts: Tuple[Tuple[str, int], ...] = None
    ) -> bool:
        """
        Check if device has internet connectivity via DNS lookup.
        
        Args:
            timeout_seconds: Socket timeout for DNS check (default: 3 seconds)
            check_hosts: List of (host, port) tuples to check (default: Google/Cloudflare DNS)
        
        Returns:
            True if online (can reach at least one host), False if offline
        """
        hosts_to_check = check_hosts or StatusDetector.DEFAULT_CHECK_HOSTS

        for host, port in hosts_to_check:
            try:
                # Create a socket and attempt connection
                socket.create_connection((host, port), timeout=timeout_seconds)
                return True

            except (socket.error, socket.timeout, OSError):
                # This host is unreachable, try next
                continue

        # If we get here, all hosts failed
        return False

    @staticmethod
    def get_connectivity_status() -> dict:
        """
        Get detailed connectivity status information.
        
        Returns:
            Dictionary with connectivity details
        """
        return {
            "is_online": StatusDetector.is_online(),
            "check_timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }

    @staticmethod
    def check_with_fallback(
        primary_timeout: int = 2,
        fallback_timeout: int = 5
    ) -> Tuple[bool, str]:
        """
        Check online status with primary and fallback timeouts.
        
        Args:
            primary_timeout: Fast check timeout
            fallback_timeout: Slower fallback timeout
        
        Returns:
            Tuple of (is_online, status_message)
        """
        # Try fast check first
        if StatusDetector.is_online(timeout_seconds=primary_timeout):
            return True, "Online (fast)"

        # Try slower check as fallback
        if StatusDetector.is_online(timeout_seconds=fallback_timeout):
            return True, "Online (slow connection)"

        return False, "Offline"
