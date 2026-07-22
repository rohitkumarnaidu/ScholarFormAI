<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Distribution Checklist — ScholarForm AI v1.0 Launch

---

## GitHub Trending

- [ ] Ensure `README.md` has a clear, scannable header with badges and demo GIF/screenshot
- [ ] Add a `docs/` link prominently in the README
- [ ] Verify all CI badges are showing "passing" (26 workflows)
- [ ] Pin a "v1.0 Launch" issue as a discussion thread
- [ ] Add `Open Source`, `AI`, `Academic` topics to the repo
- [ ] Post `Show and Tell` in GitHub Discussions
- [ ] Ensure `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` are all present (✅ done)
- [ ] Check that `CITATION.cff` is up to date with v1.0

---

## Awesome Lists

### awesome-python
- [ ] Submit PR adding ScholarForm AI under "Academic Tools" or "Document Processing"
- [ ] Description: "Open-source AI-powered academic manuscript formatting with 17 journal templates"
- [ ] Ensure repo has an `awesome`-friendly README (clear description, badges)

### awesome-selfhosted
- [ ] Submit PR adding ScholarForm AI under "Document Management" or "Publishing"
- [ ] Include Docker deployment instructions in `README.md`
- [ ] Note that Ollama backend supports fully offline/self-hosted operation
- [ ] Point to `deploy/` directory for Docker Compose configs

### awesome-academia
- [ ] Submit PR as "Academic Writing Tools" or "Manuscript Preparation"
- [ ] Highlight: 17 templates, multi-doc synthesis, AI generator
- [ ] Include link to docs

### awesome-ai-papers (or similar)
- [ ] Submit PR mentioning LLM pipeline (NVIDIA NIM, Groq, Ollama) and RAG (ChromaDB)

---

## Open Source Directories

### OpenSource.net (formerly SourceForge.net)
- [ ] Create project page
- [ ] Category: "Science and Engineering" → "Academic Publishing"
- [ ] Tags: manuscript-formatting, academic-writing, ai, python, nextjs
- [ ] Screenshots: upload 2–3 (formatter UI, live preview, template selection)
- [ ] Link to GitHub repo and documentation

### OSDN (Open Source Development Network)
- [ ] Register project in "Academic / Education" category
- [ ] Add Japanese translation of description if possible (large OSDN audience)

### SourceForge
- [ ] Mirror the repo (or link to GitHub)
- [ ] Set up file releases for tarballs if desired

### Bitbucket
- [ ] Create a mirror repo (optional, some teams prefer Bitbucket)
- [ ] Keep synced via GitHub Action

### GitLab (optional)
- [ ] Mirror to GitLab.com for European reach

---

## Docker Hub

- [ ] Publish official Docker image to Docker Hub (`rohitkumarnaidu/ScholarFormAI`)
- [ ] Update `README.md` with Docker Pull badge
- [ ] Ensure Docker Compose files are in `backend/docker/docker-compose.yml`
- [ ] Add Docker tags: `latest`, `1.0.0`, `1.0`, `stable`
- [ ] Add automated builds via GitHub Actions → Docker Hub
- [ ] Include multi-arch builds (linux/amd64, linux/arm64)
- [ ] Write Docker Hub description with usage examples

**Current status:** Images are published to `ghcr.io` with Cosign signing. Ensure Docker Hub mirror is also configured.

---

## Package Registries

### PyPI (Python Package Index)
- [ ] Publish `scholarform-ai` or `scholarform-backend` package
- [ ] Include CLI entry point if applicable
- [ ] Ensure `pyproject.toml` has correct metadata (v1.0, license, classifiers)
- [ ] Classifiers: `Framework :: FastAPI`, `Topic :: Scientific/Engineering`, `License :: OSI Approved :: MIT License`
- [ ] Add installation instructions to README: `pip install scholarform-ai`

