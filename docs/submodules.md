# Git submodules

## Registered remotes and pins

| Path | HTTPS remote | Initial pinned commit |
|---|---|---|
| `projects/construct` | `https://github.com/huynhli/Construct.git` | `fa20d3d77b9dc136408c5fb07ca974322c8f6206` |
| `projects/multiyt2mp3` | `https://github.com/huynhli/MultiYt2Mp3.git` | `35f10f4484281176a4af667222658a5eb23ec006` |
| `projects/nearestnews` | `https://github.com/huynhli/NearestNews.git` | `10663fa97b13ba9f3d771ae2d8f3efb9730e2e40` |
| `projects/reactgowebsitetemplate` | `https://github.com/huynhli/ReactGoWebsiteTemplate.git` | `d108f6de6d04bbdf718483a7e8d51d1a90272fa8` |
| `projects/scholarlysources` | `https://github.com/huynhli/ScholarlySources.git` | `6a706365202431b9c87a592c46c2c214c445c2b1` |
| `projects/portfoliowebsite` | `https://github.com/huynhli/portfolioWebsite.git` | `dead031ebb3d8f824bbf9ec64d247cc3f23a351d` |
| `projects/searchme` | `https://github.com/huynhli/SearchMe.git` | `91f816f74e3bc9cedb2ab0e461741eb07301129f` (local, not pushed) |

Each URL is stored in `.gitmodules`; parent Git records the commit through the index gitlink. The initial commits were reachable from the public remote `main` branch when registered. SearchMe contains a new local implementation commit and cannot be fetched by other clones until it is pushed with later authorization. The original `Construct`, `NearestNews`, and `ScholarlySources` working copies were on older commits; their parent pointers intentionally use current reachable remote commits. `MultiYt2Mp3` had uncommitted local source work not included in the remote commit, and that content was not copied.

## Clone and initialize

```bash
git clone --recurse-submodules <MONOREPO_URL>
```

For an existing clone:

```bash
git submodule update --init --recursive
```

Normal builds use exactly the pinned commits. They do not run `git pull` or update a submodule.

## Advance one project

After confirming the parent and selected submodule have no unrelated staged/working changes, run:

```bash
python scripts/update_submodule.py scholarlysources --ref main
```

The script fetches the selected branch from that submodule's HTTPS `origin`, checks out the resolved commit detached, and stages only the parent gitlink. It does not commit or push. Review the changed project metadata and generated index/routes before committing the parent repository.

Submodule source is upstream-owned. Make fixes in the original project repository and push them separately before advancing its parent pointer. The parent build stages tracked content from the pinned commit and refuses a dirty submodule worktree.
