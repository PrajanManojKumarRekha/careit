-- USERS
insert into users (id, email, password_hash, full_name, role)
values
(gen_random_uuid(), 'doc1@test.com', 'hash', 'Dr. Smith', 'doctor'),
(gen_random_uuid(), 'patient1@test.com', 'hash', 'John Doe', 'patient');

insert into doctors (id, user_id, full_name, specialty, license_no, lat, lng, address)
values (
gen_random_uuid(),
(select id from users where email='doc1@test.com'),
'Dr. Smith',
'Cardiology',
'LIC123',
29.4241,
-98.4936,
'San Antonio'
);

insert into appointments (id, patient_id, doctor_id, scheduled_at, status)
values (
gen_random_uuid(),
(select id from users where email='patient1@test.com'),
(select id from doctors limit 1),
now(),
'completed'
);