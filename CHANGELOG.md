# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

## [Unreleased]

## [0.1.3] - 2025-12-18

### Changed

- Refactored test structure: moved `tests/django` to `tests/django_adapter` for better clarity

## [0.1.2] - 2025-12-18

### Added

- Django adapter (`litefs-django`) with SQLite database backend
- Primary detection delegation to core `PrimaryDetector`
- Django-specific settings reader with UPPER_CASE to snake_case mapping
- Unit tests for Django adapter components

## [0.1.1] - 2025-12-18

### Added

- Initial project setup

## [0.1.0] - 2025-12-18

### Added

- Initial release
