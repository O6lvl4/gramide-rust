# Reproducible checks

Run `bash ci/check.sh` from a checkout with Almide installed, or set
`ALMIDE_BIN` to an absolute compiler path. This runs the package's tests,
builds its own binary from `cli/main.almd`, fails if `src/table.almd` is not
what the grammar compiles to, and drives the binary through temporary
fixtures: `check` and `outline` on valid and broken files, and the
structured-range cases — attributes and visibility inside an item envelope, a
raw string holding a fake declaration, a method under a trait impl inside
nested modules with its owner and module path, and invalid input refused
without JSON. No model API or credentials are used.

CI pins Almide to `dff9a458f2e581631bb6537c856a7974036e4153` and Rust to
`1.94.0`. Upgrade these deliberately and rerun the checks together. The
corpus result in the README is reproduced with gramide's
`bench/corpus_check.py --binary ./gramide_rust --root <almide checkout> --ext .rs`
and `rustfmt --edition 2024 --check` over the same files.
