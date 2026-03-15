"""
Remotive API adapter.
Free, no API key required. Remote-only job listings.
Docs: https://remotive.com/api/remote-jobs
"""

import requests
from .base import JobSource, RawJob


class RemotiveSource(JobSource):
    BASE_URL = "https://remotive.com/api/remote-jobs"

    @property
    def name(self):
        return "Remotive"

    def fetch(self, query, location="Atlanta, GA"):
        try:
            resp = requests.get(
                self.BASE_URL,
                params={"search": query, "limit": 30},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [Remotive] Error fetching '{query}': {e}")
            return []

        jobs = []
        for j in resp.json().get("jobs", []):
            candidate_location = j.get("candidate_required_location", "")
            # Skip if location is restricted to non-US
            if candidate_location and "usa" not in candidate_location.lower() \
               and "united states" not in candidate_location.lower() \
               and "worldwide" not in candidate_location.lower() \
               and "anywhere" not in candidate_location.lower() \
               and "north america" not in candidate_location.lower():
                continue

            job_type_raw = j.get("job_type", "")
            job_type = job_type_raw.replace("_", " ").title() if job_type_raw else None

            jobs.append(RawJob(
                title=j.get("title", ""),
                company=j.get("company_name", ""),
                location=candidate_location or "Remote",
                description=j.get("description", ""),
                apply_link=j.get("url", ""),
                source="Remotive",
                salary_text=j.get("salary", "") or None,
                job_type=job_type,
                is_remote=True,
                date_posted=j.get("publication_date"),
            ))

        print(f"  [Remotive] '{query}' → {len(jobs)} jobs")
        return jobs
