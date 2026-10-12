-- Initial schema for a bounded import of the French BDPM structured files.
-- Executed by the PostgreSQL image only when medication-db-data is empty.

CREATE TABLE medication_imports (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name text NOT NULL CHECK (btrim(source_name) <> ''),
    source_url text NOT NULL CHECK (btrim(source_url) <> ''),
    source_updated_on date NOT NULL,
    source_sha256 char(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    imported_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_name, source_updated_on, source_sha256)
);

CREATE TABLE medications (
    cis text PRIMARY KEY CHECK (cis ~ '^[0-9]+$'),
    name text NOT NULL CHECK (btrim(name) <> ''),
    pharmaceutical_form text,
    administration_routes text,
    authorization_status text,
    commercialization_status text,
    source_import_id bigint NOT NULL REFERENCES medication_imports(id)
);

CREATE TABLE medication_presentations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cis text NOT NULL REFERENCES medications(cis) ON DELETE CASCADE,
    cip7 text CHECK (cip7 IS NULL OR cip7 ~ '^[0-9]{7}$'),
    cip13 text CHECK (cip13 IS NULL OR cip13 ~ '^[0-9]{13}$'),
    label text NOT NULL CHECK (btrim(label) <> ''),
    administrative_status text,
    commercialization_status text,
    source_import_id bigint NOT NULL REFERENCES medication_imports(id),
    CHECK (cip7 IS NOT NULL OR cip13 IS NOT NULL),
    UNIQUE (cip7),
    UNIQUE (cip13)
);

CREATE INDEX medication_presentations_cis_idx
    ON medication_presentations (cis);

CREATE TABLE medication_compositions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cis text NOT NULL REFERENCES medications(cis) ON DELETE CASCADE,
    pharmaceutical_element text,
    substance_code text,
    substance_name text NOT NULL CHECK (btrim(substance_name) <> ''),
    substance_dosage text,
    dosage_reference text,
    component_nature text,
    linkage_number text,
    source_import_id bigint NOT NULL REFERENCES medication_imports(id)
);

CREATE INDEX medication_compositions_cis_idx
    ON medication_compositions (cis);
