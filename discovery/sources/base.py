"""
Base classes for job sources.
All sources normalize results into the RawJob dataclass.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawJob:
    """Standardized job record from any source."""
    title: str
    company: str
    location: str
    description: str
    apply_link: str
    source: str  # "Adzuna", "Remotive", "The Muse", "Indeed", "Google Jobs"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_text: Optional[str] = None
    job_type: Optional[str] = None  # "Full-time", "Part-time", "Contract"
    is_remote: Optional[bool] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    date_posted: Optional[str] = None
    company_description: Optional[str] = None


class JobSource(ABC):
    """Abstract base class for job board API adapters."""

    @abstractmethod
    def fetch(self, query: str, location: str = "Atlanta, GA") -> list[RawJob]:
        """Fetch jobs matching the query. Returns normalized RawJob list."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name."""
        pass
