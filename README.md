# Weather-Aware Agricultural Decision Support System

## 1. Project Goal

This repository builds a weather-aware agricultural decision-support system for
short-cycle vegetables in the former Binh Dinh province, Vietnam, now part of Gia
Lai.

Target crops:

| Crop ID | Common Vietnamese Scope | Scientific Name |
| --- | --- | --- |
| `cai_xanh` | cải xanh / cải bẹ xanh | Brassica juncea |
| `ngo` | ngò / ngò rí / rau mùi | Coriandrum sativum |
| `cai_cuc` | cải cúc / tần ô | Glebionis coronaria |
| `rau_muong` | rau muống | Ipomoea aquatica |
| `xa_lach` | xà lách | Lactuca sativa |

The final system has two mandatory branches:

```text
Weather Model
        +
Agricultural RAG
        +
Farm Context
        |
        v
Agro-Weather / Decision Engine
        |
        v
Recommendation + Explanation + Evidence / Source
```

Both Weather and RAG must contribute to the final recommendation.

## 2. System Flow

```text
                         USER QUERY
                              |
                              v
                       USER/FARM CONTEXT
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
       WEATHER BRANCH                     RAG BRANCH
             |                                 |
       ECMWF Forecast                    Knowledge Discovery
             |                                 |
       Verification Data                 Validated Documents
             |                                 |
       ML/MOS Correction                 Retrieval
             |                                 |
             v                                 v
      Corrected Forecast                 Evidence
             |                                 |
             v                                 |
      Agro-Weather Features                    |
             |                                 |
             +----------------+----------------+
                              |
                              v
                       DECISION ENGINE
                              |
                              v
                       LLM EXPLANATION
                              |
                              v
                       FINAL RESPONSE
```

## 3. Weather Branch

The Weather branch is still part of the project and must not be removed or
de-prioritized.

Planned Weather pipeline:

```text
ECMWF forecast
        |
        v
verification data
        |
        v
run_time / valid_time / lead_time matching
        |
        v
ML/MOS correction
        |
        v
corrected forecast
        |
        v
agro-weather features
```

Static geography for the future Weather pipeline is kept under:

```text
data/weather/geography/
```

Do not commit GRIB/GRIB2, NetCDF, raw weather downloads, weather caches, or
temporary weather reports.

## 4. RAG Data Strategy

The old source-first approach is abandoned:

```text
choose a small website whitelist
-> crawl those websites
-> keep whatever appears useful
```

The current strategy is discovery first:

```text
knowledge need
        |
        v
discovery query
        |
        v
search broad web / scholarly sources
        |
        v
candidate documents
        |
        v
content relevance validation
        |
        v
source quality validation
        |
        v
download/process later
```

There is no hard domain whitelist during discovery. Stage A3 may query web or
scholarly search providers for candidate metadata, but it still does not approve
sources, crawl whole sites, download a document corpus, build embeddings, build
BM25, create vector databases, implement retrieval, or run Weather ML.

Current RAG acquisition roles:

```text
A1 = systematic query coverage
A2 = synthetic natural-language query coverage
A3 = document candidate discovery
A4 = source vetting (future)
```

## 5. Region Semantics

`search_region` is the geographic phrase added to a search query. It is only
query context.

`search_region` must not be interpreted as the real geographic origin,
applicability, or authority of a discovered document. Later stages may assign a
separate `document_region` after content review and source/local applicability
validation.

For A2 synthetic farmer-style queries, regional terms are appended as search
keywords such as `Việt Nam`, `Bình Định`, or `Gia Lai`, not as claims that the
future document is from that place.

Round 1 Vietnamese search contexts:

```text
NONE
VIETNAM
BINH_DINH_LEGACY
GIA_LAI_CURRENT
```

Round 1 English scholarly search contexts:

```text
GLOBAL
VIETNAM
```

Future regional gap-fill scopes are defined for use only after Coverage Audit
finds missing evidence:

