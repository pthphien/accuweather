#  AccuWeather Automation Test

Selenium automation that collects daily weather forecast data from [AccuWeather](https://www.accuweather.com), stores it in CSV, logs each run, and generates two HTML reports: weather analytics and automation/QA data quality.

**Default location:** Ho Chi Minh City  
**Default schedule:** every 60 minutes (`scheduler.py`)

---

## 1. What it does

Each successful run:

1. Opens AccuWeather, searches for the target city, and navigates to the **10-day** daily forecast page.
2. Scrapes every visible daily card: date, period, weather, high/low temperature, RealFeel, and humidity.
3. Converts Celsius values from the site to Fahrenheit and validates ranges.
4. Merges new rows into `data/daily_forecast.csv`, dropping forecast dates older than the retention window.
5. Appends a passed run to `data/execution_log.json`.
6. Regenerates `data/weather_summary_report.html` and `data/automation_qa_report.html`.

   **`weather_summary_report.html`** — Weather analytics from collected forecast data: coverage (dates, periods, collection window), alert summary (heavy rain, thunderstorm, extreme heat, high humidity), condition distribution, temperature stats and daily ranges, weather by time period, humidity analysis, and forecast changes when period or weather shifts across runs for the same date.

   **`automation_qa_report.html`** — Automation execution and data quality: run success rate and overview, overall QA score (completeness, validity, consistency), plus detail sections for execution timeline, performance timing, error breakdown, field completeness, temperature/period validation, high-vs-low consistency, and duplicate row checks.

On failure, `scheduler.py` records a failed run with classified error counts before continuing the schedule.

---

## 2. Installation

**Requirements:** Python 3.9+

```bash
cd accuweather
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies:

- `pytest` — test runner
- `selenium` — browser automation
- `webdriver-manager` — automatic ChromeDriver management

---

## 3. How to run

### 3.1 Pytest

Headless (default):

```bash
python3 -m pytest tests/test_accuweather.py
python3 -m pytest tests/test_accuweather.py -m smoke
```

Visible browser:

```bash
python3 -m pytest tests/test_accuweather.py --headed
```


### 3.2 Scheduler (continuous collection)

Every 60 minutes (default):

```bash
python3 scheduler.py
```

> **Note:** The scheduler pauses while the machine is asleep and resumes when it wakes.

Run once and exit:

```bash
python3 scheduler.py --once
```

Custom interval (e.g. every 10 minutes):

```bash
python3 scheduler.py --interval 10
```

Show browser window:

```bash
python3 scheduler.py --headed
```

Keep the machine awake while the scheduler runs:

**macOS**

```bash
caffeinate -i python3 scheduler.py
```

**Windows (PowerShell)** — prevents idle sleep for the duration of the run (no permanent power-setting changes):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {
  Add-Type -Name Awake -Namespace System -MemberDefinition '
    [DllImport(\"kernel32.dll\")] public static extern uint SetThreadExecutionState(uint esFlags);
  '
  [System.Awake]::SetThreadExecutionState(0x80000003) | Out-Null
  try { python scheduler.py } finally { [System.Awake]::SetThreadExecutionState(0x80000000) | Out-Null }
}"
```




### Scheduler management

Find a running process:

```bash
pgrep -fl scheduler.py
```

Stop it:

```bash
kill <PID>
```

Force stop if needed:

```bash
kill -9 <PID>
```

### 3.3 GitHub Actions (every 60 minutes)

Run in the cloud on a fixed **60-minute** schedule (same as `DEFAULT_INTERVAL_MINUTES` in `config.py`). Workflow: [`.github/workflows/accuweather.yml`](.github/workflows/accuweather.yml)

| Trigger | When it runs |
|---------|----------------|
| `schedule` | **Hourly** (`0 * * * *` UTC — at :00 each hour; may be delayed, see below) |
| `workflow_dispatch` | Manual run from the **Actions** tab |
| `push` / `pull_request` | On code changes to `main` (not on `data/` only commits) |

**Enable the 60-minute schedule**

1. Commit and push `.github/workflows/accuweather.yml` to the **`main`** branch.
2. On GitHub: **Settings → Actions → General** → select **Allow all actions and reusable workflows** → **Save**. (This is permissions only — not where workflows are listed.)
3. After the first push, the schedule is active on `main`. The first scheduled run may take **15–30 minutes** to appear.
4. Optional — run manually:
   - Open the top nav tab **Actions** (between **Agents** and **Projects**, not **Settings**)
   - In the left sidebar, click **AccuWeather Automation**
   - Click **Run workflow** → **Run workflow**
   - Direct link: `https://github.com/pthphien/accuweather/actions/workflows/accuweather.yml`

Each run installs Python 3.11, Chrome, dependencies, then executes:

```bash
python -m pytest tests/test_accuweather.py -m smoke
```

> **Timezone:** All `Executed At` / `execution_time` values and report footers are stored in **UTC** (same on your machine and GitHub Actions). GitHub cron runs at **:00 each hour UTC** (e.g. 07:00 UTC = 14:00 in Ho Chi Minh City, GMT+7).

#### 3.4 Schedule reliability (important)

The workflow **is scheduled**, but GitHub does **not** guarantee exact hourly runs on the free plan.

| What you might expect | What actually happens |
|-----------------------|------------------------|
| Run every 60 minutes from last run | Runs at **:00 UTC** each hour (fixed clock times) |
| Always on time | Runs can be **delayed 1–6+ hours** when GitHub load is high |
| Missed run is retried | **No catch-up** — a skipped hour is not run twice later |


**If you need strict every-60-minute collection**, use local `scheduler.py`, an always-on VM, **Jenkins** (cron trigger on an always-on agent — reliable wall-clock hourly runs), or an external cron service that triggers **Run workflow** via the GitHub API — GitHub Actions alone is not reliable enough for precise hourly timing.

#### Where are the data files and reports?

**On `main` (schedule, manual run, or code push):** after a **successful** run, reports and data are saved **in the repository** under `data/` — same as running locally. Browse them on GitHub:

| File | Path in repo |
|------|----------------|
| Forecast CSV | `data/daily_forecast.csv` |
| Execution log | `data/execution_log.json` |
| Weather report | `data/weather_summary_report.html` |
| QA report | `data/automation_qa_report.html` |

