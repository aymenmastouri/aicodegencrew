"""Tests for database migration tool and SQL script detection.

Tests detection of:
- Liquibase (changelog.xml, liquibase.properties)
- Flyway (migrations folder, flyway.conf)
- SQL scripts (.sql files)
- Database schema information
"""

import pytest
from pathlib import Path


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure."""
    return tmp_path


def test_liquibase_detection_xml(temp_project):
    """Test Liquibase detection via changelog XML file."""
    # Create Liquibase structure
    db_changelog = temp_project / "src" / "main" / "resources" / "db" / "changelog"
    db_changelog.mkdir(parents=True)
    
    (db_changelog / "db.changelog-master.xml").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    
    <changeSet id="1" author="admin">
        <createTable tableName="users">
            <column name="id" type="bigint" autoIncrement="true">
                <constraints primaryKey="true" nullable="false"/>
            </column>
            <column name="username" type="varchar(255)"/>
        </createTable>
    </changeSet>
</databaseChangeLog>
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.database_collector import DatabaseCollector
    
    collector = DatabaseCollector(temp_project, "infrastructure")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect Liquibase as a component
    liquibase_components = [c for c in components if "liquibase" in c.name.lower()]
    assert len(liquibase_components) >= 1
    assert liquibase_components[0].stereotype == "database_migration"
    
    # Should detect table creation in evidence
    liquibase_evidence = [evidence[eid] for eid in liquibase_components[0].evidence_ids if eid in evidence]
    assert any("users" in ev.reason.lower() for ev in liquibase_evidence)


def test_flyway_detection(temp_project):
    """Test Flyway detection via migrations folder."""
    # Create Flyway structure
    migrations = temp_project / "src" / "main" / "resources" / "db" / "migration"
    migrations.mkdir(parents=True)
    
    (migrations / "V1__create_users_table.sql").write_text("""
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
""")
    
    (migrations / "V2__add_roles_table.sql").write_text("""
CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE user_roles (
    user_id BIGINT REFERENCES users(id),
    role_id BIGINT REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.database_collector import DatabaseCollector
    
    collector = DatabaseCollector(temp_project, "infrastructure")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect Flyway
    flyway_components = [c for c in components if "flyway" in c.name.lower()]
    assert len(flyway_components) >= 1
    assert flyway_components[0].stereotype == "database_migration"
    
    # Should detect migration scripts
    assert len([c for c in components if c.stereotype == "sql_script"]) >= 2


def test_sql_script_detection(temp_project):
    """Test standalone SQL script detection."""
    scripts = temp_project / "database" / "scripts"
    scripts.mkdir(parents=True)
    
    (scripts / "init_schema.sql").write_text("""
CREATE SCHEMA IF NOT EXISTS app_schema;

CREATE TABLE app_schema.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2)
);
""")
    
    (scripts / "stored_procedures.sql").write_text("""
CREATE OR REPLACE FUNCTION get_user_count()
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM users);
END;
$$ LANGUAGE plpgsql;
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.database_collector import DatabaseCollector
    
    collector = DatabaseCollector(temp_project, "infrastructure")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect SQL scripts
    sql_scripts = [c for c in components if c.stereotype == "sql_script"]
    assert len(sql_scripts) >= 2
    
    script_names = [c.name for c in sql_scripts]
    assert any("init_schema" in name.lower() for name in script_names)
    assert any("stored_procedures" in name.lower() or "procedure" in name.lower() for name in script_names)


def test_database_tables_extraction(temp_project):
    """Test extraction of table names from SQL scripts."""
    scripts = temp_project / "db"
    scripts.mkdir(parents=True)
    
    (scripts / "schema.sql").write_text("""
CREATE TABLE customers (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255)
);

CREATE TABLE orders (
    id BIGINT PRIMARY KEY,
    customer_id BIGINT REFERENCES customers(id),
    total DECIMAL(10, 2)
);

CREATE TABLE order_items (
    order_id BIGINT REFERENCES orders(id),
    product_id BIGINT,
    quantity INTEGER
);
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.database_collector import DatabaseCollector
    
    collector = DatabaseCollector(temp_project, "infrastructure")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect database component
    db_components = [c for c in components if c.stereotype == "database_schema"]
    assert len(db_components) >= 1
    
    # Should track table names in evidence
    all_evidence_texts = [ev.reason.lower() for ev in evidence.values()]
    assert any("customers" in text for text in all_evidence_texts)
    assert any("orders" in text for text in all_evidence_texts)


def test_liquibase_yaml_format(temp_project):
    """Test Liquibase YAML changelog support."""
    changelog_dir = temp_project / "src" / "main" / "resources" / "db" / "changelog"
    changelog_dir.mkdir(parents=True)
    
    (changelog_dir / "changelog.yaml").write_text("""
databaseChangeLog:
  - changeSet:
      id: 1
      author: developer
      changes:
        - createTable:
            tableName: accounts
            columns:
              - column:
                  name: id
                  type: bigint
                  autoIncrement: true
                  constraints:
                    primaryKey: true
              - column:
                  name: balance
                  type: decimal(19,2)
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.database_collector import DatabaseCollector
    
    collector = DatabaseCollector(temp_project, "infrastructure")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect Liquibase component
    liquibase_components = [c for c in components if "liquibase" in c.name.lower()]
    assert len(liquibase_components) >= 1


def test_flyway_config_detection(temp_project):
    """Test Flyway configuration file detection."""
    (temp_project / "flyway.conf").write_text("""
flyway.url=jdbc:postgresql://localhost:5432/mydb
flyway.user=dbuser
flyway.password=secret
flyway.locations=filesystem:db/migration
""")
    
    migrations = temp_project / "db" / "migration"
    migrations.mkdir(parents=True)
    (migrations / "V1__init.sql").write_text("CREATE TABLE test (id INT);")
    
    from src.aicodegencrew.pipelines.architecture_facts.database_collector import DatabaseCollector
    
    collector = DatabaseCollector(temp_project, "infrastructure")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect Flyway with config
    flyway_components = [c for c in components if "flyway" in c.name.lower()]
    assert len(flyway_components) >= 1
    
    # Should have evidence of config file
    flyway_evidence = [evidence[eid] for eid in flyway_components[0].evidence_ids if eid in evidence]
    assert any("flyway.conf" in ev.reason.lower() for ev in flyway_evidence)


def test_multiple_database_systems(temp_project):
    """Test detection of multiple database migration systems."""
    # Liquibase
    liquibase_dir = temp_project / "src" / "main" / "resources" / "liquibase"
    liquibase_dir.mkdir(parents=True)
    (liquibase_dir / "changelog.xml").write_text("""<?xml version="1.0"?>
<databaseChangeLog xmlns="http://www.liquibase.org/xml/ns/dbchangelog">
</databaseChangeLog>
""")
    
    # Flyway
    flyway_dir = temp_project / "src" / "main" / "resources" / "db" / "migration"
    flyway_dir.mkdir(parents=True)
    (flyway_dir / "V1__init.sql").write_text("CREATE TABLE test (id INT);")
    
    from src.aicodegencrew.pipelines.architecture_facts.database_collector import DatabaseCollector
    
    collector = DatabaseCollector(temp_project, "infrastructure")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect both systems
    migration_components = [c for c in components if c.stereotype == "database_migration"]
    assert len(migration_components) >= 2
    
    component_names = [c.name.lower() for c in migration_components]
    assert any("liquibase" in name for name in component_names)
    assert any("flyway" in name for name in component_names)


def test_no_false_positives(temp_project):
    """Test that non-database files don't create false positives."""
    # Create some random files
    (temp_project / "README.md").write_text("# Project")
    (temp_project / "data.json").write_text('{"key": "value"}')
    
    java_dir = temp_project / "src"
    java_dir.mkdir(parents=True)
    (java_dir / "Main.java").write_text("public class Main {}")
    
    from src.aicodegencrew.pipelines.architecture_facts.database_collector import DatabaseCollector
    
    collector = DatabaseCollector(temp_project, "infrastructure")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should not detect any database components
    assert len(components) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