```text
SOUTH_CENTRAL_COAST
MEKONG_DELTA
SOUTHEAST_VIETNAM
CENTRAL_HIGHLANDS
NORTH_CENTRAL_VIETNAM
RED_RIVER_DELTA
SOUTHEAST_ASIA
TROPICAL
GLOBAL
```

Round 1 does not generate Mekong Delta, South Central Coast, Red River Delta,
Southeast Asia, Tropical, or other gap-fill queries.

## 6. Stage A1, A2, and A3

### Stage A1: Discovery Query Bank V2 / Round 1

```text
config/crops.yaml
        |
        v
src/agri_rag/discovery.py
        |
        v
data/agri_rag/discovery/query_bank.csv
data/agri_rag/discovery/query_bank.jsonl
data/agri_rag/discovery/query_bank_summary.json
```

A1 creates a systematic query bank for crop/weather/action coverage. Round 1 is
deliberately smaller than the previous 11,288-query version. It combines:

```text
crop or crop group
        +
weather/agro-weather scenario
        +
effect-oriented phrase or relevant agricultural action
        +
optional search_region phrase
```

Scenario actions are curated per scenario, so the generator does not create a
meaningless full Cartesian product.

Each query record includes:

```text
query_id
search_round
language
channel
priority
query_kind
scope_type
crop_id
crop_name
crop_group
crop_term
weather_scenario
weather_factor
weather_term
effects
action
search_region
search_region_term
query
```

Effect-oriented rows use `action = NONE`.

### Stage A2: Farmer/Public Query Mining

A2 adds a synthetic natural Vietnamese farmer/public-question style layer on top
of A1. Its purpose is to improve query wording diversity before Stage A3
document discovery.

A2 does not claim to have mined real farmer questions unless public source data
exists. The repository currently has no real public-query dataset, so A2 output
is generated as `synthetic`.

Provenance classes:

```text
observed    = wording actually found in a public source; source_url required
transformed = derived from an observed query; parent_query_id required
synthetic   = generated from curated language patterns; no fake source allowed
```

A2 query schema:

```text
query_id
query_text
language
stage
query_origin
intent
scenario
action
crop_scope
crop_key
search_region
search_region_term
source_url
source_title
parent_query_id
```

A2 intent groups:

```text
irrigation_water
rain_effect
heat_sunlight
humidity_disease
fertilizer_weather
spraying_weather
planting_weather
weather_recovery
```

A2 uses curated templates and compatibility rules. It does not blindly combine
every crop, scenario, action, and region.

Current A2 quality gate:

```text
total A2 queries        : 246
queries with region     : 113
queries without region  : 133
observed                : 0
transformed             : 0
synthetic               : 246
```

During review, awkward mechanical wording was adjusted. In particular, A2 now
uses search-keyword regional suffixes instead of directly appending `ở <region>`
to every regional farmer-style question.

### Stage A3: Candidate Document Discovery V1

A3 takes the combined A1+A2 query bank and selects a controlled representative
subset before any live search is executed.

```text
query
        |
        v
search result
        |
        v
relevance check
        |
        v
fallback query variants if needed
        |
        v
candidate document
```

A3 discovers candidates only.

```text
candidate != approved RAG source
```

Source authority, local applicability, pesticide legality, scientific threshold
validity, and final acceptance belong to A4 and later validation stages.

A3 supports two logical discovery channels:

```text
web
scholarly
```

Vietnamese A1 web queries and A2 public-style queries are routed to `web`.
English research-oriented A1 queries are routed to `scholarly`. The two channel
paths are kept separate in code.

The selector is deterministic and uses:

```text
language
discovery channel
source stage
query origin
query kind
crop scope
crop key
weather scenario
action
search region
effective priority
```

The default selected subset is intentionally small compared with the full 3,732
query bank. The current dry-run selector result is:

```text
total query bank : 3732
selected queries : 96
skipped queries  : 3636
```

