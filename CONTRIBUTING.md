# Contributing to Bharat-RAG

Thanks for your interest in contributing to **Bharat-RAG**!  
This project is in an early design phase, so contributions around **architecture, protocol design, and documentation** are especially valuable.

---

## Project Philosophy

- **Protocol-first**: The Bharat-RAG Protocol (BRP) is the foundation.
- **Clean architecture**: SOLID principles, clear separation of concerns.
- **Cloud-neutral & India-centric**: Should work on-prem, on any cloud, and for Indian use-cases.

---

## Branching & Workflow

### Default Branch

- `main` is **protected** and should always remain stable.
- No direct commits to `main`. All changes go through pull requests.

### Feature Branches

1. Create a new branch from `main`:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/my-feature-name
