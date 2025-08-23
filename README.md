# Tripmate
Tripmate Backend Rest API: A Smart group Travel Platform

📖 API Documentation
Already live TEST all enpoints here : https://tripmate-39hm.onrender.com/docs

## 🛠️ Tech Stack
- **Framework**: FastAPI (async)
- **Database**: PostgreSQL + SQLAlchemy ORM (async)
- **Auth**: JWT + OAuth2 (Google)
- **Caching**: Redis
- **Deployment**: Render (with CI/CD planned)
- **Others**: Alembic (migrations), Pydantic (schemas)

### Prerequisites
- Python 3.10+
- PostgreSQL
- Redis

### Setup
```bash
# Clone repo
git clone https://github.com/Tejashgawas/Tripmate.git
cd Tripmate

```
# Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload

## 📊 Performance Benchmark
TripMate backend was tested using **Locust** with authenticated GET endpoints for a general user role.

### Summary Metrics
- **Average Latency:** ~862 ms
- **P50 Latency:** ~120 ms (typical request)
- **P95 Latency:** ~390 ms (worst 5% of requests)
- **Max Latency:** ~1.2 s
- **Throughput:** ~52 req/sec on local environment
- **Error Rate:** 0%

### Endpoint Performance Highlights
| Endpoint | Avg Latency (ms) | P95 (ms) | Max (ms) | Notes |
|----------|------------------|----------|----------|-------|
| `/health` | 162 | 180 | 200 | Lightweight health check |
| `/trips/view-trips` | 779 | 820 | 840 | Cached endpoint |
| `/itinerary/trip/16` | 99 (miss) → 60 (hit) | — | — | 39% cache improvement |
| `/expenses/trips/1/settlements` | 1,206 | 1,240 | 1,260 | DB heavy, candidate for optimization |

### Caching Impact
Tested on:
- `/trips/view-trips`
- `/trips/16`
- `/itinerary/trip/16`

| Endpoint | Miss (ms) | Hit (ms) | Improvement |
|----------|-----------|----------|-------------|
| `/itinerary/trip/16` | 99.75 | 60.31 | **+39.54% faster** |
| `/trips/view-trips` | 30.40 | 50.58 | -66.41% |
| `/trips/16` | 50.08 | 50.16 | ~0% |

> Note: Negative/zero improvement indicates small payloads where caching overhead may outweigh DB retrieval time.
>

👨‍💻 Author

Built with ❤️ by Tejas Gawas

📜 License

MIT License
