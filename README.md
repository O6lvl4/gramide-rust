# gramide-rust

Rust for [gramide-cli](https://github.com/O6lvl4/gramide-cli): the lexer spec, the
grammar as a value, that grammar compiled, and the rules that say which of its
nodes declare a name — one Almide package, `gramide_rust`, depending on
[gramide](https://github.com/O6lvl4/gramide) and on nothing else.
The `gramide` command ([gramide-cli](https://github.com/O6lvl4/gramide-cli)) ships it; this repository is where it is tested, measured and
released on its own.

[日本語](README_ja.md)

```
almide build cli/main.almd -o gramide_rust     # gramide over .rs alone
./gramide_rust check src/*.rs
./gramide_rust outline src/lib.rs              # `L4-4 method S::fmt` under `L3-5 impl fmt::Display for S`
./gramide_rust gen-table > src/table.almd      # after any change to the grammar
```

## What it covers

Every `.rs` file under `crates`, `tests`, `runtime`, `src` and `tools` of the
[Almide](https://github.com/almide/almide) compiler — 827 files, 15.7 MB:

| files | result |
|---|---|
| 826 files | all parse; `rustfmt --edition 2024` accepts exactly these 826 |
| 1 file `rustfmt` rejects | parses — it uses `gen` as a name in an edition that reserves it, a name-resolution question, not a syntax one |

The guarantee runs one way: a file this package rejects is broken for
`rustfmt` too. Every `.rs` file in the compiler repository today — 1,022
files, 17.3 MB — checks in **0.080 s** in one process, 215 MB/s, with the
same four files rejected before and after the expression ladder below was
folded and the engine's lexer packed
([evidence](docs/evidence/corpus-check-rust-lexer.json)); when this grammar
was written the same corpus took 2.4 s on one core, and the engine work
recorded in [gramide](https://github.com/O6lvl4/gramide/blob/main/docs/design.md)
is the difference.

One keystroke re-reads one item: the engine keeps a parsed file as its
recover items (here, every item of a module and every statement inside a
block) and re-reads the smallest one an edit touched
([how](https://github.com/O6lvl4/gramide/blob/main/docs/incremental.md)).
On `crates/almide-frontend/src/lower/expressions.rs` (92 KB), 1,000 letters
typed or deleted six letters into long words cost 65 µs at the median and
415 µs at the 90th percentile, against 1.7 ms for a whole parse, every
fiftieth checked against one. Over the compiler's 1,015 tracked `.rs` files,
ten random edits each (10,000 edits, every one checked token for token and
node for node against a whole parse of the same text) gave no difference;
18 edits were read as a whole file
([evidence](docs/evidence/incremental-corpus-almide-compiler-rs.json)).
`ci/incremental_check.py` runs this; `reparse --edit START:OLD_END:NEW_END --new FILE`
is the one-edit command.
The same 1,000 edits through tree-sitter-rust at `77a3747` (`ts_tree_edit` +
reparse, the C harness of
[gramide-javascript](https://github.com/O6lvl4/gramide-javascript/blob/main/bench/tree_sitter_ranges.c)
built with `-DLANG=tree_sitter_rust`) take 52 µs at the median and 72 µs at
the 90th percentile against gramide's 59 and 383
([evidence](docs/evidence/incremental-rust-frontend-expressions.json),
`bench/incremental.py`): here tree-sitter is ahead, because a statement
holding a large `match` is one item to gramide and is read again whole,
where tree-sitter reuses the arms the edit did not touch.

Structured ranges keep an item's envelope: `#[inline] pub fn read` starts at
the attribute, and a method is named with the type it is implemented on —
`S::fmt` under `impl fmt::Display for S`, whose trait and type are kept apart
the way `rustc_ast::ast::Impl` keeps `of_trait` and `self_ty`, and qualified
by its module path in flat output: `outer::inner::S::fmt`, while the outline
shows the same nesting by indentation. A function written inside a method
body is a function, not a method. Each of these is a test in
`src/symbols.almd` and a fixture in `ci/symbols.py`.

## How it is written

- **`src/lexer.almd`** — 34 lines of `Spec` and two lexer families of Rust's
  own in the shared lexer: numbers with a type suffix (`1u8`, `2.0f32`, and
  `1.` a float where `1.max` is not), and strings where `r##"…"##` closes
  only on the hashes it opened with, `b"…"` is bytes, and `'a` is a lifetime
  rather than an unterminated character — told apart by what closes them.
  `NL_NONE`: newlines mean nothing, statements end at `;` or a block. `>>` is
  deliberately absent from the operators, because it would close only one of
  the two brackets in `Vec<Vec<T>>`; the grammar spells a shift as two `>`.
- **`src/grammar.almd`** — items, types, patterns, expressions as a
  precedence ladder, closures, let chains, qualified paths. The one
  context-dependent place is the struct literal, exactly as in Go: `if x == T { }`
  must not read `T { }` as a value, so the expression rules are generated
  twice from one function and the headers of `if`, `while`, `for` and `match`
  use the second. The nine binary levels are three `prec` ladders around the
  one level a ladder cannot hold — a shift's `>>` is two `>` tokens, so that
  `Vec<Vec<T>>` closes — with `cmp` a rule of its own because a `let` chain's
  scrutinee stops there. A macro body or an attribute's contents is a balanced
  run of tokens with no reading. A `decl_head` rule keeps a half-typed item's
  name.
- **`src/symbols.almd`** — functions, methods, trait method signatures,
  types, lets, variants, fields, impls, mods and macros declare names; an
  `impl` or a type owns its methods; a `mod` qualifies what is inside it;
  `item_envelope` lends its start to the declaration it wraps.
- **`src/table.almd`** — generated by `gen-table`; CI fails if it is stale.

## Checks

`bash ci/check.sh`: `almide test` (56 tests — lifetimes and characters, raw
strings, suffixed numbers, every item kind, `>>`, `union`, closures, macro
bodies, recovery, what the readers say), the table check, the binary's smoke
test, and the structured-range fixtures ([ci/README.md](ci/README.md)).

## License

MIT or Apache-2.0, at your option.
