## `docker-compose.yml`

### 1. The Database Service (`db`)
* **Image:** Uses the official `postgres:15-alpine` (Alpine is much smaller/faster).
* **Environment:** Pulls `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` from the `.env` file.
* **Volumes:** Maps a local directory (e.g., `./postgres_data`) to `/var/lib/postgresql/data`. This ensures the emails don't vanish when the container is stopped
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

## `/backend/Dockerfile`
* **Dependency Layering:** We copy only the requirements.txt first and install it. This is a Docker "best practice" it means if you change your code but not your libraries, Docker will skip the long installation step during the next build.
* **Environment Variables:** We set PYTHONUNBUFFERED=1 so logs appear in the Linux terminal in real-time.
* **The User:** It is better not to run the app as "root" for security.

## `/worker/Dockerfile`
The worker's job is different from the API. It doesn't wait for HTTP requests; it sits in a loop, watching Redis for new `email_id` tasks.

