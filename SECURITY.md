# Security Policy

## Supported Versions

Security fixes are released for the latest minor version of SEMARC. Generated projects are
yours after generation: when a fix affects generated code, the release notes explain what to
change in existing projects.

## Reporting a Vulnerability

Please report vulnerabilities privately through
[GitHub Security Advisories](https://github.com/byterings/semarc/security/advisories/new).
Do not open a public issue.

Include the SEMARC version, the target (PHP, FastAPI, NestJS, ...), a minimal `.sem`
specification and the steps to reproduce. You will get an acknowledgement within 5 working
days and a plan for a fix after triage.

## Scope

In scope:

- the compiler (lexer, parser, validator, architecture passes, generators)
- security behaviour of generated projects: authentication, authorization, ownership checks,
  validation, rate limiting, secrets handling and default configuration

Out of scope: vulnerabilities in third-party frameworks and libraries that generated projects
depend on (report those upstream), and changes you made to a generated project.
