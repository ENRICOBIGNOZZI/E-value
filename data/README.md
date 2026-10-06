# Official JKP inputs

Raw archives are intentionally untracked. `python experiments/fetch_jkp.py` obtains the official USA monthly capped-value factor, market (`mkt`), and theme archives. Exact original source hashes and retrieval time are in `source_manifest_20261006.json`.

Returns are decimals, already signed as supplied. Do not reapply the `direction` field. Data are JKP CC BY-NC 4.0 research data, with citation in the project README. A contemporary download can differ because the provider revises historical data. The loader refuses mismatched local hashes, duplicate factor-months, and missing post-launch returns.
