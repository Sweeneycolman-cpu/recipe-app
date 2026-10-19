-- Run once in the Supabase SQL editor. Separate from all expenses tables.
create table if not exists public.recipe_book_meals (
  id uuid primary key,
  name text not null check (length(trim(name)) > 0),
  ingredients jsonb not null check (jsonb_typeof(ingredients) = 'array'),
  servings integer not null check (servings between 1 and 100),
  instructions text not null default ''
);
alter table public.recipe_book_meals enable row level security;
revoke all on public.recipe_book_meals from anon, authenticated;
grant select, insert, update, delete on public.recipe_book_meals to service_role;
-- Access is server-side only, after the app password check. No public RLS policies.
