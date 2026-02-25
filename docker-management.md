# IntellInbox Docker Management Guide

### Development Workflow

| Goal | Command | Description |
| :--- | :--- | :--- |
| **First Build** | `docker compose up --build` | Builds images from scratch and starts all services. |
| **Smart Start** | `docker compose up -d` | Starts containers in the background. Skips rebuilds if no changes detected. |
| **Check Status** | `docker ps` | Lists running containers and their health status. |
| **View Logs** | `docker compose logs -f` | Streams real-time logs from all services (Ctrl+C to stop viewing). |

---

### Debugging & Maintenance

**Enter a Container Shell** Use this to run commands directly inside the Linux environment of a specific service:
```bash
docker compose exec backend bash
```
Replace `backend` with `worker`, `db`, or `redis` to access the respective container.

**Database** Access Access the Postgres CLI without installing anything on your host machine:
```bash
docker compose exec db psql -U admin -d intellinbox_db
```
This connects you to the `intellinbox_db` database as the `admin` user

**Restart a Specific Service** Useful if you modified the worker logic and want to refresh just that piece:
```bash
docker compose restart worker
```
Replace `worker` with `backend`, `db`, or `redis` as needed.

### Shutdown & Cleanup
**Clean Stop** This will stop and remove containers, networks, and volumes created by `up`. The `-v` flag ensures that the Postgres data volume is also removed, giving you a completely fresh start next time.
```bash
docker compose down -v
```
if you want to refresh only the db data, you can remove the volume separately:
```bash
docker volume rm intellinbox_data
```
If you want to keep the data, simply omit the `-v` flag:
```bash
docker compose down
```
or hit Ctrl+C in the terminal where `docker compose up` is running to stop all services gracefully.

To not remove containers and volumes, use:
```bash
docker compose stop
```
This will stop the containers but keep them around for a quick restart later.