# Adding projects

Use the onboarding command from the monorepo root:

```bash
python scripts/add_project.py --repo https://github.com/OWNER/new-project.git --slug new-project
```

The script verifies the public HTTPS remote, adds it under `projects/new-project`, inspects committed README/package/Go/Python metadata, creates a parent-owned manifest proposal, validates the registry, regenerates Nginx/Compose, rebuilds search documents/vectors, and stages the submodule pointer plus manifest. It never pushes or edits the original repository. If the README is absent, it generates explicit review prompts rather than inventing project features.

Before publishing, review `config/projects/new-project.json` and fill in verified:

- Summary, description, domain, features, technologies, aliases, and curated suggestions.
- Only real section titles and stable anchor IDs.
- Approved public documentation paths.
- Frontend package/build command, public base, router basename support, and API prefix. The default is not to build or publish a project frontend.
- Backend language/framework, upstream API prefix, health path, ports, environment variable names, database/persistent storage needs, and whether it fits local Compose or Render.

Then run:

```bash
python scripts/validate_projects.py
python scripts/build_frontends.py
python scripts/generate_nginx.py
python scripts/generate_compose.py
```

`build_frontends.py` builds only committed submodule files in a temporary directory using `git archive`; staged adjustments are discarded with that temporary directory. Submodule source worktrees are not patched. Parent-owned adapters may adjust a temporary build copy; the PortfolioWebsite/SearchMe launcher is the only such adapter. Any lasting upstream behavior change belongs in the original repository.
