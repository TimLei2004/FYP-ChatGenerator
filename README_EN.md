# Dorm Bot Generator

A Python toolkit for generating test user profiles, automating login to a dorm advisory website, sending batch questions, and syncing Q&A records back to Supabase.

## 1. Features

- Generate test personas and structured profiles with DashScope.
- Automatically create test accounts and store them in the `bot_profile` table.
- Use Selenium to log in and auto-fill the first-time preference form.
- Generate multi-round questions and send them to the chat page.
- Poll answers from the database and write them into `bot_histories`.
- Support both single-account and parallel multi-account testing.

## 2. Project Structure

- `GenerateMessage.py`: Prompts, profile generation, question generation, and Supabase query helpers.
- `Helper.py`: Cleans and parses JSON returned by the model.
- `SeleniumFrame.py`: Selenium startup and reusable form-filling utilities.
- `Test.py`: End-to-end automation flow (login, form fill, Q&A, data sync).
- `UpdateBotHistories.py`: Syncs chat logs into structured QA records.
- `requirements.txt`: Python dependencies.
- `bot_histories.csv`: Sample/exported data.
- `Testing.ipynb`: Notebook for debugging and experiments.

## 3. Requirements

- macOS / Linux / Windows (Chrome must be installed)
- Python 3.10+

Using a virtual environment is recommended.

## 4. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Environment Variables

Create a `.env` file in the project root (or export variables in your shell):

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_or_api_key
BAILIAN_API_KEY=your_dashscope_api_key
```

These values are used for:

- Supabase read/write operations
- DashScope text generation

## 6. Supabase Table Dependencies

This project currently expects the following tables:

- `bot_profile`
- `profiles`
- `chat_logs`
- `bot_histories`

It also relies on the Supabase Auth Admin API to create test users.

## 7. Quick Start

### 7.1 Single Account Test

```python
from Test import start_a_test

start_a_test("test001@example.com", auto=True)
```

Notes:

- If the account does not exist, it will be created automatically.
- On first login, if `form_preferences` is empty, the form is auto-filled and submitted.
- The default target is around 10 rounds of conversation (based on history length).

### 7.2 Parallel Multi-Account Test

```python
from Test import start_tests_parallel

emails = [
    "test001@example.com",
    "test002@example.com",
    "test003@example.com",
]

start_tests_parallel(emails, auto=True, max_workers=2)
```

### 7.3 Manual Mode

```python
from Test import start_a_test

start_a_test("manual001@example.com", auto=False)
```

When `auto=False`, you can input test comments before each round, and manually review generated profiles during account creation.

## 8. Common Utility Functions

### 8.1 Create a Test Account

```python
from GenerateMessage import generate_test_account

generate_test_account("newtest@example.com", auto=True)
```

### 8.2 Query Chat Logs and Profiles by User

```python
from GenerateMessage import search_by_uid, get_email_to_uid

uid = get_email_to_uid()["test001@example.com"]
chat_logs, profiles = search_by_uid(uid)
```

### 8.3 Sync to bot_histories

```python
from UpdateBotHistories import update_one_bot_histories

update_one_bot_histories("test001@example.com")
```

## 9. FAQ

### 9.1 Selenium Starts Slowly or Gets Stuck

The project uses `webdriver_manager` by default to start ChromeDriver, which helps avoid Selenium Manager startup stalls in some environments.

### 9.2 Password Prompts Interrupt Automation

`Test.py` already disables Chrome password manager and password leak detection to reduce pop-up interruptions.

### 9.3 Field Matching Fails

`SeleniumFrame.py` includes a field alias map. If frontend labels change, add or adjust aliases in `_build_field_aliases`.

## 10. Notes

- `GenerateMessage.py` contains a hardcoded `app_id`; update it if you need a different DashScope application.
- `get_email_to_profile()` currently uses `eval` for deserialization. Replacing it with safe JSON parsing is recommended.
- The workflow depends heavily on external services (Supabase, DashScope, target website), so verify network access and keys first.

## 11. Dependency Versions

See `requirements.txt` for source of truth:

- supabase==2.3.4
- dashscope>=1.20.0
- python-dotenv==1.0.0
- selenium>=4.20.0
- webdriver-manager>=4.0.2
