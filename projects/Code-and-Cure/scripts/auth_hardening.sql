alter table users
  add column if not exists email_verified_at timestamptz,
  add column if not exists failed_login_attempts integer not null default 0,
  add column if not exists locked_until timestamptz;

create table if not exists auth_challenges (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references users(id) on delete cascade,
  purpose text not null check (purpose in ('email_verification', 'login_mfa')),
  code_hash text not null,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_users_email_verified on users(email_verified_at);
create index if not exists idx_users_locked_until on users(locked_until);
create index if not exists idx_auth_challenges_user on auth_challenges(user_id);
create index if not exists idx_auth_challenges_purpose on auth_challenges(purpose);
create index if not exists idx_auth_challenges_expires_at on auth_challenges(expires_at);

alter table auth_challenges enable row level security;

drop policy if exists auth_challenges_dev_all on auth_challenges;
drop policy if exists auth_challenges_service_role_only on auth_challenges;
create policy auth_challenges_service_role_only
  on auth_challenges
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

alter table users enable row level security;

drop policy if exists users_dev_all on users;
drop policy if exists users_service_role_only on users;
create policy users_service_role_only
  on users
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');
