import time

from supermarkt.jobs import SearchJobStore


class ProgressEngine:
    def snapshot(self, postal_code, aldi_region, refresh, progress=None):
        progress(status="loading", progress=35, source="Testquelle", retailer="Lidl",
                 category="Backwaren", step="Laden", processed_sources=2,
                 total_sources=6, processed_products=42)
        return {"search_id": "job-result", "offers": [{}, {}]}, False


def test_search_job_reports_real_progress_and_completion():
    jobs = SearchJobStore(ProgressEngine())
    job_id = jobs.start("01067")
    for _ in range(100):
        job = jobs.get(job_id)
        if job["status"] == "completed":
            break
        time.sleep(0.01)
    assert job["progress"] == 100
    assert job["processed_products"] == 2
    assert job["search_id"] == "job-result"


def test_search_job_forwards_manual_aldi_choice():
    class RecordingEngine(ProgressEngine):
        seen = None

        def snapshot(self, postal_code, aldi_region, refresh, progress=None):
            self.seen = (postal_code, aldi_region)
            return super().snapshot(postal_code, aldi_region, refresh, progress)

    engine = RecordingEngine()
    jobs = SearchJobStore(engine)
    job_id = jobs.start("51643", "both")
    for _ in range(100):
        if jobs.get(job_id)["status"] == "completed":
            break
        time.sleep(0.01)
    assert engine.seen == ("51643", "both")


def test_search_job_reports_failures():
    class BrokenEngine:
        def snapshot(self, *args, **kwargs):
            raise RuntimeError("synthetic failure")

    jobs = SearchJobStore(BrokenEngine())
    job_id = jobs.start("01067")
    for _ in range(100):
        job = jobs.get(job_id)
        if job["status"] == "failed":
            break
        time.sleep(0.01)
    assert job["status"] == "failed"
    assert job["error"] == "synthetic failure"
