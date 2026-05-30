-- =====================================================================
-- THE INTRINSIC — Skema Database (PostgreSQL / Supabase)
-- Jalankan di Supabase SQL Editor.
-- =====================================================================

-- 1) USERS — kredensial untuk streamlit-authenticator
create table if not exists users (
    id            uuid primary key default gen_random_uuid(),
    username      text unique not null,
    name          text not null,
    email         text unique,
    password_hash text not null,          -- bcrypt hash dari streamlit-authenticator
    created_at    timestamptz default now()
);

-- 2) PORTFOLIOS — holding pribadi tiap user (FK ke users.username)
create table if not exists portfolios (
    id           bigserial primary key,
    username     text not null references users(username) on delete cascade,
    kode_saham   text not null,
    harga_rata2  numeric(14,2) not null check (harga_rata2 >= 0),
    jumlah_lot   integer not null check (jumlah_lot >= 0),
    created_at   timestamptz default now(),
    updated_at   timestamptz default now()
);
create index if not exists idx_portfolios_username on portfolios(username);

-- 3) FUNDAMENTAL_DATA — cache metrik fundamental per emiten
create table if not exists fundamental_data (
    id              bigserial primary key,
    kode_saham      text unique not null,
    per             numeric,
    pbv             numeric,
    roe             numeric,
    der             numeric,
    dividend_yield  numeric,
    updated_at      timestamptz default now()
);

-- 4) BROKER_SUMMARY — net value per broker per tanggal (diisi scraper/API)
create table if not exists broker_summary (
    id           bigserial primary key,
    kode_saham   text not null,
    tanggal      date not null,
    kode_broker  text not null,           -- mis. MG, AK, BK
    net_value    bigint,                  -- positif = net beli, negatif = net jual (Rupiah)
    created_at   timestamptz default now(),
    unique (kode_saham, tanggal, kode_broker)
);
create index if not exists idx_broksum_kode on broker_summary(kode_saham);

-- 5) KONGLO_TRACKER — kepemilikan >= 5% taipan/institusi (sumber: IDX/KSEI)
create table if not exists konglo_tracker (
    id                  bigserial primary key,
    kode_saham          text not null,
    nama_pemilik        text not null,
    tipe                text check (tipe in ('Individu', 'Institusi', 'Keluarga')),
    persen_kepemilikan  numeric(5,2) check (persen_kepemilikan >= 0 and persen_kepemilikan <= 100),
    tanggal_update      date,
    sumber              text,
    created_at          timestamptz default now()
);
create index if not exists idx_konglo_kode on konglo_tracker(kode_saham);

-- =====================================================================
-- (Opsional, disarankan untuk produksi) Row Level Security
-- Catatan: karena auth memakai streamlit-authenticator (bukan Supabase Auth),
-- RLS berbasis auth.uid() tidak otomatis berlaku. Untuk produksi nyata,
-- pertimbangkan beralih ke Supabase Auth agar RLS di bawah ini aktif penuh.
-- =====================================================================
-- alter table portfolios enable row level security;
-- create policy "user_owns_portfolio" on portfolios
--     for all using (auth.uid()::text = username);
