"""
The Muse API adapter.
Unauthenticated usage (no API key required for low volume).
Docs: https://www.themuse.com/developers/api/v2
"""

import requests
from .base import JobSource, RawJob


class TheMuseSource(JobSource):
    BASE_URL = "https://www.themuse.com/api/public/jobs"

    @property
    def name(self):
        return "The Muse"

    def fetch(self, query, location="Atlanta, GA"):
        jobs = []

        # The Muse uses category-based filtering, not free-text search.
        # We fetch "Business Operations" and "Project Management" categories
        # and filter by query keywords in post-processing.
        categories = ["Business Operations", "Project Management and Logistics"]

        for category in categories:
            for page_num in range(2):  # 2 pages per category
                try:
                    resp = requests.get(
                        self.BASE_URL,
                        params={
                            "category": category,
                            "location": "Atlanta, GA",
                            "page": page_num,
                        },
                        timeout=15,
                    )
                    resp.raise_for_status()
                except requests.RequestException as e:
                    print(f"  [The Muse] Error fetching category '{category}' page {page_num}: {e}")
                    break

                results = resp.json().get("results", [])
                if not results:
                    break

                for j in results:
                    company_data = j.get("company", {})
                    locations = j.get("locations", [])
                    loc_str = ", ".join(loc.get("name", "") for loc in locations) if locations else ""

                    # Extract company size
                    size_data = company_data.get("size", {})
                    company_size = size_data.get("name", "") if isinstance(size_data, dict) else ""

                    # Extract industry
                    industries = company_data.get("industries", [])
                    industry = industries[0].get("name", "") if industries else ""

                    # Check if remote
                    is_remote = any("remote" in loc.get("name", "").lower() for loc in locations)

                    # Detect job type from levels
                    levels = j.get("levels", [])
                    level_names = [l.get("name", "") for l in levels]

                    jobs.append(RawJob(
                        title=j.get("name", ""),
                        company=company_data.get("name", ""),
                        location=loc_str,
                        description=j.get("contents", ""),
                        apply_link=j.get("refs", {}).get("landing_page", ""),
                        source="The Muse",
                        company_size=company_size,
                        industry=industry,
                        is_remote=is_remote,
                        company_description=company_data.get("short_name", ""),
                        date_posted=j.get("publication_date"),
                    ))

        # Also try fetching remote jobs in these categories
        for category in categories:
            try:
                resp = requests.get(
                    self.BASE_URL,
                    params={
                        "category": category,
                        "location": "Flexible / Remote",
                        "page": 0,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                for j in resp.json().get("results", []):
                    company_data = j.get("company", {})
                    locations = j.get("locations", [])
                    loc_str = ", ".join(loc.get("name", "") for loc in locations) if locations else "Remote"

                    size_data = company_data.get("size", {})
                    company_size = size_data.get("name", "") if isinstance(size_data, dict) else ""
                    industries = company_data.get("industries", [])
                    industry = industries[0].get("name", "") if industries else ""

                    jobs.append(RawJob(
                        title=j.get("name", ""),
                        company=company_data.get("name", ""),
                        location=loc_str,
                        description=j.get("contents", ""),
                        apply_link=j.get("refs", {}).get("landing_page", ""),
                        source="The Muse",
                        company_size=company_size,
                        industry=industry,
                        is_remote=True,
                        company_description=company_data.get("short_name", ""),
                        date_posted=j.get("publication_date"),
                    ))
            except requests.RequestException as e:
                print(f"  [The Muse] Error fetching remote '{category}': {e}")

        print(f"  [The Muse] total → {len(jobs)} jobs")
        return jobs
