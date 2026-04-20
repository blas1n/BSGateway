-- name: create_worker
INSERT INTO workers (tenant_id, name, labels, capabilities, token_hash, status)
VALUES ($1, $2, $3, $4, $5, 'online')
RETURNING id, tenant_id, name, labels, capabilities, status, token_hash,
          last_heartbeat, is_active, created_at, updated_at;

-- name: get_worker_by_token
SELECT id, tenant_id, name, labels, capabilities, status,
       last_heartbeat, is_active, created_at, updated_at
FROM workers WHERE token_hash = $1 AND is_active = TRUE;

-- name: update_heartbeat
UPDATE workers SET status = 'online', last_heartbeat = NOW(), updated_at = NOW()
WHERE id = $1 AND is_active = TRUE
RETURNING id, status, last_heartbeat;

-- name: list_workers
SELECT id, tenant_id, name, labels, capabilities, status,
       last_heartbeat, is_active, created_at, updated_at
FROM workers WHERE tenant_id = $1 AND is_active = TRUE
ORDER BY name;

-- name: find_available_worker
SELECT id, tenant_id, name, capabilities
FROM workers
WHERE tenant_id = $1 AND is_active = TRUE AND status = 'online'
  AND last_heartbeat > NOW() - INTERVAL '120 seconds'
ORDER BY last_heartbeat ASC
LIMIT 1;

-- name: deactivate_worker
UPDATE workers SET is_active = FALSE, updated_at = NOW()
WHERE id = $1 AND tenant_id = $2;

-- name: create_task
INSERT INTO executor_tasks (tenant_id, executor_type, prompt, status)
VALUES ($1, $2, $3, 'pending')
RETURNING id, tenant_id, executor_type, prompt, status, worker_id,
          output, error_message, created_at, updated_at;

-- name: get_task
SELECT id, tenant_id, executor_type, prompt, status, worker_id,
       output, error_message, created_at, updated_at
FROM executor_tasks WHERE id = $1 AND tenant_id = $2;

-- name: update_task_dispatched
UPDATE executor_tasks SET status = 'dispatched', worker_id = $2, updated_at = NOW()
WHERE id = $1;

-- name: update_task_result
UPDATE executor_tasks
SET status = CASE WHEN $2 THEN 'done' ELSE 'failed' END,
    output = $3,
    error_message = $4,
    updated_at = NOW()
WHERE id = $1
RETURNING id, status;

-- name: list_tasks
SELECT id, tenant_id, executor_type, prompt, status, worker_id,
       output, error_message, created_at, updated_at
FROM executor_tasks WHERE tenant_id = $1
ORDER BY created_at DESC
LIMIT $2 OFFSET $3;
