# Mongo init script (init-mongo.js) — documentation

This document explains what the `init-mongo.js` script does, why it is used, how it runs inside the MongoDB Docker image, and how to verify or re-run it. It also documents each line of the file and where the methods come from.

File: /home/adraoui/Desktop/buy-01/product-service/docker/mongo/init-mongo.js

## Purpose

The init script creates an application database user and assigns roles during the initial bootstrap of the MongoDB container. It is intended to be run by the official `mongo` Docker image during the initial container startup when the data directory is empty.

## How the script is executed

- The official `mongo` Docker image executes any script placed in `/docker-entrypoint-initdb.d/` when the container initializes a fresh database (i.e., an empty data directory).
- The script is evaluated by `mongosh` (the modern MongoDB shell), which exposes a JS runtime where `process.env`, `db`, and shell helper methods are available.
- In our docker-compose.yml the script is mounted to that folder; when the container starts for the first time it will run.

## File (line-by-line explanation)

1. const dbName = process.env.MONGO_DATABASE;
   - Reads the `MONGO_DATABASE` environment variable into `dbName`.
   - `process.env` is the Node.js-style environment object available in `mongosh`.

2. const username = process.env.MONGO_USERNAME ;
   - Reads the `MONGO_USERNAME` environment variable into `username`.

3. const password = process.env.MONGO_PASSWORD ;
   - Reads the `MONGO_PASSWORD` environment variable into `password`.

5. const db = db.getSiblingDB(dbName);
   - `db` here is the shell-provided Database object (current DB context).
   - `getSiblingDB(name)` returns a Database instance for `name` (it does not change the global `db` context permanently, it simply returns the DB object for the requested database).
   - Source: MongoDB shell API (mongosh).

7. const existingUser = db.getUser(username);
   - Queries the database for an existing user with `username`.
   - `getUser()` is a MongoDB shell helper that looks up a user in the database's user store.

8. if (!existingUser) {
   - Checks if the user does not exist so the script remains idempotent.

9-16. db.createUser({ user: username, pwd: password, roles: [...] });
   - Creates a new user with the provided username/password and assigns roles.
   - `createUser()` is a MongoDB shell Database method. The `roles` array contains standard MongoDB roles (e.g. `readWrite`, `dbAdmin`).

## Where these methods come from

- `process.env` — provided by the JS runtime (Node-style) available in `mongosh`.
- `db`, `db.getSiblingDB()`, `db.getUser()`, `db.createUser()` — these are part of the MongoDB shell API (mongosh / legacy mongo shell). They wrap server commands (user creation, user lookup) and are documented in MongoDB server & shell docs.

## Execution lifecycle & behavior

- When: Run during the container bootstrap phase (only when the data directory is empty on first startup).
- How often: Only on first initialization by default. If the docker volume already contains data, the init scripts are skipped.
- Ordering: Files in `/docker-entrypoint-initdb.d/` are executed in lexicographic order.
- Idempotency: The script checks for user existence (`db.getUser()`) before creating one, making it safe if accidentally executed more than once.

## Environment configuration

- The script reads values from environment variables. Provide them through Docker Compose `env_file` or `environment`.
- Example `.env` entries used in this project:

```
MONGO_DATABASE=product_service_db
MONGO_USERNAME=product_service
MONGO_PASSWORD=VeryStrongPasswordYouShllNotPass
MONGO_ROOT_USERNAME=root
MONGO_ROOT_PASSWORD=rootpass
MONGODB_URI=mongodb://product_service:VeryStrongPasswordYouShllNotPass@localhost:27018/product_service_db?authSource=product_service_db
```

- In the repository, `docker-compose.yml` mounts `init-mongo.js` and uses `env_file: - ./.env` so those variables are available to the container.

## How to verify the user and DB were created

- Check container logs:

```
docker logs product-service-mongodb
```

- Inspect users and DB via `mongosh` inside the container (using the root/admin account or the app user once created):

```
# as root (created via MONGO_INITDB_ROOT_* env vars)
docker exec -it product-service-mongodb mongosh -u root -p rootpass --authenticationDatabase admin --eval "db.getSiblingDB('product_service_db').getUsers(); db.getMongo().getDBNames();"

# as the app user
docker exec -it product-service-mongodb mongosh --username "$MONGO_USERNAME" --password "$MONGO_PASSWORD" --authenticationDatabase "$MONGO_DATABASE" --eval "db.runCommand({ ping: 1 }); db.getUsers();"
```

You should see the created user in the output and the `ping` command should return `{ ok: 1 }`.

## How to force the script to run again (destructive)

The init scripts run on empty data directories only. To re-run them you must remove the data volume (this deletes the database):

```
docker compose down -v
docker compose up -d
```

The init scripts will run again because the data volume is recreated.

## Best practices and recommendations

- Keep `.env` out of version control (it can contain secrets). Ensure `.gitignore` excludes it.
- Validate required env vars at the top of the script and print meaningful console messages (use `console.log()`), e.g.:

```js
if (!process.env.MONGO_DATABASE || !process.env.MONGO_USERNAME || !process.env.MONGO_PASSWORD) {
  console.error('Missing required MONGO_* environment variables');
  throw new Error('Missing required MONGO_* environment variables');
}
```

- Add console.log statements so container logs show when the script created or skipped user creation.
- If you need to update credentials on an existing DB, prefer an administrative migration step rather than relying on init scripts (init scripts only run on first boot).
- For maximum compatibility with older `mongo` images (which use the legacy shell), a host-side templating approach (e.g. `envsubst`) can be used instead of `process.env` inside the script.

## Troubleshooting

- `Authentication failed` when trying to use the app user: check that the user exists (see `db.getUsers()`), verify `MONGO_DATABASE` was used as the authentication DB, and ensure the app's `MONGODB_URI` uses `authSource=<db>` if required.
- Script didn’t run: confirm the data volume was empty before starting the container, and that the script was mounted to `/docker-entrypoint-initdb.d/` correctly.
- Env vars not available: ensure `docker-compose.yml` includes `env_file: - ./.env` or proper `environment:` entries, and that `.env` contains the expected keys.

## Optional script improvements

- Add validation & console logs.
- Update the script to `db.updateUser()` when the user exists if you prefer to ensure the password is always set.
- Add index creation lines in the init script if you want certain indexes to exist at DB creation time.

---

If you want, I can:
- Add the suggested validation/logging lines to `init-mongo.js` (non-breaking), or
- Add a short README to the project root linking to this file and documenting how to bring up the stack and verify connectivity.

