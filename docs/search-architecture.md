# Search architecture

## Data flow

1. Parent-owned JSON manifests describe projects and verified sections.
2. `scripts/build_search_index.py` validates the registry and reads only explicitly approved README introductions (no source-tree crawling, private configuration, model corpus, or generated dependencies).
3. It creates deterministic project and section records with overview and anchor URLs. The artifact hash is based on serialized document content.
4. `@huggingface/transformers` generates normalized 384D vectors using `onnx-community/all-MiniLM-L6-v2-ONNX`, repository revision `aff7a1dc4e8a1ea593e6ea21e95c22ef0a25966f`, `q4` ONNX weights, mean pooling, and normalization. The embedding model is downloaded during build into the ignored `.hf-cache/` and is not copied into the page's initial bundle.
5. The submitted browser query is embedded in a dedicated Web Worker using the exact same model revision, dtype, pooling, and normalization. The first semantic query downloads the model into Transformers.js browser cache. Later queries reuse the worker. The ONNX Runtime WASM binary and factory are fetched lazily from a version-pinned jsDelivr path; this avoids bundling a 26.9 MB file that exceeds Cloudflare's 25 MiB static asset limit. Cloudflare's current limit is documented in its [Workers platform limits](https://developers.cloudflare.com/workers/platform/limits/).
6. The client computes cosine similarity against static document vectors and combines ranks with lexical retrieval.

The ONNX model is Apache-2.0 licensed. Transformers.js supports feature extraction with mean pooling/normalization and quantized ONNX variants; the implementation follows those documented APIs ([feature extraction](https://huggingface.co/docs/transformers.js/api/pipelines), [quantized dtypes](https://huggingface.co/docs/transformers.js/guides/dtypes)).

## Record schema

`documents.json` holds:

- `meta`: schema version, content hash, document/project counts, model ID/revision/dimensions, and curated suggestions.
- `documents[]`: stable `id`, `project_id`, `slug`, `kind` (`project` or `section`), title, summary, bounded searchable text, technologies, keywords, valid `url`, and nullable `application_url`.

`embeddings.json` is keyed by the exact document ID. It records model ID, commit revision, dimensions, normalization and index hash. The client rejects a vector file whose model/index metadata does not match the document index.

`projects.json` contains only display fields used by `/work/{slug}/` pages. `built-frontends.json` contains only successful static app builds, which gates application links. Autocomplete suggestions are drawn from actual project names, section titles, technology terms, aliases, and curated query phrases.

## Ranking

- Lexical scoring weights exact project-name/slug matches most highly, then title, keyword, normalized text, prefix, and one-edit fuzzy matches.
- Vector ranking uses cosine similarity. A vector candidate is admitted at similarity `>= 0.27`, or whenever it also has a lexical match.
- Lexical and vector results are combined with reciprocal rank fusion: `0.65/(60 + lexical_rank) + 0.35/(60 + vector_rank)`. This avoids adding uncalibrated raw score ranges. Exact project title and slug matches receive explicit boosts.
- Results are deduplicated into one project row, with ranked section links listed under that row. If embedding load/inference fails, the same index continues to provide lexical results and the UI reports the fallback.

## Index safety and lifecycle

Approved inputs are limited to `approved_docs` in each manifest, currently README files. Only the opening description is read; code fences are discarded and common secret-like assignments are redacted. All other searchable details are deliberately curated in parent-owned manifests. Search artifacts are stable for identical content and are public static deployment files. Rebuild after project metadata/submodule changes; never automatically move a submodule during a release build.

Commands:

```powershell
python scripts/validate_projects.py
python scripts/build_search_index.py
npm --prefix projects/searchme test
```
