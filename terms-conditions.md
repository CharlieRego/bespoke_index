# Terms & Conditions — Data Sources and Information Providers

Living register of attribution, license, and usage obligations for every external data source or information provider used in this project.

Agents and contributors **must** update this file when adding, changing, or removing a data source. See `CLAUDE.md` for the project-wide pointer.

## How to maintain this file

1. **One section per provider.** Use the provider’s legal / brand name as the heading.
2. **Capture before coding against the source.** Record attribution, allowed uses, and hard prohibitions *before* wiring an API key or shipping charts that cite the data.
3. **Prefer primary documents.** Link the official Terms of Use, Data Platform / API terms, brand kit, and privacy policy. Summarize obligations here; do not treat this file as a substitute for the legal text.
4. **Record the snapshot.** Note document versions and “last reviewed” dates. Re-check when renewing keys, upgrading tiers, or before public launch of a feature that redistributes or cites the data.
5. **Separate internal vs public use.** State what is fine for internal analysis versus what is required for public charts, posts, reports, or derived products.
6. **Call out project implications.** Under each provider, note concrete rules for this repo (e.g. chart footers, no bulk dumps, no competing benchmark product).
7. **Remove or mark obsolete** when a source is dropped; leave a one-line “removed” note with date if historical citations remain in the product.

### Section template (copy for new providers)

```markdown
## Provider Name

- **Last reviewed:** YYYY-MM-DD
- **Tier / product used:** Free API | Pro | Commercial | website scrape | etc.
- **Primary docs:**
  - Terms of Use: <url>
  - Data / API terms: <url>
  - Brand / attribution kit: <url>
  - Privacy: <url>

### Attribution

- …

### Allowed uses

- …

### Prohibited / restricted

- …

### Project implications (bespoke_index)

- …
```

---

## Artificial Analysis

- **Last reviewed:** 2026-09-29
- **Tier / product used:** Free API (model benchmarks); subject to upgrade if Pro/Commercial features are needed
- **Primary docs:**
  - API docs (attribution note): https://artificialanalysis.ai/documentation
  - Website Terms of Use: https://artificialanalysis.ai/docs/legal/Terms-of-Use.pdf
  - Data Platform Terms (v1.1, revised 2026-08-19): https://artificialanalysiscdn.com/legal/ProDataPlatformTerms.pdf
  - Brand kit: https://artificialanalysis.ai/brand-kit (assets: https://artificialanalysiscdn.com/brand-kit/aa_brand_kit.zip)
  - Privacy Policy: https://artificialanalysis.ai/privacy-policy

### Attribution (mandatory for free API and all external sharing)

Attribution is required whenever Data or Derived Data is shared, published, displayed, or otherwise made available **outside** internal systems. Data Platform Terms §5: **no exceptions**.

| Content type | Required attribution |
| --- | --- |
| Charts & visualizations | Artificial Analysis **logo visible on the chart** |
| Data & metrics | `Source: Artificial Analysis (artificialanalysis.ai)` with hyperlink where feasible |
| Derived data | `Based on data from Artificial Analysis` **plus** a non-endorsement statement |

Brand-kit practice that applies to this project:

- Put credit **inside** the chart image (screenshots drop footnotes).
- Link to the **specific** leaderboard, model, or methodology page when possible, not only the homepage.
- Spell **“Artificial Analysis”** in full on first mention; “AA” afterward is fine.
- Carry **index version** and **access/snapshot date** with scores and ranks.
- Use published metric names; keep `-AA` suffixes on adapted benchmarks (e.g. `GDPval-AA`).
- Do **not** imply endorsement: avoid “verified by,” “certified by,” “in partnership with,” or using the logo as an approval badge.
- Do not crop/rescale/filter charts in a way that changes the finding.

### Allowed uses (Free / Pro summary)

- **Internal:** analysis, research, and decision-making.
- **Public citation (Free and Pro):** limited citation in articles, posts, blogs, academic papers with correct attribution, and **without** reproducing data in a structured, tabular, or machine-readable redistributable form.
- **Pro / Commercial (when subscribed):** incorporate selected data into external reports, presentations, and client materials with attribution; create and externally distribute Derived Data with attribution and non-endorsement.

### Terms of Use (website)

Website Terms of Use govern access to `artificialanalysis.ai` (accounts, acceptable use, IP/trademarks, disclaimers, liability limits, California law / arbitration language). They are general site rules; the **Data Platform Terms** are the operative license for API and subscription data.

### Data Platform Terms — restrictions that matter here

- No **bulk redistribution** of the underlying dataset (citing figures ≠ republishing the feed).
- No use of data to build a **Competitive Product** (another AI benchmarking / evaluation product or service).
- No sharing of API keys or credentials; keep keys server-side; cache responses; respect rate limits (free API documented at 1,000 requests/day for the data API).
- Do not alter scores/metrics while presenting them as Artificial Analysis data.
- Do not selectively present data in a materially misleading way while attributing it to Artificial Analysis.
- No unauthorized reverse engineering, circumvention of access controls, or unauthorized use of data to train AI/ML systems.
- CritPt grader (if used): novel academic research or testing models intended for future public release only; no reverse-engineering of solution sets; access is non-transferable and may be revoked.
- Artificial Analysis retains ownership of the Data; license is use rights only.
- Company may monitor usage, request use information (15 business days to respond), require upgrade, suspend, terminate, or audit for out-of-scope use.
- Breaches of redistribution, anti-competitive, data-integrity, CritPt, general restriction, or attribution rules (where material harm results) can sit outside the general liability cap; customer indemnifies for breaches of those sections.

### Project implications (bespoke_index)

- Any public chart, leaderboard tile, or report cell sourced from Artificial Analysis must carry in-chart logo or `Source: Artificial Analysis (artificialanalysis.ai)` (hyperlinked) per the table above.
- Derived indices or scores built from AA inputs must say they are **based on** Artificial Analysis data and include a clear non-endorsement line (created by this project; not AA’s views or endorsement).
- Do not expose raw AA API payloads, bulk dumps, or machine-readable mirrors of their dataset.
- Do not market this product as “verified/certified by Artificial Analysis” or use their mark as a partner badge.
- Prefer stable `id` fields from the API over changing `name` / `slug` values.
- `aa_mirror/` (AA Study Mirror) is an **internal-only** study copy: it stores raw payloads and per-snapshot tables locally, so it must stay behind localhost/SSH tunnel or auth, with no public deployment, export/download features, or JSON data endpoints. Fetched data is gitignored; test fixtures are synthetic. It does not use AA logos as its own identity.
- Re-review this section if the project moves from Free to Pro/Commercial or starts shipping AA-derived data in downloadable/tabular form.