Current selected-query breakdown:

```text
web        : 72
scholarly  : 24
vi         : 72
en         : 24
A1         : 64
A2         : 32
action     : 34
effect     : 30
natural    : 32
crop group : 24
crop specific : 72
```

Regional breakdown:

```text
VIETNAM          : 33
BINH_DINH_LEGACY : 14
GIA_LAI_CURRENT  : 14
NONE             : 11
GLOBAL           : 24
```

`search_region` remains search context only. A3 does not create
`document_region` from query context.

A3 live web discovery uses the Brave Search API when `BRAVE_SEARCH_API_KEY` is
available. If no Brave key is configured, it falls back to `ddgs` text search.
Brave is optional; DDGS is the default no-key web-search fallback. Web discovery
keeps only search-result metadata such as URL, title, snippet, rank, and
provider. It does not download page contents yet. Scholarly discovery uses
Crossref metadata through the public works endpoint. If a provider is not
available or returns a network/rate-limit error, A3 fails clearly instead of
fabricating URLs.

A3 applies deterministic relevance rules before writing candidates. Web results
are checked using available search-result title and snippet/description.
Scholarly Crossref results are checked using available title, abstract, subject,
DOI, URL, and type metadata. URL/domain are preserved as metadata but are not
sufficient semantic evidence. A result must match crop identity and weather
scenario evidence, or crop/group identity plus strong agronomic effect/action
evidence. A crop name alone is not enough. Obvious crop-only noise such as
genetic diversity, molecular markers, row spacing, nitrogen dose, storage, or
antioxidant-only papers is filtered unless the metadata also contains relevant
weather/effect/action evidence.

Relevance labels are not source-authority decisions:

```text
direct_match
supporting_match
rejected_irrelevant
```

Rejected irrelevant records are counted in the A3 summary but are not written as
final candidates.

Live search errors are handled per original query. A zero-result provider
response does not abort the whole A3 run. Temporary provider errors are retried
conservatively and then recorded as query-local errors. If an original web query
returns no relevant candidate, A3 may try up to three deterministic fallback
variants:

```text
original
crop_scenario
crop_scenario_action
crop_weather_general
```

Fallback searches preserve the original `search_region` as provenance, but they
do not require local terms such as Binh Dinh or Gia Lai in every variant.

Candidate records include:

```text
candidate_id
url
canonical_url
title
title_status
snippet
source_domain
source_type
doi
abstract
subjects
relevance_status
relevance_score
relevance_reasons
matched_crop_terms
matched_scenario_terms
matched_action_terms
language
discovery_channel
query_id
original_query_id
original_query_text
search_variant_text
search_variant_type
query_text
crop_scope
crop_key
scenario
action
search_region
retrieved_at
raw_result_count
discovery_providers
languages
discovery_channels
source_stages
query_origins
query_references
```

A single canonical URL is written once, with all query provenance retained in
`query_references`.

## 7. Repository Structure

```text
KhoaLuan/
|
|-- AGENTS.md
|-- README.md
|-- requirements.txt
|-- .gitignore
|
|-- config/
|   `-- crops.yaml
|
|-- src/
|   |
|   |-- agri_rag/
|   |   |-- __init__.py
|   |   |-- candidate_discovery.py
|   |   `-- discovery.py
|   |
|   `-- weather/
|       `-- __init__.py
|
`-- data/
    |
    |-- agri_rag/
    |   |-- candidates/                         generated by live A3, ignored
    |   |   |-- candidate_documents.jsonl          generated, ignored
    |   |   `-- candidate_discovery_summary.json  generated, ignored
    |   |
    |   `-- discovery/
    |       |-- a2_public_queries.csv           generated, ignored
    |       |-- a2_public_queries.jsonl         generated, ignored
    |       |-- discovery_queries_combined.jsonl generated, ignored
    |       |-- query_bank.csv                  generated, ignored
    |       |-- query_bank.jsonl                generated, ignored
    |       `-- query_bank_summary.json         generated, ignored
    |
    `-- weather/
        `-- geography/
            |-- binh_dinh_geography_metadata.json
            |-- binh_dinh_location_registry.csv
            |-- binh_dinh_old_boundary.geojson
            `-- binh_dinh_weather_grid_025.geojson
