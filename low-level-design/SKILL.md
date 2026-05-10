---
name: low-level-design
description: Generates a highly modular Low-Level Design (LLD) document from product requirements. Use when the user asks to create an architecture blueprint, design software packages, define APIs, or structure a codebase.
---

# Low-Level Design (LLD) Generator

This skill ensures you design robust, strictly decoupled architectures that enforce single responsibilities and clean dependency graphs.

## Core Principles

When asked to create an LLD, enforce these principles immediately:

1. **Strictly Decoupled Packages**: Break core logic into separate, independent packages (e.g., `Engine`, `Storage`, `Network`). These foundational packages must **not** depend laterally on one another.
2. **Domain Layer at the Bottom**: House all shared entities, cross-platform data models, and protocols in a dedicated `Domain` package. The foundational packages depend *downward* on this Domain package to share a common language without direct coupling.
3. **The Orchestrator**: Introduce an orchestrator package (e.g., `AppKit` or `CoreOrchestrator`) that sits above the foundational packages. It handles the lifecycle and coordinates data flow between them.
4. **Platform Isolation**: Keep UI and platform-specific logic (e.g., macOS global hotkeys, iOS views) strictly contained in their own platform packages that depend on the orchestrator.
5. **Modern API Patterns**: Utilize up-to-date framework capabilities (e.g., `@Observable` instead of verbose Combine subscriptions) for package APIs, and define distinct errors within each package instead of a global error enum.

## Workflows

**1. Analyze Requirements**
- Read the PRD/requirements.
- Identify the necessary domains (e.g., persistence, external APIs, core logic).

**2. Define the Package Architecture**
- Extract shared entities to `Domain`.
- Propose the independent foundational packages.
- Detail the Orchestrator package.
- Detail Platform-specific packages.

**3. Define APIs**
- Draft the public protocols and computed properties each package will expose.
- Ensure state updates are observable by the UI.

**4. External Dependencies & Fallbacks**
- When designing complex native features (e.g., system-level text insertion, background tasks), check if a reliable, single-purpose open-source package exists.
- If no dominant package exists, prioritize adapting well-tested implementations from open-source applications (like FluidVoice) over using incomplete wrapper libraries.

## Review Checklist

Before finalizing your LLD, verify:
- [ ] Are foundational packages free of lateral dependencies?
- [ ] Are all shared models housed in the central Domain layer?
- [ ] Are the APIs observable and modern?
- [ ] Are third-party dependencies robust and necessary?
