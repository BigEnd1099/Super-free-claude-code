---
name: security-auditor
description: "Scan code for security vulnerabilities including XSS, CSRF, SQL Injection, and insecure dependencies."
category: Security
tags: [security, audit, vulnerabilities]
risk: medium
version: 1.0.0
---

# Security Auditor

Perform deep security audits on codebases to identify and mitigate risks.

## Instructions
1. Identify all user input points (sinks).
2. Trace input through the system to execution points.
3. Check for proper sanitization and validation.
4. Review authentication and authorization logic.
5. Inspect dependencies for known CVEs.
