# session-inventory Specification

## Purpose

Reports the login sessions currently active on the host, with the identity,
terminal, login time, and origin of each session.

## Requirements

### Requirement: Active session listing

The system SHALL list every active session reported by `who`, showing user,
terminal, login time, and origin.

#### Scenario: Two sessions for one user

- **WHEN** one user has two active sessions
- **THEN** both sessions appear as separate rows

#### Scenario: No active sessions

- **WHEN** no sessions are active
- **THEN** the result is empty and the exit status is zero

### Requirement: Session source failure

When the session source is unavailable or fails, the system SHALL report the
failure on stderr and MUST NOT display invented sessions.

#### Scenario: who fails

- **WHEN** `who` exits with a non-zero status
- **THEN** the error names `who` and the exit status is non-zero
