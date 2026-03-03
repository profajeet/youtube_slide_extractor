# YouTube Slide Extractor

A FastAPI-based application for extracting slides from YouTube videos.

## Project Structure

```
youtube_slide_extractor/
├── app/                          # Main application code
│   ├── main.py                   # FastAPI application entry point
│   ├── api/v1/                   # API v1 routes
│   │   ├── router.py             # Main router
│   │   └── endpoints/            # API endpoints
│   │       ├── jobs.py           # Job management endpoints
│   │       └── download.py       # Download endpoints
│   ├── core/                     # Core configuration
│   │   ├── config.py             # Application settings
│   │   └── logging.py            # Logging setup
│   ├── models/                   # Data models
│   │   └── job.py                # Job model
│   ├── services/                 # Business logic services
│   │   ├── extractor.py          # Slide extraction service
│   │   ├── job_store.py          # Job storage service
│   │   └── worker.py             # Background worker
│   └── utils/                    # Utility functions
│       └── file_utils.py         # File operations
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest configuration
│   ├── test_jobs.py              # Job management tests
│   └── test_extractor.py         # Extractor tests
├── .env.example                  # Example environment variables
├── requirements.txt              # Project dependencies
├── Dockerfile                    # Docker configuration
└── README.md                     # This file
```

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Running the Application

### Local Development

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Docker

```bash
docker build -t youtube-slide-extractor .
docker run -p 8000:8000 youtube-slide-extractor
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/v1/jobs/` - List all jobs
- `GET /api/v1/jobs/{job_id}` - Get a specific job
- `POST /api/v1/jobs/` - Create a new job
- `GET /api/v1/download/{job_id}` - Download extracted slides

## Testing

Run the test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app
```

## Configuration

Configure the application using environment variables in the `.env` file:

- `YOUTUBE_API_KEY` - YouTube API key for video access
- `DEBUG` - Enable debug mode
- `OUTPUT_DIR` - Directory for saving extracted slides
- `LOG_LEVEL` - Logging level

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Commit and push
5. Create a pull request

## License

MIT
