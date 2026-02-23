## `docker-compose.yml`

### 1. The Database Service (`db`)
* **Image:** Uses the official `postgres:15-alpine` (Alpine is much smaller/faster).
* **Ports:** Maps `5434:5432` so the API can connect to it. Note that we use `5434` on the host to avoid conflicts with any local Postgres instances.
* **Environment:** Pulls `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` from the `.env` file.
* **Volumes:** Maps a local directory (`./postgres_data`) to `/var/lib/postgresql/data`. This ensures the emails don't vanish when the container is stopped
* **Healthcheck:** This is vital. We define the `pg_isready` command so other services know exactly when the DB is ready to talk.

### 2. The Message Broker (`redis`)
* **Image:** `redis:7-alpine`.
* **Purpose:** This acts as the "waiting room" for the emails. The API drops an ID here, and the Worker picks it up.

### 3. The Backend API (`api`)
* **Build:** This points to the `./backend` folder where the `Dockerfile` lives.
* **Environment:** It needs the `DATABASE_URL` and `REDIS_URL`.
* **Ports:** Maps `8000:8000` so Swagger UI (`/docs`) can be accessed from the browser.
* **Depends On:** This is set up to depend on `db` with the `service_healthy` condition.

### 4. The ML Worker (`worker`)
* **Build:** Points to the `./worker` folder.
* **Command:** This container won't run a web server; its "entrypoint" will be the Celery worker command.
* **Volumes:** **This is the most important part.** Maps the local `./models` folder to the container's cache directory (usually `~/.cache/huggingface`).
* *Why?* When the worker runs BERT for the first time, it will download ~500MB. Without this volume, we’d have to redownload it every time we rebuild the container.
* **Depends On:** `redis` and `db`.

### 5. Portainer
* **Image:** `portainer/portainer-ce:latest`.
* **Purpose:** A web UI to manage Docker containers. It’s optional but highly recommended for monitoring and debugging.
* **Ports:** Maps `9443:9443` for access.

## `/backend`
### `Dockerfile`
* **Dependency Layering:** We copy only the requirements.txt first and install it. Docker will skip the long installation step during the next build if the dependencies haven't changed, which speeds up development.
* **Environment Variables:** We set PYTHONUNBUFFERED=1 so logs appear in the Linux terminal in real-time.
* **The User:** It is better not to run the app as "root" for security.

### `database.py`
* Define the database URL.
* Create an engine instance. The engine manages database connections.
* Then, create a `SessionLocal` class. Each request will get its own session.
* Define the Base class here so models.py can import it.
* `get_db` manages the lifecycle of a database connection so we don't leak memory or leave connections open.

### `schema.py`
1. **The Relationship:**
One email will have one analysis. This is a **One-to-One** relationship.
2. **Handling the Status:**
The `status` column on the Email table is the "heartbeat" of the pipeline.

#### Key Columns
##### **Table 1: `Email` (The Source)**
* **`id`**: Integer, Primary Key.
* **`sender`**: String.
* **`subject`**: String.
* **`body`**: Text (this holds the full content for BERT/T5 to read).
* **`received_at`**: DateTime (defaulting to the current time).
* **`status`**: String (Pending/Processing/Completed/Failed).

##### **Table 2: `Analysis` (The AI Output)**
* **`id`**: Integer, Primary Key.
* **`email_id`**: Integer, Foreign Key (links back to `emails.id`).
* **`priority_score`**: Float (The BERT output, e.g., $0.95$).
* **`summary`**: Text (The T5 output).
* **`category`**: String (e.g., "Work", "Personal", "Spam").

### `models.py`
* This is where we define the SQLAlchemy models that correspond to our database tables.
* Each class (Email and Analysis) inherits from `Base` and defines the columns as class attributes.
* The `relationship` function is used to link the two tables together, allowing us to easily access the analysis from an email and vice versa.

### `main.py`
* This is the entry point for the FastAPI application.
* We define the API routes under the `/routes` directory, which keeps our code organized.

#### Key Routes
#### **Email Management (`/emails`)**

