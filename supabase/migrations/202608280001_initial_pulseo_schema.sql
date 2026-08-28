-- Pulseo MVP: persistent source, article and event data.
-- Apply this migration to the remote Supabase project through its MCP or CLI.

create table public.sources (
  id text primary key,
  name text not null,
  language text not null check (char_length(language) between 2 and 10),
  country text,
  homepage_url text,
  rss_url text not null unique,
  quality_score numeric(3,2) not null default 0.50 check (quality_score between 0 and 1),
  priority smallint not null default 100,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  summary text not null,
  why_it_matters text,
  category text not null default 'Actualité',
  topics text[] not null default '{}',
  entities text[] not null default '{}',
  importance numeric(3,2) not null default 0.50 check (importance between 0 and 1),
  language text not null default 'fr',
  status text not null default 'published' check (status in ('draft', 'published', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.articles (
  id uuid primary key default gen_random_uuid(),
  source_id text not null references public.sources(id) on delete restrict,
  url text not null unique,
  original_title text not null,
  content_excerpt text,
  normalized_hash text not null unique,
  published_at timestamptz,
  event_id uuid references public.events(id) on delete set null,
  created_at timestamptz not null default now()
);

create index articles_published_at_idx on public.articles (published_at desc);
create index articles_event_id_idx on public.articles (event_id);
create index events_language_created_at_idx on public.events (language, created_at desc);

create table public.event_sources (
  event_id uuid not null references public.events(id) on delete cascade,
  source_id text not null references public.sources(id) on delete restrict,
  article_id uuid not null references public.articles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (event_id, article_id)
);

create table public.interactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  event_id uuid not null references public.events(id) on delete cascade,
  action text not null check (action in ('impression', 'like', 'source_open', 'article_open', 'swipe')),
  duration_ms integer check (duration_ms >= 0),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index interactions_event_id_created_at_idx on public.interactions (event_id, created_at desc);

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger sources_set_updated_at before update on public.sources
for each row execute function public.set_updated_at();

create trigger events_set_updated_at before update on public.events
for each row execute function public.set_updated_at();
