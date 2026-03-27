"""
REST Countries API Tool
Production-grade client for fetching country data.
"""

import aiohttp
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from utils.helpers import setup_logging
from models.schemas import CountryField

logger = setup_logging("country_api")




@dataclass
class CountryData:
    """Structured country data response."""
    name: str
    official_name: str
    population: Optional[int] = None
    capital: Optional[List[str]] = None
    currencies: Optional[Dict[str, Any]] = None
    languages: Optional[Dict[str, str]] = None
    region: Optional[str] = None
    subregion: Optional[str] = None
    area: Optional[float] = None
    flag_url: Optional[str] = None
    timezones: Optional[List[str]] = None
    calling_codes: Optional[List[str]] = None
    
    def get_field_value(self, field: CountryField) -> Any:
        """Get a specific field value in a user-friendly format."""
        field_map = {
            CountryField.POPULATION: self.population,
            CountryField.CAPITAL: self.capital[0] if self.capital else None,
            CountryField.CURRENCY: self._format_currencies(),
            CountryField.LANGUAGE: self._format_languages(),
            CountryField.REGION: self.region,
            CountryField.SUBREGION: self.subregion,
            CountryField.AREA: self.area,
            CountryField.FLAG: self.flag_url,
            CountryField.TIMEZONE: self.timezones[0] if self.timezones else None,
            CountryField.CALLING_CODE: self.calling_codes[0] if self.calling_codes else None,
        }
        return field_map.get(field)
    
    def _format_currencies(self) -> Optional[str]:
        """Format currencies as readable string."""
        if not self.currencies:
            return None
        currency_list = []
        for code, data in self.currencies.items():
            name = data.get("name", "")
            symbol = data.get("symbol", "")
            if name and symbol:
                currency_list.append(f"{name} ({symbol})")
            elif name:
                currency_list.append(name)
            else:
                currency_list.append(code)
        return ", ".join(currency_list)
    
    def _format_languages(self) -> Optional[str]:
        """Format languages as readable string."""
        if not self.languages:
            return None
        return ", ".join(self.languages.values())


class RESTCountriesClient:
    """Production client for REST Countries API."""
    
    BASE_URL = "https://restcountries.com/v3.1"
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session
    
    async def search_country(self, name: str) -> Optional[CountryData]:
        """
        Search for a country by name.
        
        Args:
            name: Country name (partial or full)
            
        Returns:
            CountryData if found, None otherwise
        """
        url = f"{self.BASE_URL}/name/{name}"
        
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 404:
                    logger.warning(f"Country not found: {name}")
                    return None
                
                response.raise_for_status()
                data = await response.json()
                
                if not data:
                    return None
                
                # Return the best match (usually exact match or first result)
                return self._parse_country_data(data[0])
                
        except aiohttp.ClientError as e:
            logger.error(f"API request failed for '{name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching country '{name}': {e}")
            return None
    
    def _parse_country_data(self, data: Dict[str, Any]) -> CountryData:
        """Parse API response into CountryData."""
        name_data = data.get("name", {})
        
        return CountryData(
            name=name_data.get("common", ""),
            official_name=name_data.get("official", ""),
            population=data.get("population"),
            capital=data.get("capital"),
            currencies=data.get("currencies"),
            languages=data.get("languages"),
            region=data.get("region"),
            subregion=data.get("subregion"),
            area=data.get("area"),
            flag_url=data.get("flags", {}).get("png"),
            timezones=data.get("timezones"),
            calling_codes=data.get("idd", {}).get("suffixes")
        )
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton instance for reuse
_country_client: Optional[RESTCountriesClient] = None


def get_country_client() -> RESTCountriesClient:
    """Get singleton instance of REST Countries client."""
    global _country_client
    if _country_client is None:
        _country_client = RESTCountriesClient()
    return _country_client


async def fetch_country_data(country_name: str) -> Optional[CountryData]:
    """
    Convenience function to fetch country data.
    
    Args:
        country_name: Name of the country to search
        
    Returns:
        CountryData if found, None otherwise
    """
    client = get_country_client()
    return await client.search_country(country_name)