### npm
- [ ] Publish `@scholarform/frontend` or `scholarform-ui`
- [ ] Ensure `package.json` has correct metadata (version 1.0.0, license, keywords)
- [ ] Include `README.md` in the package
- [ ] Classifiers: `Academic`, `Manuscript Formatting`

---

## Newsletters

### Python Weekly
- [ ] Submit via [pythonweekly.com/submit](https://pythonweekly.com/submit)
- [ ] Subject: "ScholarForm AI v1.0 — Open-source academic manuscript formatting"
- [ ] Body: 3–4 sentence summary with link to GitHub repo
- [ ] Angle: "Built with FastAPI + Celery, this open-source tool formats academic papers to any journal style"

### JavaScript Weekly
- [ ] Submit via [javascriptweekly.com/submit](https://javascriptweekly.com/submit)
- [ ] Subject: "ScholarForm AI v1.0 — Next.js 16 + React 19 academic formatting platform"
- [ ] Angle: "Showcases Next.js 16 App Router, React 19, TanStack Query, real-time WebSocket preview"

### This Week in React
- [ ] Submit via [thisweekinreact.com](https://thisweekinreact.com)
- [ ] Highlight: React 19, Next.js 16, Server Components, WebSocket streaming for live preview

### DevOps Weekly
- [ ] Submit via [devopsweekly.com](https://devopsweekly.com)
- [ ] Angle: "26 CI/CD workflows, Cosign-signed containers, SLSA L3 provenance, SBOMs, multi-arch Docker builds"
- [ ] Include architecture diagram link

### Changelog (podcast + newsletter)
- [ ] Submit as "Open Source Friday" candidate
- [ ] Pitch: "Open-source tool that saves academics hours of formatting time — built with FastAPI, Next.js, and AI"

### PyCoder's Weekly
- [ ] Submit via [pycoders.com/submit](https://pycoders.com/submit)
- [ ] Python angle: FastAPI, Celery, ChromaDB, pipeline architecture, 382 packages

### Papers with Code (optional)
- [ ] Create a "Papers with Code" entry for the RAG/agent systems
- [ ] Category: "Natural Language Processing" → "Document Generation"

### Academic newsletters (optional)
- [ ] Authentic Research (authentic-research.substack.com)
- [ ] The Research Scientist (research-scientist.com)
- [ ] Nature Briefing (nature.com/briefing/signup) — submit via their tip line

---

## Social Launch Sequence (Timeline)

| Day | Action |
|-----|--------|
| D-7 | Pre-announce to core contributors and beta testers |
| D-3 | Submit to newsletters (most need 3-5 day lead time) |
| D-1 | Submit to Product Hunt for scheduled launch |
| D-0 | **Launch Day** — Push all social media posts, Reddit, HN, Dev.to |
| D+1 | Reply to comments and questions; monitor GitHub issues |
| D+3 | Submit to Awesome Lists and Open Source Directories |
| D+7 | Post-launch retrospective and v1.1 roadmap preview |

---

## Launch Metrics to Track

- [ ] GitHub stars (target: 100+ in first week)
- [ ] GitHub clones and unique visitors (Insights → Traffic)
- [ ] Docker Hub pulls
- [ ] PyPI downloads
- [ ] Website sign-ups (if demo is live)
- [ ] Newsletter click-through rates
- [ ] Product Hunt upvotes
- [ ] HN upvotes and comments
- [ ] Reddit upvotes and cross-post reach
- [ ] New issues and PRs submitted
- [ ] New contributors (first-time PRs)

## Pre-Launch Checks

- [ ] All 26 CI/CD workflows green on `main`
- [ ] `CHANGELOG.md` reflects v1.0 accurately
- [ ] `README.md` badges are all correct
- [ ] `CITATION.cff` version = 1.0.0, date = 2026-07-21
- [ ] Demo instance (if any) is deployed and stable
- [ ] No outstanding critical or high-severity issues
- [ ] All 80+ docs are up to date
- [ ] Release tag `v1.0.0` is pushed
- [ ] Release notes are drafted on GitHub
