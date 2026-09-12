# CORDIS → SDG Web Prototype (Registration §6 Item 7)

A zero-backend static web application for exploring the SDG mapping of Horizon Europe (2021–2027) projects from CORDIS.

## 1. Specification & Scope

Built strictly under **Registration v10** (`c5f2a26ce6049e801a7e757efc2cbe4253689987fad761f1d97cfb5b0ad68fb2`, ratified at cordis-sdg seq 261):
- Scope: §6 item 7 only — search a project, see its assignments and their evidence, browse the SDG distribution.
- Static data, no API key, deployable on any static web hosting.
- Reads four inputs and never alters them:
  1. Published mapping table `data/corpus/mapping-table-0246412.csv` (`181d378a3078014193f3ae4f684b00b375ed62f3d24b2b34c060f6457b4a00d3`)
  2. Figures document `data/corpus/figures.json` (`03d79580081ca40bf0d1d25b5279a57880ddf09d750490553593387126d92f6f`)
  3. Metrics artefact `data/pipeline/evaluation-100-metrics.json` (`babd37415581ce82ecb09c4501052ce811e834e57dad7c6735389ce321dd8a2e`)
  4. Six committed notebook SVGs under `figures/`:
     - `recall-ceiling.svg` (`2877c3ac441ffbb0485b712abda4cff057c8efa93e904c7ca494fcd6f8427ed1`)
     - `disagreement-shape.svg` (`d9c6a91a11481c3265be6d4747b69352790fa7e4536ff98ff19ea831ea3f9e61`)
     - `goals-by-project-count.svg` (`7db6eae48b966e1fa73c3e928f21958171cad4a8536f49f3fe1e816701f02d23`)
     - `most-linked-targets.svg` (`8f2caf29f882ebf6148ffd73485308fb02a7e682e0bfaace837de532c1d644d6`)
     - `relevance-by-field.svg` (`46baad33a8d40a4cba2b0ee220df564d01b4bc61308ff102374da95ace6f4d6f`)
     - `confidence-bands.svg` (`7d55aa97458541589e569986b3be7a8abb14e7a5da12ccef06030469fe160761`)

## 2. Binding Render Rules (Room seq 266 & 267)

1. **Hyphen titles preserved**: Two CORDIS titles begin with a hyphen (`101073045` and `101275778`). They are rendered as plain unescaped CORDIS bytes.
2. **Parked explanation marker**: Section 3.7 explanation pass is parked in this environment. The marker text is displayed explicitly as a parked notice badge, never as model-generated explanation prose.
3. **Field presence vs absence**: `sources_present` and `sources_absent` are surfaced prominently so readers can clearly distinguish a field that matched nothing from a field that was absent.
4. **No chart redrawing**: The prototype embeds the committed notebook SVGs directly.

## 3. Data Pipeline & Architecture

`prototype/build_data.py` reads the four inputs, verifies their hashes, and transforms the 28,833 mapping rows into client-side JSON assets:
- `prototype/data/corpus_summary.json`: Aggregated metrics, SDG goals distribution, and dimension breakdowns.
- `prototype/data/projects_index.json`: 23,451 project index entries for instantaneous in-browser search and filtering.
- `prototype/data/projects/<prefix>.json`: 42 sharded project detail bundles for fast on-demand inspection without high memory usage.

## 4. How to Run & Verify

1. Run the data builder:
   ```bash
   python prototype/build_data.py
   ```
2. Open `prototype/index.html` directly in a modern browser, or serve via any static HTTP server:
   ```bash
   python -m http.server 8000
   ```
   Then navigate to `http://localhost:8000/prototype/` (or `http://localhost:8000/` if served directly from the `prototype` directory).

## 5. Regeneration & Integrity Guarantees (Attila seq 285 & Counsel seq 280)

1. **Deliberate Repository Exception**: Under Attila's ruling at `cordis-sdg` seq 285, §6 item 2 (mapping table) is a named deliverable and §6 item 7 (`prototype/data/`) is its static derivative, and a clone must carry both so a reader or judge can inspect the prototype immediately without running multi-step data pipelines or accessing external vaults.
2. **Hash Guard**: `build_data.py` validates the SHA-256 hashes of all four confirmed inputs before reading or writing any data. If any hash diverges, execution halts immediately with an assertion failure.
3. **Deterministic & Minimal Churn**: Prototype data files under `prototype/data/` are regenerated **only** when the published mapping table or figures hash moves on the chain, never for cosmetic or UI changes.
4. **Standalone Integrity**: For independent, zero-dependency deployment without access to the outer repository structure, `prototype/figures/` maintains verified byte-identical copies of the six committed figures.
