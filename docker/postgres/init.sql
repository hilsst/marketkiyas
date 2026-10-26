-- İlk kurulumda çalışır. Migration da extension'ı oluşturur; bu, test DB'si için de garanti.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE DATABASE marketkiyas_test OWNER marketkiyas;
\c marketkiyas_test
CREATE EXTENSION IF NOT EXISTS pg_trgm;
