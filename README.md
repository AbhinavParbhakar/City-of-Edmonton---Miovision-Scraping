# Miovision Study Report Downloader

## Overview

This repository contains a Python-based automation tool that:

1. Authenticates into Miovision DataLink using Playwright  
2. Scrapes study types and study IDs for a specified year range  
3. Downloads each study's report as an `.xlsx` file  
4. Saves reports to a specified local directory  

The script supports configurable time aggregation intervals and parallelized downloads.

---

## Repository Structure

```
.
├── main.py
├── auth_provider.py
├── miovision_info_provider.py
├── report_downloads_provider.py
├── existing_file_validation.py
├── logger_provider.py
```

### File Responsibilities

- **main.py**  
  Entry point. Handles CLI arguments, loads environment variables, and orchestrates scraping and downloads.

- **auth_provider.py**  
  Performs Playwright login and saves authenticated browser session state.

- **miovision_info_provider.py**  
  Scrapes study types and study IDs from Miovision DataLink.

- **report_downloads_provider.py**  
  Downloads study reports as `.xlsx` files using authenticated cookies.

- **existing_file_validation.py**  
  Prevents duplicate downloads by checking if a file already exists.

- **logger_provider.py**  
  Configures logging output (`playwright_scraping.log`).

---

## Requirements

- Python 3.10+
- Internet access to https://datalink.miovision.com
- Valid Miovision credentials

---

# Installation (Using uv)

This project uses **uv** for reproducible dependency management.

The receiving organization should:
- Install uv
- Compile a pinned requirements file
- Sync environment from that pinned file

Assume uv is NOT installed initially.

---

## 1) Install uv

### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell)
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Restart terminal and verify:

```bash
uv --version
```

---

## 2) Create Virtual Environment

From repo root:

```bash
uv venv
```

Activate environment:

### macOS/Linux
```bash
source .venv/bin/activate
```

### Windows
```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3) Create requirements.in (if not already present)

Create file in repo root named `requirements.in`:

```
playwright
python-dotenv
requests
beautifulsoup4
lxml
```

---

## 4) Compile pinned dependencies

This generates a fully pinned reproducible environment file.

```bash
uv pip compile requirements.in -o requirements.out
```

---

## 5) Sync environment from pinned file

```bash
uv pip sync requirements.out
```

---

## 6) Install Playwright browser

```bash
playwright install chromium
```

---

# Environment Configuration

Create a `.env` file in repository root:

```
MIOVISION_USERNAME=your_username_here
MIOVISION_PASSWORD=your_password_here
```

---

# Running the Script

The script uses positional CLI arguments.

## Command Format

```bash
python main.py <auth_session_json> <output_folder> <start_year> <end_year> "<time_interval>"
```

---

# CLI Arguments (Detailed)

## 1. auth_session_json
Path to Playwright session JSON file.

Must:
- End with `.json`
- Will be created automatically if not present

Example:
```
./auth_session.json
```

---

## 2. output_folder
Directory where downloaded `.xlsx` reports will be stored.

- Created automatically if not present

Example:
```
./downloads
```

---

## 3. start_year
Starting year for scraping.

Format:
```
YYYY
```

Example:
```
2023
```

---

## 4. end_year
Ending year for scraping.

Must be:
```
>= start_year
```

Example:
```
2024
```

---

## 5. time_interval
Aggregation interval for downloaded reports.

Must match EXACTLY one of:

```
"1 minute"
"5 minutes"
"10 minutes"
"30 minutes"
"1 hour"
```

Case and spacing must match exactly.

---

# Example Run

```bash
python main.py ./auth_session.json ./downloads 2023 2024 "5 minutes"
```

This will:
- Authenticate into Miovision
- Scrape studies from 2023–2024
- Download all reports
- Save into ./downloads

---

# Output

Saved files format:

```
<output_folder>/<STUDY_TYPE>-<STUDY_ID>.xlsx
```

Example:
```
downloads/ATR-123456.xlsx
```

Logs written to:
```
playwright_scraping.log
```

---

# Changing the Output Destination (S3 / GCS / Other)

By default, reports are saved to the local filesystem under `<output_folder>`.

If the receiving organization wants to store outputs in **Amazon S3**, **Google Cloud Storage**, or another destination, this can be changed by modifying the code to implement a storage/output interface (e.g., a `StorageProvider` / `OutputSink`) and swapping the local write implementation with a cloud-backed implementation.

Suggested approach:

- Define an interface with methods such as:
  - `exists(object_name: str) -> bool`
  - `write_bytes(object_name: str, content: bytes) -> None`
- Implement:
  - `LocalStorageProvider` (current behavior)
  - `S3StorageProvider`
  - `GCSStorageProvider`
- Update `report_downloads_provider.py` to write via the provider rather than directly to disk.

This allows:
- Local downloads (current)
- S3 uploads instead of local writes
- GCS uploads instead of local writes
- Future extension to Azure Blob, etc.

---

# How It Works (Internals)

1. Launches headless Chromium via Playwright
2. Authenticates and saves session cookies
3. Iterates month-by-month across year range
4. Scrapes study metadata
5. Downloads report via authenticated HTTP request
6. Saves XLSX to configured output destination
7. Skips already-downloaded files
8. Parallelizes downloads using multiprocessing

---

# Operational Notes

- Parallel downloads use CPU core count
- Can reduce concurrency in main.py if rate-limited
- Automatically retries failed downloads
- Skips files that already exist
- Credentials must remain secure

---

# Troubleshooting

## uv not found
Restart terminal after install or run:
```bash
uv --version
```

## Playwright errors
```bash
playwright install chromium
```

## Invalid CLI arguments
Check:
- Session file ends with .json
- Years numeric
- end_year >= start_year
- Valid time interval string

## Downloads failing
- Verify .env credentials
- Confirm Miovision access
- Check playwright_scraping.log

---

# Security Considerations

- Never commit `.env`
- Restrict access to session JSON
- Ensure output folder permissions (or bucket permissions for cloud storage)
- Rotate credentials if shared externally

---

# Handoff Checklist (Receiving Organization)

1. Install uv
2. uv venv
3. Activate environment
4. uv pip compile requirements.in -o requirements.out
5. uv pip sync requirements.out
6. playwright install chromium
7. Create .env with credentials
8. Run small test first (1 year)
9. Confirm downloads + logs working
10. (Optional) Implement cloud output destination interface if required (S3/GCS/etc.)

---

# Optional Improvements

- Docker container
- Config file instead of CLI args
- Structured logging
- Retry/backoff tuning
- CI/CD integration
- Configurable concurrency
- Add pluggable storage/output interface (local + S3 + GCS)

---

# Maintainer Notes

Provided as-is for internal automation use.  
Ensure proper credential handling and operational security practices.