"""Collector agent for fetching emails from various sources."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..models import Email, ConnectorConfig
from ..connectors import GmailConnector
from ..sdk.base import BaseConnector
from ..sdk.exceptions import ConnectorError, AuthenticationError

logger = logging.getLogger(__name__)


class CollectorAgent:
    """Agent responsible for collecting emails from various connectors."""
    
    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        self.stats: Dict[str, Any] = {
            "total_collected": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "last_sync": None
        }
    
    async def collect_emails(
        self, 
        connector_configs: List[ConnectorConfig], 
        since: Optional[datetime] = None
    ) -> List[Email]:
        """Collect emails from all configured connectors."""
        if since is None:
            since = datetime.now() - timedelta(days=1)  # Default to last 24 hours
        
        all_emails = []
        tasks = []
        
        # Create collection tasks for each connector
        for config in connector_configs:
            if config.enabled:
                task = self._collect_from_connector(config, since)
                tasks.append(task)
        
        if not tasks:
            logger.warning("No enabled connectors found")
            return []
        
        # Execute all collection tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            config = connector_configs[i]
            
            if isinstance(result, Exception):
                logger.error(f"Failed to collect from {config.name}: {str(result)}")
                self.stats["failed_syncs"] += 1
            else:
                emails = result or []
                all_emails.extend(emails)
                self.stats["successful_syncs"] += 1
                logger.info(f"Collected {len(emails)} emails from {config.name}")
        
        self.stats["total_collected"] += len(all_emails)
        self.stats["last_sync"] = datetime.now()
        
        logger.info(f"Total emails collected: {len(all_emails)}")
        return all_emails
    
    async def _collect_from_connector(
        self, 
        config: ConnectorConfig, 
        since: datetime
    ) -> List[Email]:
        """Collect emails from a single connector."""
        try:
            # Get or create connector instance
            connector = await self._get_connector(config)
            
            # Authenticate if needed
            if not connector.authenticated:
                success = await connector.authenticate()
                if not success:
                    raise AuthenticationError(f"Authentication failed for {config.name}")
            
            # Pull emails
            emails = await connector.pull(since)
            
            # Add connector metadata to emails
            for email in emails:
                email.connector_data["connector_type"] = config.type
                email.connector_data["connector_name"] = config.name
            
            return emails
            
        except Exception as e:
            logger.error(f"Error collecting from {config.name}: {str(e)}")
            raise ConnectorError(f"Collection failed for {config.name}: {str(e)}")
    
    async def _get_connector(self, config: ConnectorConfig) -> BaseConnector:
        """Get or create a connector instance."""
        connector_key = f"{config.type}_{config.name}"
        
        if connector_key not in self.connectors:
            connector = await self._create_connector(config)
            self.connectors[connector_key] = connector
        
        return self.connectors[connector_key]
    
    async def _create_connector(self, config: ConnectorConfig) -> BaseConnector:
        """Create a new connector instance."""
        if config.type == "gmail":
            return GmailConnector(config.config)
        else:
            raise ConnectorError(f"Unknown connector type: {config.type}")
    
    async def test_connector(self, config: ConnectorConfig) -> Dict[str, Any]:
        """Test a connector configuration."""
        result = {
            "connector_name": config.name,
            "connector_type": config.type,
            "success": False,
            "error": None,
            "auth_status": "unknown",
            "test_results": {}
        }
        
        try:
            connector = await self._create_connector(config)
            
            # Test authentication
            auth_success = await connector.authenticate()
            result["auth_status"] = "success" if auth_success else "failed"
            
            if auth_success:
                # Test pulling a small number of emails
                test_emails = await connector.pull(
                    since=datetime.now() - timedelta(minutes=5)
                )
                
                result["test_results"] = {
                    "emails_found": len(test_emails),
                    "supports_push": connector.supports_push,
                    "connector_type": connector.connector_type
                }
                result["success"] = True
            else:
                result["error"] = "Authentication failed"
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Connector test failed for {config.name}: {str(e)}")
        
        return result
    
    async def get_connector_stats(self, connector_name: str) -> Dict[str, Any]:
        """Get statistics for a specific connector."""
        # Find connector in our instances
        for key, connector in self.connectors.items():
            if connector_name in key:
                return {
                    "connector_type": connector.connector_type,
                    "authenticated": connector.authenticated,
                    "supports_push": connector.supports_push,
                    "last_used": "recently"  # Would track this in real implementation
                }
        
        return {"error": f"Connector {connector_name} not found"}
    
    async def refresh_connector_auth(self, config: ConnectorConfig) -> bool:
        """Refresh authentication for a connector."""
        try:
            connector = await self._get_connector(config)
            return await connector.authenticate()
        except Exception as e:
            logger.error(f"Failed to refresh auth for {config.name}: {str(e)}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get collector agent status."""
        return {
            "active_connectors": len(self.connectors),
            "stats": self.stats.copy(),
            "connector_types": list(set(
                conn.connector_type for conn in self.connectors.values()
            ))
        }
    
    async def shutdown(self) -> None:
        """Shutdown the collector agent."""
        try:
            # Close all connector connections
            for connector in self.connectors.values():
                if hasattr(connector, 'close'):
                    await connector.close()
            
            self.connectors.clear()
            logger.info("Collector agent shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during collector shutdown: {str(e)}")
    
    def get_supported_connector_types(self) -> List[str]:
        """Get list of supported connector types."""
        return ["gmail"]  # Expand as more connectors are added