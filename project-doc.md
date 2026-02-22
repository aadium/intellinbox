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
* The API has one main **POST** endpoint to receive emails and two **GET** endpoints to check the status and retrieve the analysis.
* When an email is received, we create a new record in the `Email` table with the status "Pending" and then push the `email_id` to Redis for the worker to process.
* The **GET** endpoints allow clients to check the status of an email and retrieve the analysis once it's completed.
* The **PUT** endpoint allows clients to update the status of an email, which can be useful for error handling or manual overrides.
* The **DELETE** endpoint allows clients to remove an email and its analysis from the database, which can be useful for cleanup or testing purposes.

## `/worker`
### `Dockerfile`
The worker sits in a loop, watching Redis for new `email_id` tasks.

### `worker.py`
* The worker uses Celery to manage background tasks. It connects to Redis as the broker and PostgreSQL as the backend for storing results.
* When a new `email_id` is received from Redis, the worker retrieves the corresponding email from the database, processes it with BERT and T5, and then updates the database with the results.
* The worker also updates the email's status to "Processing" when it starts and "Completed" or "Failed" when it finishes, allowing the API to provide real-time status updates to clients.