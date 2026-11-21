#!/usr/bin/env bash
# Crux #726 item 1: the 2026-11-21 run, rebuilt after the fact from the commands typed.
# Not run as a script. The sed pattern and health wait differ slightly from what ran.
# Run from Git Bash in an empty folder under $TEMP, never inside the repo.
set -u
npx -y supabase@latest init --force
# Enable the pooler block with pool size 1 (see config-pooler-block.toml).
sed -i '/^\[db.pooler\]/,/^max_client_conn/{s/^enabled = false/enabled = true/;s/^default_pool_size = .*/default_pool_size = 1/}' supabase/config.toml
npx -y supabase@latest start -x gotrue,realtime,storage-api,imgproxy,kong,mailpit,postgrest,postgres-meta,studio,edge-runtime,logflare,vector
MSYS_NO_PATHCONV=1 docker exec -i supabase_db_crux-726-pooler psql -U postgres -d postgres -v ON_ERROR_STOP=1 -q < schema.sql
D=$(date -u +%Y-%m-%d)
python -I pooler_rls_test.py "$(npx -y supabase@latest --version)" > "run-$D.log" 2>&1; echo "test exit $?"
# Step 8b: each local leak action in turn (mutates the throwaway tenant row).
L="leak-action-$D.log"; : > "$L"
for m in ignore log error; do
  MSYS_NO_PATHCONV=1 docker exec supabase_db_crux-726-pooler psql -U postgres -d _supabase -Atc \
    "update _supavisor.tenants set txn_mode_leak_action = '$m' where external_id = 'pooler-dev' returning external_id, txn_mode_leak_action" >> "$L" 2>&1
  docker restart supabase_pooler_crux-726-pooler >> "$L" 2>&1
  until [ "$(docker inspect -f '{{.State.Health.Status}}' supabase_pooler_crux-726-pooler)" = healthy ]; do sleep 2; done
  python -I leak_action_probe.py >> "$L" 2>&1
done
npx -y supabase@latest stop --no-backup
