"""
JobSpy fallback source.
Scrapes Indeed + Google Jobs. Only used when API sources return <5 new jobs.
Wrapped in try/except so failures don't crash the pipeline.
"""

from .base import JobSource, RawJob


class JobSpySource(JobSource):

    @property
    def name(self):
        return "JobSpy"

    def fetch(self, query, location="Atlanta, GA"):
        try:
            from jobspy import scrape_jobs
        except ImportError:
            print("  [JobSpy] python-jobspy not installed, skipping")
            return []

        jobs = []
        try:
            df = scrape_jobs(
                site_name=["indeed", "google"],
                search_term=query,
                google_search_term=f"{query} jobs near Atlanta, GA",
                location=location,
                results_wanted=30,
                hours_old=48,
                country_indeed="USA",
            )

            for _, row in df.iterrows():
                salary_text = ""
                salary_min = None
                salary_max = None
                if row.get("min_amount") and row.get("max_amount"):
                    try:
                        salary_min = float(row["min_amount"])
                        salary_max = float(row["max_amount"])
                        salary_text = f"${salary_min:,.0f} - ${salary_max:,.0f}"
                    except (ValueError, TypeError):
                        pass

                source = "Indeed" if "indeed" in str(row.get("site", "")).lower() else "Google Jobs"

                jobs.append(RawJob(
                    title=str(row.get("title", "")),
                    company=str(row.get("company", "")),
                    location=str(row.get("location", "")),
                    description=str(row.get("description", "")),
                    apply_link=str(row.get("job_url", "")),
                    source=source,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_text=salary_text or None,
                    is_remote=bool(row.get("is_remote", False)),
                    company_size=str(row.get("company_employees_label", "")) or None,
                    date_posted=str(row.get("date_posted", "")) or None,
                ))

        except Exception as e:
            print(f"  [JobSpy] Error scraping '{query}': {e}")

        print(f"  [JobSpy] '{query}' → {len(jobs)} jobs")
        return jobs
