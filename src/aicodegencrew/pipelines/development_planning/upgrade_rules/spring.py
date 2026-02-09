"""
Spring Boot upgrade rules (declarative).

Generic rules for Spring Boot major version upgrades.
Scans for patterns in any Spring Boot project.
"""

from .base import (
    UpgradeRule, UpgradeRuleSet, CodePattern,
    UpgradeSeverity, UpgradeCategory,
)


# =============================================================================
# Spring Boot 3.1 -> 3.2
# =============================================================================

SPRING_31_TO_32 = UpgradeRuleSet(
    framework="Spring",
    from_version="3.1",
    to_version="3.2",
    required_dependencies={
        "org.springframework.boot": "3.2.x",
    },
    verification_commands=["./gradlew build", "./gradlew test", "mvn verify"],
    rules=[
        UpgradeRule(
            id="spring32-restclient",
            title="RestTemplate -> RestClient (new)",
            description=(
                "Spring 3.2 introduces RestClient as modern replacement for RestTemplate. "
                "RestTemplate is not deprecated yet but RestClient is recommended."
            ),
            severity=UpgradeSeverity.RECOMMENDED,
            category=UpgradeCategory.API_CHANGE,
            from_version="3.1", to_version="3.2",
            detection_patterns=[
                CodePattern(
                    name="resttemplate_usage",
                    file_glob="*.java",
                    regex=r"RestTemplate",
                    description="RestTemplate usage (consider RestClient)",
                ),
            ],
            migration_steps=[
                "1. Replace RestTemplate with RestClient for new code",
                "2. RestClient.create() for simple usage",
                "3. RestClient.builder() for customized clients",
                "4. Existing RestTemplate code can remain (not deprecated)",
            ],
            affected_stereotypes=["service"],
            effort_per_occurrence=15,
        ),
        UpgradeRule(
            id="spring32-virtual-threads",
            title="Virtual Threads support (Java 21+)",
            description=(
                "Spring Boot 3.2 supports Java 21 virtual threads. "
                "Enable with spring.threads.virtual.enabled=true."
            ),
            severity=UpgradeSeverity.OPTIONAL,
            category=UpgradeCategory.MIGRATION,
            from_version="3.1", to_version="3.2",
            detection_patterns=[
                CodePattern(
                    name="thread_pool_config",
                    file_glob="*.java",
                    regex=r"ThreadPoolTaskExecutor|@Async",
                    description="Custom thread pool or @Async usage",
                ),
            ],
            migration_steps=[
                "1. Ensure Java 21+ is used",
                "2. Add spring.threads.virtual.enabled=true to application.properties",
                "3. Review custom ThreadPoolTaskExecutor configurations",
                "4. Test async operations with virtual threads",
            ],
            affected_stereotypes=["service", "controller"],
            effort_per_occurrence=10,
        ),
        UpgradeRule(
            id="spring32-observability",
            title="Micrometer Observation API changes",
            description="Spring 3.2 refactors observability. Some Micrometer APIs changed.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.API_CHANGE,
            from_version="3.1", to_version="3.2",
            detection_patterns=[
                CodePattern(
                    name="micrometer_timer",
                    file_glob="*.java",
                    regex=r"MeterRegistry|@Timed|Timer\.builder",
                    description="Micrometer metrics usage",
                ),
            ],
            migration_steps=[
                "1. Review Micrometer 1.12 changelog for API changes",
                "2. Update @Timed annotations if needed",
                "3. Check custom MeterRegistry configurations",
            ],
            affected_stereotypes=["service"],
            effort_per_occurrence=10,
        ),
    ],
)


# =============================================================================
# Spring Boot 3.2 -> 3.3
# =============================================================================

