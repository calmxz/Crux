-- Crux #726 item 1: pooler + row-level security test schema.
-- Run as `postgres` on the direct port (54322), not through the pooler.
-- Local-only password; this database is thrown away after the test.

drop table if exists sessions_no_nullif;
drop table if exists sessions;
drop table if exists homes;
drop role if exists crux_app;

create role crux_app login password 'crux_app_local' nobypassrls;

-- Tables are created by, and owned by, postgres.
create table homes (
  id   uuid primary key,
  name text not null
);

create table sessions (
  id      bigint generated always as identity primary key,
  home_id uuid not null references homes (id),
  title   text not null
);

-- Same data, but its policy casts without nullif (for step 7).
create table sessions_no_nullif (
  id      bigint generated always as identity primary key,
  home_id uuid not null references homes (id),
  title   text not null
);

alter table homes              enable row level security;
alter table sessions           enable row level security;
alter table sessions_no_nullif enable row level security;

create policy homes_by_home on homes
  using      (id = nullif(current_setting('app.home_id', true), '')::uuid)
  with check (id = nullif(current_setting('app.home_id', true), '')::uuid);

create policy sessions_by_home on sessions
  using      (home_id = nullif(current_setting('app.home_id', true), '')::uuid)
  with check (home_id = nullif(current_setting('app.home_id', true), '')::uuid);

create policy sessions_no_nullif_by_home on sessions_no_nullif
  using      (home_id = current_setting('app.home_id', true)::uuid)
  with check (home_id = current_setting('app.home_id', true)::uuid);

-- Supabase's default privileges hand table rights to anon, authenticated
-- and service_role. Strip everything, then grant crux_app only what it needs.
revoke all on homes, sessions, sessions_no_nullif from public, anon, authenticated, service_role;
grant usage on schema public to crux_app;
grant select, insert on homes, sessions, sessions_no_nullif to crux_app;

-- Seed as postgres (owner, so RLS does not apply to these inserts).
-- Ana has 3 sessions and Ben has 2, so a leak shows up as a wrong count.
insert into homes (id, name) values
  ('aaaaaaaa-0000-4000-8000-000000000001', 'Ana'),
  ('bbbbbbbb-0000-4000-8000-000000000002', 'Ben');

insert into sessions (home_id, title) values
  ('aaaaaaaa-0000-4000-8000-000000000001', 'Ana: biology week 1'),
  ('aaaaaaaa-0000-4000-8000-000000000001', 'Ana: biology week 2'),
  ('aaaaaaaa-0000-4000-8000-000000000001', 'Ana: chemistry'),
  ('bbbbbbbb-0000-4000-8000-000000000002', 'Ben: history'),
  ('bbbbbbbb-0000-4000-8000-000000000002', 'Ben: law');

insert into sessions_no_nullif (home_id, title)
  select home_id, title from sessions order by id;
