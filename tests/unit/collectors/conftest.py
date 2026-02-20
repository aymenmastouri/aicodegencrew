"""Shared fixtures for collector unit tests.

All fixtures create minimal but realistic repo structures in a tmp_path,
with no LLM calls and no external dependencies.
"""

import json
from pathlib import Path

import pytest

# =============================================================================
# Helpers
# =============================================================================


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """An empty temporary directory with no source files."""
    return tmp_path


@pytest.fixture
def spring_repo(tmp_path: Path) -> Path:
    """A minimal Spring Boot repo containing a controller, service, and repository.

    Layout::

        src/main/java/com/example/
            FooController.java   — @RestController + @GetMapping + @PostMapping
            FooService.java      — @Service
            Foo.java             — @Entity
            FooRepository.java   — @Repository + extends JpaRepository<Foo, Long>
    """
    java = tmp_path / "src" / "main" / "java" / "com" / "example"

    _write(
        java / "FooController.java",
        """\
package com.example;

import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/foo")
public class FooController {

    @GetMapping
    public List<String> list() {
        return List.of();
    }

    @PostMapping
    public String create(@RequestBody String body) {
        return "ok";
    }
}
""",
    )

    _write(
        java / "FooService.java",
        """\
package com.example;

import org.springframework.stereotype.Service;

@Service
public class FooService {
    public String doSomething() { return "done"; }
}
""",
    )

    _write(
        java / "Foo.java",
        """\
package com.example;

import javax.persistence.Entity;

@Entity
public class Foo {
    private Long id;
    private String name;
}
""",
    )

    _write(
        java / "FooRepository.java",
        """\
package com.example;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface FooRepository extends JpaRepository<Foo, Long> {
    List<Foo> findByName(String name);
}
""",
    )

    return tmp_path


@pytest.fixture
def angular_repo(tmp_path: Path) -> Path:
    """A minimal Angular repo containing a component, directive, service, and routing.

    Layout::

        angular.json             — signals Angular root
        src/app/
            foo.component.ts     — @Component (standalone=true, selector='app-foo')
            highlight.directive.ts — @Directive
            foo.service.ts       — @Injectable providedIn root
            app-routing.module.ts  — RouterModule.forRoot with eager + lazy routes
    """
    # angular.json at root signals Angular root to collectors
    (tmp_path / "angular.json").write_text('{"version": 1, "projects": {}}', encoding="utf-8")

    app = tmp_path / "src" / "app"

    _write(
        app / "foo.component.ts",
        """\
import { Component } from '@angular/core';

@Component({
  selector: 'app-foo',
  standalone: true,
  templateUrl: './foo.component.html',
})
export class FooComponent {
  title = 'foo';
}
""",
    )

    _write(
        app / "highlight.directive.ts",
        """\
import { Directive } from '@angular/core';

@Directive({
  selector: '[appHighlight]',
})
export class HighlightDirective {}
""",
    )

    _write(
        app / "foo.service.ts",
        """\
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class FooService {
  getData() { return []; }
}
""",
    )

    _write(
        app / "app-routing.module.ts",
        """\
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { FooComponent } from './foo.component';

const routes: Routes = [
  { path: '', component: FooComponent },
  {
    path: 'dashboard',
    loadChildren: () => import('./dashboard/dashboard.module').then(m => m.DashboardModule),
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
""",
    )

    return tmp_path


@pytest.fixture
def container_repo(tmp_path: Path) -> Path:
    """A repo with a Spring Boot backend (pom.xml) and Angular frontend (package.json).

    Layout::

        backend/
            pom.xml              — Spring Boot, JPA; two explicit dependencies
        frontend/
            package.json         — @angular/core runtime dep + @angular/cli dev dep
    """
    # Spring Boot backend
    backend = tmp_path / "backend"
    backend.mkdir()
    _write(
        backend / "pom.xml",
        """\
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
           http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>backend</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
      <version>3.2.0</version>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-data-jpa</artifactId>
      <version>3.2.0</version>
    </dependency>
  </dependencies>
</project>
""",
    )

    # Angular frontend
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        json.dumps(
            {
                "name": "frontend",
                "version": "1.0.0",
                "dependencies": {
                    "@angular/core": "^17.0.0",
                    "@angular/common": "^17.0.0",
                    "rxjs": "^7.8.0",
                },
                "devDependencies": {
                    "@angular/cli": "^17.0.0",
                    "typescript": "^5.2.0",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return tmp_path
