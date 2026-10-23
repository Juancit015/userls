# Spec Delta

## REMOVED Requirements

### Requirement: Read-only operation

**Reason**: Read-only operation previously allowed one exception, writing an
explicit export target. The export command is removed, so the exception is
replaced by a stricter requirement that permits no file writes.

**Migration**: Use stdout with shell redirection when a file is needed. No
command writes files on the user's behalf.

## ADDED Requirements

### Requirement: Read-only operation without file writes

The system MUST NOT create, modify, or delete accounts, passwords, groups, or
system files, and MUST NOT write any files.

#### Scenario: Listing performs no writes

- **WHEN** any listing or inspection command runs
- **THEN** no account database or system file is modified

#### Scenario: No command writes files

- **WHEN** any command runs
- **THEN** no file is created, modified, or deleted