1. **POST `/emails/**`: Accepts raw email data (sender, subject, body). It creates a new record with a "Pending" status and dispatches the `tasks.analyze_email` task to Redis for immediate AI processing.
2. **GET `/emails/**`: Retrieves a list of all emails, ordered by the most recently received. Supports pagination via `skip` and `limit` parameters.
3. **GET `/emails/{email_id}**`: Fetches a single email record. Because of the database relationship, this includes the linked AI analysis (summary, priority, category) if the task is complete.
4. **PATCH `/emails/{email_id}/analysis**`: Used to rerun AI analysis. It resets the email status to "Processing," deletes the existing analysis record, and re-triggers the `tasks.analyze_email` worker task.
5. **DELETE `/emails/{email_id}**`: Removes an email and its associated analysis from the database.

#### **Inbox Management (`/inboxes`)**

6. **POST `/inboxes/**`: Registers a new IMAP account. It encrypts the password before storage and triggers the **`tasks.setup_inbox`** task, which performs the "Bootstrap" fetch of historical emails from the past week.
7. **GET `/inboxes/**`: Returns a list of all monitored email accounts and their current active status.
8. **POST `/inboxes/syncall**`: A global trigger that iterates through all active inboxes and dispatches a **`tasks.sync_inbox`** task for each. This is used for "Incremental" syncing of unseen emails.
9. **POST `/inboxes/{inbox_id}/sync**`: Manually triggers an incremental sync for a specific inbox by ID.
10. **PATCH `/inboxes/{inbox_id}/status**`: Toggles whether an inbox is active. If inactive, it will be skipped during `syncall` operations.
11. **DELETE `/inboxes/{inbox_id}**`: Permanently removes an inbox and all data associated with it from the system.

## `/worker`
### `Dockerfile`
The worker container is built on a Python 3.11 image, pre-loading `PyTorch` and `Transformers`. It sits in a continuous loop, watching the Redis queue for task signals. It is designed to be stateless, relying on the database for persistent storage and a local volume for model caching.

### `fetcher.py` (The Retrieval Engine)
This module handles the low-level IMAP communication. It is responsible for logging into mail servers, searching for relevant messages, and extracting clean text.

* **Heuristic Filtering (`is_promotional`)**: Before an email is even saved, it is checked for marketing "DNA."
* **Headers**: Detects the `List-Unsubscribe` header used by nearly all legitimate newsletters and bulk senders.
* **Keywords**: Scans for "unsubscribe," "view in browser," or "privacy policy."
* **Body Logic**: If the email is relatively short and contains "opt out" triggers, it is flagged to prevent wasting AI resources on "garbage" data.

* **Safe Extraction**:
* **Decoding**: Safely decodes RFC822 headers and handles various character encodings (UTF-8, Latin-1) with error replacement.
* **Multipart Handling**: Specifically targets `text/plain` parts of emails to ensure the AI receives clean text rather than raw HTML/CSS code.
* **Body Guard**: Only returns emails that contain actual text content after stripping whitespace.

### `tasks.py` (The AI Intelligence Layer)
This is the "brain" of the application. It defines how the worker process initializes and handles asynchronous jobs.

* **Model Initialization (`init_worker`)**:
* Uses the `@worker_process_init` signal to load models into memory **once** when a worker process starts. This prevents the system from reloading gigabytes of weights for every single email.
* **Sentiment**: RoBERTa classifies the emotional tone.
* **Summary**: T5 generates a condensed version of the body.
* **Priority**: BART (Zero-Shot) categorizes the email against custom labels ("Urgent," "Social," "Neutral") without needing specific training on your data.

* **The Dual-Sync Strategy**:
1. **`setup_inbox_task` (Bootstrap Mode)**: Triggered when a new inbox is added. It uses the `SINCE "{date}"` IMAP command to pull all emails from the **last 7 days**, ensuring the user doesn't start with an empty dashboard.
2. **`sync_inbox_task` (Incremental Mode)**: The lightweight standard sync. It looks only for `UNSEEN` messages, acting as the daily driver to keep the inbox current.

* **Atomic Analysis (`analyze_email`)**:
* Processes emails one by one.
* **Failure Resilience**: Uses a robust `try-except-finally` block. If the AI model crashes (due to memory or formatting), the database status is automatically set to `FAILED`, and the transaction is rolled back to prevent data corruption.
* **Context Truncation**: Intelligently slices the email body (first 1024 characters) to fit within the "context window" of the Transformer models, ensuring consistent performance.