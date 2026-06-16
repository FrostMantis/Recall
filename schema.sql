-- ============================================================
--  Kernel schema (MariaDB/InnoDB)
-- ============================================================

CREATE TABLE IF NOT EXISTS nodes (
    id          INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(512)  NOT NULL,
    type        VARCHAR(128)  NOT NULL DEFAULT 'thing',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS properties (
    id       INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    node_id  INT          NOT NULL,
    `key`    VARCHAR(256) NOT NULL,
    value    TEXT,
    UNIQUE (node_id, `key`),
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS links (
    id          INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source_id   INT          NOT NULL,
    target_id   INT          NOT NULL,
    flavour     VARCHAR(32)  NOT NULL DEFAULT 'uses_serves',
    label       VARCHAR(256) NOT NULL DEFAULT '',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_id, target_id, label),
    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE,
    CONSTRAINT chk_flavour CHECK (flavour IN ('lives_in', 'uses_serves', 'made_of', 'other'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS session (
    id        INT  NOT NULL PRIMARY KEY,
    focus_id  INT,
    trail     TEXT NOT NULL DEFAULT '[]'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX IF NOT EXISTS idx_nodes_name   ON nodes (name(255));
CREATE INDEX IF NOT EXISTS idx_nodes_type   ON nodes (type);
CREATE INDEX IF NOT EXISTS idx_props_value  ON properties (value(255));
CREATE INDEX IF NOT EXISTS idx_links_source ON links (source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links (target_id);