```

Generated RAG outputs remain ignored by Git.

## 8. File Responsibilities

`AGENTS.md`

Persistent instructions for coding agents. It records project rules that should
survive across sessions, including the mandatory Weather + RAG direction,
cleaned-repository constraints, generated-data exclusions, RAG discovery
principles, crop scope, geographic scope, and scientific safety boundaries.

`README.md`

Project map. It documents the current system flow, repository tree, source-file
responsibilities, important input/output paths, how to run the current stage,
current status, and next stage.

`requirements.txt`

Python dependencies for the current stage. Stage A1/A2 currently requires PyYAML.

`.gitignore`

Keeps Python caches, local environments, secrets, raw weather datasets,
generated RAG data, indexes, models, caches, and temporary outputs out of Git.

`config/crops.yaml`

Single source of truth for the crop scope. It defines crop IDs, Vietnamese
names, scientific names, Vietnamese aliases, English aliases, and crop groups.

`src/agri_rag/__init__.py`

Marks `src.agri_rag` as a Python package. It has no runtime input or output.

`src/agri_rag/discovery.py`

Implements RAG Data Acquisition Stage A1 and A2.

A1 builds the systematic Discovery Query Bank V2 / Round 1. A2 builds the
Vietnamese natural farmer/public-question layer with explicit `query_origin`
provenance.

Input:

```text
config/crops.yaml
```

Outputs:

```text
data/agri_rag/discovery/query_bank.csv
data/agri_rag/discovery/query_bank.jsonl
data/agri_rag/discovery/a2_public_queries.csv
data/agri_rag/discovery/a2_public_queries.jsonl
data/agri_rag/discovery/discovery_queries_combined.jsonl
data/agri_rag/discovery/query_bank_summary.json
```

It generates discovery queries only. It does not crawl websites, search
scholarly APIs, download documents, validate source quality, build embeddings,
build BM25, create vector databases, implement retrieval, or run Weather ML.

`src/agri_rag/candidate_discovery.py`

Implements RAG Data Acquisition Stage A3 / Candidate Document Discovery V1.

Input:

```text
data/agri_rag/discovery/discovery_queries_combined.jsonl
```

Outputs from live runs:

```text
data/agri_rag/candidates/candidate_documents.jsonl
data/agri_rag/candidates/candidate_discovery_summary.json
```

It loads the combined A1+A2 query bank, selects a deterministic representative
subset, optionally executes a conservative live search, normalizes and
deduplicates URLs, derives basic source-domain metadata, preserves query
provenance, and audits the resulting candidate registry. It does not approve
sources, perform A4 source vetting, download the full documents, chunk text,
embed content, build indexes, or run retrieval.

`src/weather/__init__.py`

Marks `src.weather` as a Python package. The Weather pipeline will be rebuilt in
a later phase. It has no runtime input or output today.

`data/weather/geography/`

Static geography for the former Binh Dinh study area. This directory is required
for the future Weather branch and must be kept.

## 9. Important Paths

Input:

```text
config/crops.yaml
```

Generated A1/A2 RAG output:

```text
data/agri_rag/discovery/
```

Generated A3 live-search output:

```text
data/agri_rag/candidates/
```

A1/A2 generated file names:

```text
query_bank.csv
query_bank.jsonl
a2_public_queries.csv
a2_public_queries.jsonl
discovery_queries_combined.jsonl
query_bank_summary.json
```

A3 live generated file names:

```text
candidate_documents.jsonl
candidate_discovery_summary.json
```

Static Weather geography:

```text
data/weather/geography/
```

Never commit:

```text
GRIB/GRIB2
NetCDF
downloaded web/PDF RAG documents
generated indexes
caches
temporary reports
```

## 10. How To Run Stage A1/A2

Install dependencies:

```powershell
pip install -r requirements.txt
```

Generate A1, A2, the combined query file, and the summary:

```powershell
python -m src.agri_rag.discovery
```

Expected successful audit:

```text
Status                  : READY_FOR_A3
Issues                  : 0
```

Current successful counts:

```text
A1 queries              : 3486
A2 queries              : 246
Combined unique queries : 3732
```

Current A2 provenance:

```text
observed    : 0
transformed : 0
synthetic   : 246
```

The command prints A1 counts, A2 breakdowns, region/no-region counts, review
changes, audit status, audit issues, and 24 representative A2 queries.

## 11. How To Run Stage A3

Audit the A3 query selector without external search:

```powershell
python -m src.agri_rag.candidate_discovery --dry-run
```

Default dry-run status:

```text
Audit status : DRY_RUN_READY
Audit issues : 0
```

Run a small controlled scholarly-only live discovery:

```powershell
python -m src.agri_rag.candidate_discovery --live --channels scholarly --limit 3
```

Run a small controlled web live discovery without a Brave API key:

```powershell
python -m src.agri_rag.candidate_discovery --live --channels web --limit 3
```

Optionally use Brave instead of the DDGS fallback:

```powershell
$env:BRAVE_SEARCH_API_KEY = "<your-key>"
python -m src.agri_rag.candidate_discovery --live --channels web --limit 3
```

The default live limit is conservative and must not be used to execute all
3,732 queries.

A valid live A3 run reports:

```text
status = READY_FOR_A4
```

This requires a clean A3 structural audit, at least one relevant candidate in
the live run, and a query hit rate of at least 0.60. If live discovery has too
few relevant candidates per executed query, the status is:

```text
A3_LOW_COVERAGE
```

The A3 summary includes:

```text
raw_provider_results
relevant_results_kept
irrelevant_filtered
executed_queries
executed_original_queries
executed_search_requests
queries_with_relevant_results
queries_without_relevant_results
query_hit_rate
original_queries_succeeded
queries_recovered_by_fallback
provider_errors
queries_with_provider_error
queries_with_zero_results
```

`READY_FOR_A4` does not mean the candidates are trusted or approved RAG sources.

## 12. Current Status

```text
Repository cleanup                    DONE
Old source-first RAG pipeline         REMOVED
Old crawlers/legal pipelines          NOT RESTORED
Weather experimental scripts          REMOVED
Weather branch                        KEPT
Weather geography                     KEPT

CURRENT:
Stage A3
Candidate Document Discovery V1

READY FOR:
Review A3 query selection
Small controlled live discovery run

FUTURE:
Stage A4
Source vetting
```

## 13. Next Stages

```text
A4. Source vetting
A5. Relevance validation
A6. Source/local applicability validation
A7. Download
A8. Extract/normalize
A9. Weather-agronomy metadata
A10. Coverage audit
A11. Regional gap fill
A12. Freeze Dataset V1
```

Only after Dataset V1 is frozen should the project move to chunking, BM25, dense
embeddings, hybrid retrieval, reranking, and retrieval evaluation.

## 14. Development Rules

1. Do not remove or de-prioritize the Weather branch.
2. Do not restore old crawlers, old legal pipelines, old numbered audit scripts,
   old experimental weather scripts, or old generated RAG data.
3. Keep the repository small and understandable.
4. Prefer one clear module per major responsibility.
5. Do not create unnecessary small Python files.
6. Do not hardcode absolute local paths.
7. Do not use a hard domain whitelist during discovery.
8. Do not invent agronomic thresholds, pesticide legality, chemical dosage, or
   scientific parameters.
9. Every significant code, config, or file-structure change must update this
   README.
