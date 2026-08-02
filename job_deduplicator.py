"""
Deduplicator for jobs scraped from multiple platforms
Identifies duplicate jobs and keeps the best version
"""

from typing import List, Dict
import difflib
from collections import defaultdict

class JobDeduplicator:
    """Identifies and deduplicates jobs from multiple platforms"""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Score (0-1) for title similarity match
        """
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, jobs: List[Dict]) -> tuple[List[Dict], List[Dict]]:
        """
        Deduplicate jobs from multiple platforms.

        Returns:
            (unique_jobs, duplicates_info)
        """
        if not jobs:
            return [], []

        unique_jobs = []
        seen_keys = set()
        duplicates_info = []

        # Group by similar titles
        groups = self._group_similar_jobs(jobs)

        for group in groups:
            if len(group) == 1:
                # No duplicates
                job = group[0]
                if job["job_key"] not in seen_keys:
                    unique_jobs.append(job)
                    seen_keys.add(job["job_key"])
            else:
                # Found duplicates - keep best
                best_job = self._select_best_job(group)
                if best_job["job_key"] not in seen_keys:
                    unique_jobs.append(best_job)
                    seen_keys.add(best_job["job_key"])

                # Record duplicate info
                for job in group:
                    if job["id"] != best_job["id"]:
                        duplicates_info.append({
                            "original": job,
                            "duplicate_of": best_job["id"],
                            "platforms": [j["platform"] for j in group]
                        })

        return unique_jobs, duplicates_info

    def _group_similar_jobs(self, jobs: List[Dict]) -> List[List[Dict]]:
        """Group jobs by title similarity"""
        groups = []
        used = set()

        for i, job1 in enumerate(jobs):
            if i in used:
                continue

            group = [job1]
            used.add(i)

            for j, job2 in enumerate(jobs[i+1:], start=i+1):
                if j in used:
                    continue

                similarity = self._title_similarity(
                    job1["title"],
                    job2["title"]
                )

                if similarity >= self.similarity_threshold:
                    if self._location_match(job1.get("location"), job2.get("location")):
                        group.append(job2)
                        used.add(j)

            groups.append(group)

        return groups

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        s = difflib.SequenceMatcher(None, title1.lower(), title2.lower())
        return s.ratio()

    def _location_match(self, loc1: str, loc2: str) -> bool:
        """Check if locations match"""
        if not loc1 or not loc2:
            return True  # Allow match if location not specified

        loc1 = loc1.lower()
        loc2 = loc2.lower()

        # Exact or contains match
        return loc1 in loc2 or loc2 in loc1 or loc1 == loc2

    def _select_best_job(self, group: List[Dict]) -> Dict:
        """
        Select best job from duplicates.

        Scoring:
        - Has salary: +10
        - Has description: +5
        - From known job platform (not company career site): +3
        """
        scores = {}

        for job in group:
            score = 0

            if job.get("salary"):
                score += 10

            if job.get("description") and len(job["description"]) > 50:
                score += 5

            # Prefer dedicated job platforms
            if job["platform"] in ["HospitalityJobsUK", "Caterer", "Indeed", "TotalJobs", "Reed"]:
                score += 3

            scores[job["id"]] = score

        # Return job with highest score
        best_id = max(scores, key=scores.get)
        return next(j for j in group if j["id"] == best_id)

    def get_dedup_stats(self, original_count: int, unique_count: int) -> Dict:
        """Get deduplication statistics"""
        return {
            "original_count": original_count,
            "unique_count": unique_count,
            "duplicates_removed": original_count - unique_count,
            "dedup_ratio": f"{((original_count - unique_count) / original_count * 100):.1f}%" if original_count > 0 else "0%"
        }
