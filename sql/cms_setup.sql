-- Run manually once as the uhr database owner.
-- This file is never executed by deploy.

CREATE TABLE cms_pages (
    id SERIAL PRIMARY KEY,
    site VARCHAR(32) NOT NULL,
    locale VARCHAR(8) NOT NULL DEFAULT 'nl',
    slug VARCHAR(160) NOT NULL,
    title VARCHAR(255) NOT NULL,
    seo_title VARCHAR(255) NOT NULL DEFAULT '',
    seo_description TEXT NOT NULL DEFAULT '',
    draft_version_id INTEGER,
    published_version_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (site, locale, slug),
    CONSTRAINT cms_pages_site_chk CHECK (site IN ('uhrbv', 'ukrwerkspot'))
);

CREATE TABLE cms_page_versions (
    id SERIAL PRIMARY KEY,
    page_id INTEGER NOT NULL REFERENCES cms_pages(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    project_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    html TEXT NOT NULL DEFAULT '',
    css TEXT NOT NULL DEFAULT '',
    note VARCHAR(255) NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (page_id, version)
);
CREATE INDEX cms_page_versions_page_idx ON cms_page_versions(page_id, version DESC);

CREATE TABLE cms_menus (
    id SERIAL PRIMARY KEY,
    site VARCHAR(32) NOT NULL,
    locale VARCHAR(8) NOT NULL DEFAULT 'nl',
    area VARCHAR(32) NOT NULL DEFAULT 'header',
    name VARCHAR(128) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    published_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    draft_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (site, locale, area),
    CONSTRAINT cms_menus_site_chk CHECK (site IN ('uhrbv', 'ukrwerkspot')),
    CONSTRAINT cms_menus_area_chk CHECK (area IN ('header', 'footer'))
);

CREATE TABLE cms_menu_versions (
    id SERIAL PRIMARY KEY,
    menu_id INTEGER NOT NULL REFERENCES cms_menus(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (menu_id, version)
);

CREATE TABLE cms_posts (
    id SERIAL PRIMARY KEY,
    site VARCHAR(32) NOT NULL,
    locale VARCHAR(8) NOT NULL DEFAULT 'nl',
    kind VARCHAR(16) NOT NULL DEFAULT 'blog',
    slug VARCHAR(160) NOT NULL,
    title VARCHAR(255) NOT NULL,
    excerpt TEXT NOT NULL DEFAULT '',
    cover_url VARCHAR(512) NOT NULL DEFAULT '',
    draft_body TEXT NOT NULL DEFAULT '',
    published_body TEXT NOT NULL DEFAULT '',
    status VARCHAR(16) NOT NULL DEFAULT 'draft',
    version INTEGER NOT NULL DEFAULT 1,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (site, locale, kind, slug),
    CONSTRAINT cms_posts_site_chk CHECK (site IN ('uhrbv', 'ukrwerkspot')),
    CONSTRAINT cms_posts_kind_chk CHECK (kind IN ('news', 'blog')),
    CONSTRAINT cms_posts_status_chk CHECK (status IN ('draft', 'published'))
);
CREATE INDEX cms_posts_public_idx ON cms_posts(site, kind, status, published_at DESC);

CREATE TABLE cms_post_versions (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES cms_posts(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (post_id, version)
);

CREATE TABLE cms_media (
    id SERIAL PRIMARY KEY,
    site VARCHAR(32) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    stored_path VARCHAR(512) NOT NULL,
    public_url VARCHAR(512) NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    size_bytes INTEGER NOT NULL,
    alt VARCHAR(255) NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT cms_media_site_chk CHECK (site IN ('uhrbv', 'ukrwerkspot'))
);
CREATE INDEX cms_media_site_idx ON cms_media(site, created_at DESC);

CREATE TABLE cms_catalog_categories (
    id SERIAL PRIMARY KEY,
    site VARCHAR(32) NOT NULL,
    slug VARCHAR(128) NOT NULL,
    title VARCHAR(255) NOT NULL,
    profession VARCHAR(128) NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    image_url VARCHAR(512) NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_visible BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (site, slug),
    CONSTRAINT cms_categories_site_chk CHECK (site IN ('uhrbv', 'ukrwerkspot'))
);