SPRING_32_TO_33 = UpgradeRuleSet(
    framework="Spring",
    from_version="3.2",
    to_version="3.3",
    required_dependencies={
        "org.springframework.boot": "3.3.x",
    },
    verification_commands=["./gradlew build", "./gradlew test", "mvn verify"],
    rules=[
        UpgradeRule(
            id="spring33-cds-support",
            title="CDS (Class Data Sharing) support",
            description="Spring 3.3 adds CDS support for faster startup. Optional optimization.",
            severity=UpgradeSeverity.OPTIONAL,
            category=UpgradeCategory.BUILD_CONFIG,
            from_version="3.2", to_version="3.3",
            detection_patterns=[
                CodePattern(
                    name="spring_main_class",
                    file_glob="*.java",
                    regex=r"@SpringBootApplication",
                    description="Spring Boot main class",
                ),
            ],
            migration_steps=[
                "1. Build with CDS: ./gradlew bootJar && java -Dspring.context.exit=onRefresh -jar app.jar",
                "2. Run with CDS: java -XX:SharedArchiveFile=app.jsa -jar app.jar",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=30,
        ),
        UpgradeRule(
            id="spring33-property-migration",
            title="Deprecated properties removed",
            description=(
                "Several deprecated Spring Boot properties were removed in 3.3. "
                "Check application.properties/yml for removed keys."
            ),
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.MIGRATION,
            from_version="3.2", to_version="3.3",
            detection_patterns=[
                CodePattern(
                    name="deprecated_properties",
                    file_glob="application*.properties",
                    regex=r"spring\.jpa\.hibernate\.ddl-auto|spring\.datasource\.initialization-mode|management\.metrics\.export",
                    description="Potentially deprecated Spring property",
                ),
                CodePattern(
                    name="deprecated_properties_yml",
                    file_glob="application*.yml",
                    regex=r"initialization-mode:|metrics:\s*\n\s*export:",
                    description="Potentially deprecated Spring property (YAML)",
                ),
            ],
            migration_steps=[
                "1. Run: java -jar app.jar --spring.config.additional-location=... to detect warnings",
                "2. Replace deprecated property keys with new equivalents",
                "3. See Spring Boot 3.3 release notes for property mapping",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=10,
        ),
    ],
)


# =============================================================================
# Spring Boot 3.3 -> 3.4
# =============================================================================

SPRING_33_TO_34 = UpgradeRuleSet(
    framework="Spring",
    from_version="3.3",
    to_version="3.4",
    required_dependencies={
        "org.springframework.boot": "3.4.x",
    },
    verification_commands=["./gradlew build", "./gradlew test", "mvn verify"],
    rules=[
        UpgradeRule(
            id="spring34-structured-logging",
            title="Structured logging support",
            description="Spring 3.4 adds structured logging (JSON format). Optional migration.",
            severity=UpgradeSeverity.OPTIONAL,
            category=UpgradeCategory.MIGRATION,
            from_version="3.3", to_version="3.4",
            detection_patterns=[
                CodePattern(
                    name="logback_config",
                    file_glob="logback*.xml",
                    regex=r"<configuration|<appender",
                    description="Custom Logback configuration",
                ),
                CodePattern(
                    name="log4j_config",
                    file_glob="log4j2*.xml",
                    regex=r"<Configuration|<Appenders",
                    description="Custom Log4j2 configuration",
                ),
            ],
            migration_steps=[
                "1. Add logging.structured.format.console=ecs to application.properties",
                "2. Review custom log patterns for JSON compatibility",
                "3. Update log parsing if using ELK/Splunk",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=20,
        ),
        UpgradeRule(
            id="spring34-mockmvc-assertions",
            title="MockMvc assertion changes",
            description="MockMvc now uses AssertJ assertions. Some test patterns may need updates.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.TEST_RUNNER,
            from_version="3.3", to_version="3.4",
            detection_patterns=[
                CodePattern(
                    name="mockmvc_usage",
                    file_glob="*Test.java",
                    regex=r"MockMvc|mockMvc\.perform",
                    description="MockMvc test usage",
                ),
            ],
            migration_steps=[
                "1. Review MockMvc test assertions for compatibility",
                "2. Consider using MockMvcTester (new AssertJ-based API)",
                "3. Existing andExpect() chains still work",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=5,
        ),
        UpgradeRule(
            id="spring34-flyway-10",
            title="Flyway 10+ compatibility",
            description="Spring Boot 3.4 supports Flyway 10. Check migration script compatibility.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.DEPENDENCY,
            from_version="3.3", to_version="3.4",
            detection_patterns=[
                CodePattern(
                    name="flyway_dependency",
                    file_glob="build.gradle",
                    regex=r"flyway|org\.flywaydb",
                    description="Flyway dependency",
                ),
                CodePattern(
                    name="flyway_dependency_maven",
                    file_glob="pom.xml",
                    regex=r"flyway|org\.flywaydb",
                    description="Flyway dependency (Maven)",
                ),
                CodePattern(
                    name="flyway_config",
                    file_glob="application*.properties",
                    regex=r"spring\.flyway\.",
                    description="Flyway configuration",
                ),
            ],
            migration_steps=[
                "1. Check Flyway 10 changelog for breaking changes",
                "2. Review Flyway callbacks if using FlywayCallback (deprecated)",
                "3. Update spring.flyway.* properties if needed",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=30,
        ),
    ],
)


# =============================================================================
# Cross-version: Jakarta EE Migration (Spring Boot 2.x -> 3.x)
# =============================================================================

SPRING_JAKARTA_MIGRATION = UpgradeRuleSet(
    framework="Spring",
    from_version="2",
    to_version="3",
    required_dependencies={
        "org.springframework.boot": "3.x",
        "java": ">=17",
    },
    verification_commands=["./gradlew build", "./gradlew test", "mvn verify"],
    rules=[
        UpgradeRule(
            id="spring3-javax-to-jakarta",
            title="javax.* -> jakarta.* namespace migration",
            description=(
                "Spring Boot 3 requires Jakarta EE 9+. All javax.* packages "
                "(servlet, persistence, validation, etc.) must migrate to jakarta.*."
            ),
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.MIGRATION,
            from_version="2", to_version="3",
            detection_patterns=[
                CodePattern(
                    name="javax_servlet",
                    file_glob="*.java",
                    regex=r"import\s+javax\.servlet",
                    description="javax.servlet imports",
                ),
                CodePattern(
                    name="javax_persistence",
                    file_glob="*.java",
                    regex=r"import\s+javax\.persistence",
                    description="javax.persistence imports (JPA)",
                ),
                CodePattern(
                    name="javax_validation",
                    file_glob="*.java",
                    regex=r"import\s+javax\.validation",
                    description="javax.validation imports",
                ),
                CodePattern(
                    name="javax_inject",
                    file_glob="*.java",
                    regex=r"import\s+javax\.inject",
                    description="javax.inject imports",
                ),
                CodePattern(
                    name="javax_annotation",
                    file_glob="*.java",
                    regex=r"import\s+javax\.annotation",
                    description="javax.annotation imports",
                ),
            ],
            migration_steps=[
                "1. Replace all javax.servlet -> jakarta.servlet",
                "2. Replace all javax.persistence -> jakarta.persistence",
                "3. Replace all javax.validation -> jakarta.validation",
                "4. Replace javax.inject -> jakarta.inject",
                "5. Replace javax.annotation -> jakarta.annotation",
                "6. Use OpenRewrite recipe: org.openrewrite.java.migrate.jakarta.JavaxMigrationToJakarta",
            ],
            schematic="openrewrite:org.openrewrite.java.migrate.jakarta.JavaxMigrationToJakarta",
            affected_stereotypes=["controller", "service", "repository", "entity"],
            effort_per_occurrence=2,
        ),
        UpgradeRule(
            id="spring3-java17-required",
            title="Java 17 minimum required",
            description="Spring Boot 3.x requires Java 17+.",
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.DEPENDENCY,
            from_version="2", to_version="3",
            detection_patterns=[
                CodePattern(
                    name="java_source_compat_gradle",
                    file_glob="build.gradle",
                    regex=r"sourceCompatibility\s*=.*(?:1\.[0-9]|1[0-6])\b",
                    description="Java source compatibility below 17 (Gradle)",
                ),
                CodePattern(
                    name="java_source_compat_maven",
                    file_glob="pom.xml",
                    regex=r"<java\.version>(?:1[0-6]|1\.[0-9])</java\.version>",
                    description="Java version below 17 (Maven)",
                ),
            ],
            migration_steps=[
                "1. Update Java to 17+",
                "2. Update build config: sourceCompatibility = JavaVersion.VERSION_17",
                "3. Review code for removed Java APIs (e.g., SecurityManager)",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=120,
        ),
        UpgradeRule(
            id="spring3-deprecated-websecurityconfigureradapter",
            title="WebSecurityConfigurerAdapter removed",
            description=(
                "WebSecurityConfigurerAdapter was removed in Spring Security 6. "
                "Use SecurityFilterChain @Bean instead."
            ),
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.API_CHANGE,
            from_version="2", to_version="3",
            detection_patterns=[
                CodePattern(
                    name="websecurity_adapter",
                    file_glob="*.java",
                    regex=r"WebSecurityConfigurerAdapter",
                    description="WebSecurityConfigurerAdapter usage",
                ),
            ],
            migration_steps=[
                "1. Remove extends WebSecurityConfigurerAdapter",
                "2. Create @Bean SecurityFilterChain method",
                "3. Move configure(HttpSecurity) logic to SecurityFilterChain bean",
                "4. Replace authorizeRequests() with authorizeHttpRequests()",
                "5. Replace antMatchers() with requestMatchers()",
            ],
            affected_stereotypes=["service"],
            effort_per_occurrence=60,
        ),
        UpgradeRule(
            id="spring3-antmatchers-removed",
            title="antMatchers() -> requestMatchers()",
            description="antMatchers/mvcMatchers removed in Spring Security 6. Use requestMatchers().",
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.API_CHANGE,
            from_version="2", to_version="3",
            detection_patterns=[
                CodePattern(
                    name="antmatchers",
                    file_glob="*.java",
                    regex=r"\.antMatchers\s*\(|\.mvcMatchers\s*\(",
                    description="antMatchers/mvcMatchers usage",
                ),
            ],
            migration_steps=[
                "1. Replace .antMatchers() with .requestMatchers()",
                "2. Replace .mvcMatchers() with .requestMatchers()",
                "3. Note: requestMatchers() auto-selects MVC or Ant matching",
            ],
            affected_stereotypes=["service"],
            effort_per_occurrence=5,
        ),
    ],
)


# =============================================================================
# Combined export
# =============================================================================

SPRING_UPGRADE_RULES: list = [
    SPRING_JAKARTA_MIGRATION,
    SPRING_31_TO_32,
    SPRING_32_TO_33,
    SPRING_33_TO_34,
]
