-- Run once in the target Supabase project before enabling production traffic.
-- Review the first SELECT result before running the DELETE statement.

select id, email, role
from users
where email like 'demo.%@careit.local'
   or password_hash = 'DEMO_AUTH_ONLY';

-- Remove only the known shared demo identities. Related rows cascade according
-- to the existing foreign keys. Uncomment after review.
-- delete from users
-- where email like 'demo.%@careit.local'
--    or password_hash = 'DEMO_AUTH_ONLY';

-- Clerk integration requires these columns and service-role-only RLS policies.
-- This migration is idempotent and safe to run after auth_hardening.sql.
alter table users
  add column if not exists clerk_user_id text,
  alter column password_hash drop not null,
  add column if not exists email_verified_at timestamptz;

create unique index if not exists idx_users_clerk_user_id
  on users(clerk_user_id)
  where clerk_user_id is not null;
