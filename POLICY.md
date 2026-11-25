# Data collection policy

This project publishes **metadata only**: headlines, canonical links, publication
dates, publisher-provided summaries (truncated and stripped of HTML), repository
descriptions, paper abstracts and the project's own topic labels.

It does **not** publish article bodies, images, video, paywalled text, or any
re-hosted copy of third-party content. Every record links to the original source.

## Sources

- Only publicly reachable feeds and public APIs are used: publisher RSS/Atom
  feeds, the arXiv API, and the GitHub Search API.
- A source is added only after checking that its feed or API is public, that the
  response is the documented machine-readable format, and that the operator's
  terms allow metadata aggregation with attribution.
- Feeds that require authentication, return 403, or cannot be parsed are not
  used. Sources that start failing are disabled after repeated failures and
  listed in the daily digest.
- Requests are rate limited per host, use a descriptive User-Agent, and are
  bounded in time and size.

## Correction and removal

If you operate one of the aggregated sources and want a source removed, or you
find an incorrect record, open an issue in this repository. Removals are applied
to future runs and existing records for that source are deleted.

## No warranty

Aggregated labels are automated and may be wrong. Nothing here is legal,
financial, or editorial advice, and inclusion in this dataset is not an
endorsement of any item.
