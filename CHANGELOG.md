# Changelog

All notable changes to this project will be documented in this file.

## [0.3.1] - 2026-02-28

### Added
- Added release date and downloads badges to README.

### Fixed
- Fixed internal project version consistency in `pyproject.toml`.

## [0.3.0] - 2026-02-06

### Added
- Auto-install support for uv and Python in run scripts (where possible).
- License file (MIT).

### Changed
- Run scripts now use uv consistently for dependency install and execution.
- Safer handling of cross-platform venvs between Windows and WSL/Linux.

## [0.2.0] - 2026-01-16

### Added
- **Portable Tor Integration**: Tor is now bundled directly with the application, removing the need for external installation.
- **Multi-platform Bundling**: Support for dropping platform-specific Tor binaries in `bin/windows`, `bin/linux`, and `bin/macos`.
- **Automatic Process Management**: The application automatically launches and manages the Tor background process.
- **Improved UX**: New visual loading screens for Tor connection ("Connecting...", "Success", "Error").
- **Visual Feedback**: Tor button now changes color (Orange for connecting, Green for active).

### Changed
- Refactored `TorManager` to support automatic binary detection.
- Updated `config.json` to be environment-agnostic.
- Removed invalid `setProxy` calls preventing application crash.

### Fixed
- Fixed `WinError 10061` connection refused by auto-launching Tor.
- Fixed Windows compatibility issue with `stem` library (timeout argument).
- Fixed application crash when toggling Tor due to QWebEngineProfile error.

## [0.1.0] - 2026-01-15
### Initial Release
- Basic browsing functionality.
- Tabbed interface.
- Camera/Microphone software toggles.
- Basic Tor toggle (requires external Tor).
