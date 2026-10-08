-- Initial schema. Run once on the server database.
-- Later changes: send me the request, I will return ALTER statements only.

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(32)  NOT NULL DEFAULT 'admin',
    name            VARCHAR(255) NOT NULL DEFAULT '',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT users_role_chk CHECK (role IN ('admin', 'company'))
);

CREATE TABLE craftsmen (
    id                 SERIAL PRIMARY KEY,
    status             VARCHAR(32)  NOT NULL DEFAULT 'pending',
    published          BOOLEAN      NOT NULL DEFAULT FALSE,
    name               VARCHAR(255) NOT NULL DEFAULT '',
    phone              VARCHAR(64)  NOT NULL DEFAULT '',
    email              VARCHAR(255) NOT NULL DEFAULT '',
    language           VARCHAR(32)  NOT NULL DEFAULT 'uk',
    company_name       VARCHAR(255) NOT NULL DEFAULT '',
    kvk                VARCHAR(16)  NOT NULL DEFAULT '',
    btw                VARCHAR(64)  NOT NULL DEFAULT '',
    address            TEXT         NOT NULL DEFAULT '',
    website            VARCHAR(255) NOT NULL DEFAULT '',
    instagram          VARCHAR(255) NOT NULL DEFAULT '',
    facebook           VARCHAR(255) NOT NULL DEFAULT '',
    tiktok             VARCHAR(255) NOT NULL DEFAULT '',
    profession         VARCHAR(128) NOT NULL DEFAULT '',
    extra_work         TEXT         NOT NULL DEFAULT '',
    experience_years   INTEGER,
    hourly_rate        NUMERIC(10,2),
    city               VARCHAR(128) NOT NULL DEFAULT '',
    radius_km          INTEGER,
    availability       VARCHAR(64)  NOT NULL DEFAULT '',
    nationwide         BOOLEAN      NOT NULL DEFAULT FALSE,
    description        TEXT         NOT NULL DEFAULT '',
    portfolio_url      VARCHAR(512) NOT NULL DEFAULT '',
    admin_comment      TEXT         NOT NULL DEFAULT '',
    consent_at         TIMESTAMPTZ,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT craftsmen_status_chk CHECK (status IN ('pending', 'clarification', 'approved', 'rejected'))
);

CREATE INDEX craftsmen_status_idx ON craftsmen (status);
CREATE INDEX craftsmen_created_idx ON craftsmen (created_at DESC);

CREATE TABLE companies (
    id                   SERIAL PRIMARY KEY,
    status               VARCHAR(32)  NOT NULL DEFAULT 'pending',
    company_name         VARCHAR(255) NOT NULL DEFAULT '',
    kvk                  VARCHAR(16)  NOT NULL DEFAULT '',
    btw                  VARCHAR(64)  NOT NULL DEFAULT '',
    address              TEXT         NOT NULL DEFAULT '',
    website              VARCHAR(255) NOT NULL DEFAULT '',
    description          TEXT         NOT NULL DEFAULT '',
    contact_name         VARCHAR(255) NOT NULL DEFAULT '',
    contact_role         VARCHAR(128) NOT NULL DEFAULT '',
    email                VARCHAR(255) NOT NULL DEFAULT '',
    phone                VARCHAR(64)  NOT NULL DEFAULT '',
    region               VARCHAR(128) NOT NULL DEFAULT '',
    desired_profession   VARCHAR(128) NOT NULL DEFAULT '',
    expected_count       INTEGER,
    sna                  VARCHAR(32)  NOT NULL DEFAULT '',
    admin_comment        TEXT         NOT NULL DEFAULT '',
    consent_at           TIMESTAMPTZ,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT companies_status_chk CHECK (status IN ('pending', 'clarification', 'approved', 'rejected'))
);

CREATE INDEX companies_status_idx ON companies (status);

CREATE TABLE documents (
    id             SERIAL PRIMARY KEY,
    owner_type     VARCHAR(32)  NOT NULL,
    owner_id       INTEGER      NOT NULL,
    kind           VARCHAR(64)  NOT NULL,
    original_name  VARCHAR(255) NOT NULL,
    stored_path    VARCHAR(512) NOT NULL,
    mime_type      VARCHAR(128) NOT NULL DEFAULT '',
    size_bytes     INTEGER,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT documents_owner_chk CHECK (owner_type IN ('craftsman', 'company'))
);

CREATE INDEX documents_owner_idx ON documents (owner_type, owner_id);

CREATE TABLE requests (
    id                SERIAL PRIMARY KEY,
    public_id         VARCHAR(32)  NOT NULL UNIQUE,
    company_id        INTEGER      REFERENCES companies (id) ON DELETE SET NULL,
    craftsman_id      INTEGER      REFERENCES craftsmen (id) ON DELETE SET NULL,
    project           VARCHAR(255) NOT NULL DEFAULT '',
    site_address      TEXT         NOT NULL DEFAULT '',
    start_date        DATE,
    duration          VARCHAR(128) NOT NULL DEFAULT '',
    schedule          VARCHAR(255) NOT NULL DEFAULT '',
    workers_count     INTEGER,
    work_description  TEXT         NOT NULL DEFAULT '',
    requirements      TEXT         NOT NULL DEFAULT '',
    status            VARCHAR(64)  NOT NULL DEFAULT 'submitted',
    admin_comment     TEXT         NOT NULL DEFAULT '',
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT requests_status_chk CHECK (status IN (
        'draft', 'submitted', 'in_progress', 'candidate', 'confirmed', 'done', 'cancelled'
    ))
);

CREATE INDEX requests_status_idx ON requests (status);

CREATE TABLE messages (
    id           SERIAL PRIMARY KEY,
    request_id   INTEGER      NOT NULL REFERENCES requests (id) ON DELETE CASCADE,
    sender_role  VARCHAR(32)  NOT NULL,
    sender_id    INTEGER      REFERENCES users (id) ON DELETE SET NULL,
    body         TEXT         NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT messages_role_chk CHECK (sender_role IN ('admin', 'company'))
);

CREATE INDEX messages_request_idx ON messages (request_id, created_at);

CREATE TABLE site_texts (
    id          SERIAL PRIMARY KEY,
    site        VARCHAR(32)  NOT NULL,
    page        VARCHAR(64)  NOT NULL,
    key         VARCHAR(128) NOT NULL,
    locale      VARCHAR(8)   NOT NULL DEFAULT 'uk',
    label       VARCHAR(255) NOT NULL,
    value       TEXT         NOT NULL DEFAULT '',
    sort_order  INTEGER      NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (site, page, key, locale)
);

CREATE INDEX site_texts_lookup_idx ON site_texts (site, page, locale);
