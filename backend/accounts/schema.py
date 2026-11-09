"""Account, consent, school and sharing tables.

Lives in the same SQLite file as the learning-engine tables, which are untouched.
Relationships (parent-child, class enrolment, sharing) are separate tables with a
status, so access can be granted, paused or revoked without deleting people.
"""

ACCOUNTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK (role IN ('student','learner','parent','teacher','school_admin','platform_admin')),
    email TEXT UNIQUE,                 -- lowercase; optional for under-18 students
    email_verified_at TEXT,
    username TEXT UNIQUE,              -- lowercase; required for students
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    date_of_birth TEXT,                -- YYYY-MM-DD; students and learners only
    status TEXT NOT NULL CHECK (status IN ('pending_verification','pending_consent','active','suspended')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    revoked_at TEXT
);

-- Every emailed link: single use, stored only as a hash.
CREATE TABLE IF NOT EXISTS email_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    purpose TEXT NOT NULL CHECK (purpose IN ('verify_email','reset_password','parent_consent',
                                             'teacher_invite','admin_invite','share_invite')),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT
);

CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    udise_code TEXT UNIQUE,
    state TEXT,
    district TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    source_year TEXT,
    verified INTEGER NOT NULL DEFAULT 0,
    subscription_status TEXT NOT NULL DEFAULT 'none' CHECK (subscription_status IN ('none','active','lapsed')),
    subscription_ends TEXT,
    consent_handled_by_school INTEGER NOT NULL DEFAULT 0,
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    grade INTEGER NOT NULL CHECK (grade BETWEEN 1 AND 12),
    division TEXT NOT NULL,
    academic_year TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (school_id, grade, division, academic_year)
);

CREATE TABLE IF NOT EXISTS student_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    pathway TEXT NOT NULL CHECK (pathway IN ('individual','school')),
    grade INTEGER,
    division TEXT,
    school_id INTEGER REFERENCES schools(id),
    manual_school_name TEXT,
    onboarding_complete INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS parent_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    relationship_note TEXT
);

CREATE TABLE IF NOT EXISTS teacher_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    can_create_codes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS school_memberships (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    role_at_school TEXT NOT NULL CHECK (role_at_school IN ('student','teacher','admin')),
    status TEXT NOT NULL CHECK (status IN ('active','removed')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, school_id)
);

CREATE TABLE IF NOT EXISTS referral_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    created_by INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL,
    max_uses INTEGER NOT NULL,
    uses INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('active','revoked')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS class_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected','removed')),
    via_code_id INTEGER REFERENCES referral_codes(id),
    decided_by INTEGER REFERENCES users(id),
    decided_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (student_user_id, class_id)
);

CREATE TABLE IF NOT EXISTS teacher_class_assignments (
    teacher_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    subject TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    PRIMARY KEY (teacher_user_id, class_id, subject)
);

CREATE TABLE IF NOT EXISTS parent_student_links (
    parent_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('active','revoked')),
    permissions TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (parent_user_id, student_user_id)
);

-- Append-only: a change adds a new row, nothing is overwritten.
CREATE TABLE IF NOT EXISTS consent_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    given_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('granted','updated','withdrawn')),
    purposes TEXT NOT NULL,
    permissions TEXT NOT NULL,
    notice_version TEXT NOT NULL,
    method TEXT NOT NULL,
    declarations TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS share_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    grantee_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    invite_email TEXT,
    scopes TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK (status IN ('invited','requested','active','rejected','revoked','expired')),
    expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    viewer_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    what TEXT NOT NULL,
    via TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_events (
    key TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Used when no email service is configured: emails are saved here instead of sent.
CREATE TABLE IF NOT EXISTS email_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_email ON email_tokens(email);
CREATE INDEX IF NOT EXISTS idx_enroll_class ON class_enrollments(class_id);
CREATE INDEX IF NOT EXISTS idx_links_student ON parent_student_links(student_user_id);
CREATE INDEX IF NOT EXISTS idx_grants_owner ON share_grants(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_rate_key ON rate_events(key, created_at);
"""
