create extension if not exists "uuid-ossp";

create table users (
  id uuid primary key default uuid_generate_v4(),
  email text unique not null,
  password_hash text not null,
  full_name text not null,
  role text check (role in ('patient','doctor','admin')),
  created_at timestamp default now()
);

create table doctors (
  id uuid primary key default uuid_generate_v4(),

  user_id uuid references users(id) on delete cascade,

  full_name text not null,
  specialty text not null,
  license_no text not null,

  lat float,
  lng float,
  address text,

  availability jsonb,

  created_at timestamp default now()
);

create table patient_profiles (
  user_id uuid primary key references users(id) on delete cascade,

  date_of_birth date,
  medical_history text,
  allergies text,

  created_at timestamp default now()
);

create table hospitals (
  id uuid primary key default uuid_generate_v4(),

  name text not null,
  address text,
  lat float,
  lng float,

  created_at timestamp default now()
);

create table appointments (
  id uuid primary key default uuid_generate_v4(),

  patient_id uuid references users(id) on delete cascade,
  doctor_id uuid references doctors(id) on delete cascade,
  hospital_id uuid references hospitals(id),

  scheduled_at timestamptz not null,

  status text not null check (
    status in ('pending', 'confirmed', 'completed', 'cancelled')
  ) default 'pending',

  notes text,

  created_at timestamp default now()
);

create table intake_forms (
  id uuid primary key default uuid_generate_v4(),

  appointment_id uuid references appointments(id) on delete cascade,
  patient_id uuid references users(id) on delete cascade,

  symptoms text,
  allergies text,
  medications text,
  medical_history text,

  submitted_at timestamp default now()
);

create table soap_notes (
  id uuid primary key default uuid_generate_v4(),

  appointment_id uuid references appointments(id) on delete cascade,
  doctor_id uuid references doctors(id) on delete cascade,

  subjective text,
  objective text,
  assessment text,
  plan text,

  raw_transcript text,

  approved boolean default false,
  approved_at timestamptz,

  created_at timestamp default now()
);

create table fhir_records (
  id uuid primary key default uuid_generate_v4(),

  soap_note_id uuid references soap_notes(id) on delete cascade,

  fhir_version text default 'R4',
  resource_type text default 'Composition',

  fhir_json jsonb not null,

  created_at timestamp default now()
);

create table logs (
  id uuid primary key default uuid_generate_v4(),

  user_id uuid references users(id),

  action text not null,
  resource text not null,
  ip_address text,

  created_at timestamp default now()
);

create index idx_users_email on users(email);

create index idx_doctors_specialty on doctors(specialty);

create index idx_doctors_location on doctors(lat, lng);

create index idx_appointments_patient on appointments(patient_id);

create index idx_appointments_doctor on appointments(doctor_id);

create index idx_appointments_time on appointments(scheduled_at);

create index idx_logs_user on logs(user_id);

create index idx_logs_created on logs(created_at);