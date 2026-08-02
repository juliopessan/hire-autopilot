"""
Base class for platform scrapers
"""

from abc import ABC, abstractmethod
from typing import List, Dict
import hashlib

class PlatformScraper(ABC):
    """Base class for job platform scrapers"""

    def __init__(self, name: str):
        self.name = name
        self.jobs = []

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        """Scrape jobs from platform. Must return list of job dicts."""
        pass

    def normalize_job(self, title: str, company: str, location: str,
                     salary: str, url: str, description: str = "") -> Dict:
        """
        Normalize job data to standard format.

        Returns dict with:
        - id: unique hash
        - platform: platform name
        - title, company, location, salary, url, description
        """
        job_key = f"{title}_{company}_{url}"
        job_id = hashlib.sha256(job_key.encode()).hexdigest()[:16]

        return {
            "id": job_id,
            "platform": self.name,
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "url": url,
            "description": description,
            "job_key": job_key,  # For deduplication
        }

    def __repr__(self):
        return f"<{self.name}Scraper>"
