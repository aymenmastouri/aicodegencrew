"""
Java version upgrade rules (declarative).

Generic rules for Java major version upgrades.
Scans for patterns in any Java project.
"""

from .base import (
    UpgradeRule, UpgradeRuleSet, CodePattern,
    UpgradeSeverity, UpgradeCategory,
)


# =============================================================================
# Java 17 -> 21
# =============================================================================

JAVA_17_TO_21 = UpgradeRuleSet(
    framework="Java",
    from_version="17",
    to_version="21",
    required_dependencies={
        "java": ">=21",
    },
    verification_commands=["java -version", "./gradlew build", "mvn verify"],
    rules=[
        UpgradeRule(
            id="java21-security-manager-removed",
            title="SecurityManager removed",
            description="SecurityManager and related APIs are removed in Java 21.",
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.API_CHANGE,
            from_version="17", to_version="21",
            detection_patterns=[
                CodePattern(
                    name="security_manager",
                    file_glob="*.java",
                    regex=r"SecurityManager|System\.setSecurityManager|System\.getSecurityManager",
                    description="SecurityManager API usage",
                ),
            ],
            migration_steps=[
                "1. Remove SecurityManager usage entirely",
                "2. Replace with modern security mechanisms (e.g., module system, agent-based)",
                "3. Review third-party libraries that may use SecurityManager",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=30,
        ),
        UpgradeRule(
            id="java21-finalization-deprecated",
            title="Object.finalize() deprecated for removal",
            description="finalize() is deprecated for removal. Use Cleaner or try-with-resources.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.API_CHANGE,
            from_version="17", to_version="21",
            detection_patterns=[
                CodePattern(
                    name="finalize_method",
                    file_glob="*.java",
                    regex=r"protected\s+void\s+finalize\s*\(",
                    description="finalize() method override",
                ),
            ],
            migration_steps=[
                "1. Replace finalize() with AutoCloseable + try-with-resources",
                "2. For native resources, use java.lang.ref.Cleaner",
                "3. Remove @SuppressWarnings(\"deprecation\") for finalize",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=30,
        ),
        UpgradeRule(
            id="java21-record-patterns",
            title="Record patterns available (Java 21)",
            description="Java 21 finalizes record patterns and pattern matching for switch.",
            severity=UpgradeSeverity.OPTIONAL,
            category=UpgradeCategory.SYNTAX,
            from_version="17", to_version="21",
            detection_patterns=[
                CodePattern(
                    name="instanceof_cast",
                    file_glob="*.java",
                    regex=r"instanceof\s+\w+\s*\)\s*\{\s*\n\s*\w+\s+\w+\s*=\s*\(\w+\)",
                    description="instanceof followed by cast (can use pattern matching)",
                ),
            ],
            migration_steps=[
                "1. Replace instanceof+cast with pattern matching: if (obj instanceof String s)",
                "2. Use switch pattern matching for type checks",
                "3. Optional: convert POJOs to records where applicable",
            ],
            affected_stereotypes=["service", "entity"],
            effort_per_occurrence=5,
        ),
        UpgradeRule(
            id="java21-gradle-version",
            title="Gradle version compatibility for Java 21",
            description="Java 21 requires Gradle 8.4+ for full support.",
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.BUILD_CONFIG,
            from_version="17", to_version="21",
            detection_patterns=[
                CodePattern(
                    name="gradle_wrapper_old",
                    file_glob="gradle-wrapper.properties",
                    regex=r"gradle-[0-7]\.|gradle-8\.[0-3]",
                    description="Gradle below 8.4",
                ),
            ],
            migration_steps=[
                "1. Update Gradle wrapper: ./gradlew wrapper --gradle-version=8.7",
                "2. Review build.gradle for deprecated Gradle APIs",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=30,
        ),
        UpgradeRule(
            id="java21-maven-compiler",
            title="Maven compiler plugin for Java 21",
            description="Maven compiler plugin needs update for Java 21.",
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.BUILD_CONFIG,
            from_version="17", to_version="21",
            detection_patterns=[
                CodePattern(
                    name="maven_compiler_source",
                    file_glob="pom.xml",
                    regex=r"<source>17</source>|<release>17</release>",
                    description="Maven compiler source version 17",
                ),
                CodePattern(
                    name="maven_java_version",
                    file_glob="pom.xml",
                    regex=r"<java\.version>17</java\.version>",
                    description="Maven java.version property set to 17",
                ),
            ],
            migration_steps=[
                "1. Update <java.version>21</java.version>",
                "2. Update maven-compiler-plugin to 3.12+",
                "3. Set <source>21</source> and <target>21</target>",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=15,
        ),
    ],
)


# =============================================================================
# Combined export
# =============================================================================

JAVA_UPGRADE_RULES: list = [
    JAVA_17_TO_21,
]
