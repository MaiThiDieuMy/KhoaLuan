# AGENTS.md

Persistent instructions for coding agents working in this repository.

## Project Rules

1. This repository contains two core branches of work:
   - Weather Model
   - Agricultural RAG

2. Do not remove or de-prioritize the Weather branch. The final system combines:

   ```text
   Weather + RAG + Farm Context -> Agro-Weather / Decision Engine
   ```

3. The repository was recently cleaned intentionally. Do not restore old crawlers, old legal pipelines, old numbered audit scripts, old experimental weather scripts, or old generated RAG data.

4. Keep the repository small and understandable. Do not create many tiny Python scripts. Prefer one clear module per major responsibility.

5. Every significant code, config, or file-structure change must also update `README.md`.

6. `README.md` must always document:
   - current system flow
   - repository tree
   - responsibility of every source-code file
   - important input/output paths
   - how to run the current stage
   - current project status
   - next stage

7. Never commit:
   - GRIB/GRIB2
   - NetCDF
   - downloaded web/PDF RAG documents
   - generated indexes
   - caches
   - temporary reports

8. Keep `data/weather/geography/` because it is required for the future Weather pipeline.

9. RAG acquisition follows:

   ```text
   discovery first -> relevance validation -> source validation
   ```

   There must not be a hard domain whitelist during discovery.

10. Agricultural scope:
    - `cai_xanh` / Brassica juncea
    - `ngo` / Coriandrum sativum
    - `cai_cuc` / Glebionis coronaria
    - `rau_muong` / Ipomoea aquatica
    - `xa_lach` / Lactuca sativa

11. Primary geographic applicability is Vietnam first. Former Binh Dinh / current Gia Lai is the study area. International sources may be used later for gap filling.

12. Do not invent agronomic thresholds, pesticide legality, chemical dosage, or scientific parameters.
