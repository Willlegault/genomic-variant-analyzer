-- Supabase schema for the genomic variant analyzer.
-- Run this once in the Supabase SQL editor.
-- The whole row payload (variants + summary + explanations) is denormalized
-- into a JSONB blob — there is no separate `variants` table. Cheaper to write,
-- trivial to evolve, and queryable via JSONB operators if it ever needs to be.

create table if not exists analyses (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    reference_id text not null,
    gene text not null,
    query_sequence text not null,
    query_length integer not null,
    variant_count integer not null,
    summary jsonb not null,
    variants jsonb not null
);

create index if not exists analyses_created_at_idx
    on analyses (created_at desc);

create index if not exists analyses_reference_id_idx
    on analyses (reference_id);

-- This is a portfolio app with no auth layer — RLS is therefore disabled so
-- the anon key can read/write `analyses`. If you wire up Supabase auth later,
-- enable RLS and add per-user policies before exposing this in production.
alter table analyses disable row level security;
