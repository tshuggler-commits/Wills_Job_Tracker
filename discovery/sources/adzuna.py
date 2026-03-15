"""
Adzuna API adapter.
Free tier: ~250 requests/day.
Docs: https://developer.adzuna.com/docs/search
"""

import os
import requests
from .base import JobSource, RawJob


class AdzunaSource(JobSource):
    BASE_URL = "https://api.adzuna.com/v1/api/jobs/us/search"

    def __init__(self):
        self.app_id = os.environ.get("ADZUNA_APP_ID", "")
        self.app_key = os.environ.get("ADZUNA_APP_KEY", "")

    @property
    def name(self):
        return "Adzuna"

    def fetch(self, query, location="Atlanta, GA"):
        if not self.app_id or not self.app_key:
            print("  [Adzuna] Skipping — ADZUNA_APP_ID or ADZUNA_APP_KEY not set")
            return []

        jobs = []
        for page in range(1, 3):  # 2 pages = up to 40 results per query
            try:
                resp = requests.get(
                    f"{self.BASE_URL}/{page}",
                    params={
                        "app_id": self.app_id,
                        "app_key": self.app_key,
                        "results_per_page": 20,
                        "what": query,
                        "where": location,
                        "max_days_old": 2,
                        "sort_by": "date",
                        "content-type": "application/json",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"  [Adzuna] Error fetching '{query}' page {page}: {e}")
                break

            results = resp.json().get("results", [])
            if not results:
                break

            for r in results:
                location_name = r.get("location", {}).get("display_name", "")
                company_name = r.get("company", {}).get("display_name", "")

                salary_min = r.get("salary_min")
                salary_max = r.get("salary_max")
                salary_text = None
                if salary_min and salary_max:
                    salary_text = f"${salary_min:,.0f} - ${salary_max:,.0f}"
                elif salary_min:
                    salary_text = f"${salary_min:,.0f}+"

                # Detect remote from title/location/description
                text_lower = (r.get("title", "") + " " + location_name + " " + r.get("description", "")).lower()
                is_remote = "remote" in text_lower

                jobs.append(RawJob(
                    title=r.get("title", ""),
                    company=company_name,
                    location=location_name,
                    description=r.get("description", ""),
                    apply_link=r.get("redirect_url", ""),
                    source="Adzuna",
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_text=salary_text,
                    is_remote=is_remote,
                    date_posted=r.get("created"),
                ))

        print(f"  [Adzuna] '{query}' → {len(jobs)} jobs")
        return jobs
