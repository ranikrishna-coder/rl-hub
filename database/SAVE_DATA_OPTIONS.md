# Ways to Save Data Into the Database

Besides the **web UI forms**, you can write data using the **REST API** or **direct SQL**.

---

## 1. Contact form → `contact_submissions`

| Method | How |
|--------|-----|
| **UI** | Contact form in the app (name, email, organization, subject, use case). |
| **REST** | `POST /api/contact` with JSON body. |
| **SQL** | `INSERT INTO contact_submissions (...)` in MariaDB. |

**REST example (contact):**
```bash
curl -X POST http://localhost:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane","email":"jane@example.com","organization":"Acme","subject":"Demo","use_case":"Testing the simulator"}'
```

**Required JSON fields:** `name`, `email`, `organization`, `use_case`. Optional: `subject`.

---

## 2. Custom environments → `user_environments`

| Method | How |
|--------|-----|
| **UI** | Create/import environment, then save in the app. |
| **REST** | `POST /api/custom-environments` (create) or `PUT /api/custom-environments/{name}` (update). |
| **SQL** | `INSERT` / `UPDATE` on `user_environments` (store full JSON in `data`; set `name`, `source`, `created_at`, `updated_at`). |

**REST example (create environment):**
```bash
curl -X POST http://localhost:8000/api/custom-environments \
  -H "Content-Type: application/json" \
  -d '{"name":"my-env","category":"custom","source":"custom"}'
```

Body can include any environment config (name required). Updates: `PUT /api/custom-environments/my-env` with full or partial JSON.

---

## 3. Scenarios → `user_scenarios`

| Method | How |
|--------|-----|
| **UI** | Create/edit scenario in the app and save. |
| **REST** | `POST /api/scenarios` with one scenario or a list. |
| **SQL** | `INSERT` / `UPDATE` on `user_scenarios` (store full JSON in `data`; set `id`, `product`, `source`, `created_at`, `updated_at`). |

**REST example (single scenario):**
```bash
curl -X POST http://localhost:8000/api/scenarios \
  -H "Content-Type: application/json" \
  -d '{"id":"scenario-1","name":"My scenario","product":"MyProduct","source":"custom"}'
```

**REST example (bulk):**
```bash
curl -X POST http://localhost:8000/api/scenarios \
  -H "Content-Type: application/json" \
  -d '{"scenarios":[{"id":"s1","name":"First"},{"id":"s2","name":"Second"}]}'
```

Each item must have an `id`. Other fields are optional and stored as-is in the JSON `data` blob.

---

## 4. Verifiers → `user_verifiers`

| Method | How |
|--------|-----|
| **UI** | Create/edit verifier in the app. |
| **REST** | `POST /api/verifiers` (create), `PUT /api/verifiers/{verifier_id}` (edit). |
| **SQL** | `INSERT` / `UPDATE` on `user_verifiers` (store full JSON in `data`; set `id`, `environment`, `source`, `created_at`, `updated_at`). |

**REST example (create verifier):**
```bash
curl -X POST http://localhost:8000/api/verifiers \
  -H "Content-Type: application/json" \
  -d '{
    "name":"My verifier",
    "type":"rule-based",
    "system":"Custom",
    "environment":"my-env",
    "description":"Custom rule verifier"
  }'
```

**VerifierDefinition fields:** `name`, `type`, `system`, `environment` (required); optional: `id`, `version`, `status`, `used_in_scenarios`, `description`, `metadata`, `logic`, `example_input`, `example_output`, `failure_policy`, etc.

---

## 5. Environment backups → `environment_backups`

| Method | How |
|--------|-----|
| **UI** | Backup action in the app. |
| **REST** | MCP/agent endpoint (if enabled): create backup via the agent API. |
| **SQL** | Usually not needed; app creates backups automatically. |

---

## 6. Health snapshots → `health_snapshots`

Written only by the app at runtime (health checks). No UI or public API to “form submit”; optional to add your own endpoint or script that inserts into this table if you need custom health data.

---

## Summary

- **Forms in the app:** Contact (→ `contact_submissions`); Environments, Scenarios, Verifiers (→ `user_environments`, `user_scenarios`, `user_verifiers`).
- **Other ways to save:** Call the REST endpoints above (e.g. from Postman, curl, or your own frontend), or run `INSERT`/`UPDATE` in MariaDB. For `contact_submissions`, `user_environments`, `user_scenarios`, and `user_verifiers`, REST is the preferred “other form” so the app stays in sync.
