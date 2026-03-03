import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_job_invalid_url(client):
    r = await client.post("/api/v1/jobs", json={"youtube_url": "not-a-url"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_job_returns_202(client):
    payload = {"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    r = await client.post("/api/v1/jobs", json=payload)
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_get_nonexistent_job(client):
    r = await client.get("/api/v1/jobs/doesnotexist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_download_not_complete(client):
    payload = {"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    r = await client.post("/api/v1/jobs", json=payload)
    job_id = r.json()["job_id"]
    r2 = await client.get(f"/api/v1/jobs/{job_id}/download")
    assert r2.status_code == 409