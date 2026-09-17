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
recover items (here, every item of the file or of a module, trait, impl or
extern block, every statement inside a block, and every arm of a `match`)
and re-reads the smallest one an edit touched
([how](https://github.com/O6lvl4/gramide/blob/main/docs/incremental.md)).
The same 1,000 edits on `crates/almide-frontend/src/lower/expressions.rs`
(92 KB), each a letter typed or deleted six letters into a word of thirteen
or more, in-process, for gramide's `reparse-bench` and for tree-sitter-rust
at `77a3747` through `ts_tree_edit` + reparse in the C harness of
[gramide-javascript](https://github.com/O6lvl4/gramide-javascript/blob/main/bench/tree_sitter_ranges.c)
built with `-DLANG=tree_sitter_rust`; every fiftieth result checked against
a whole parse ([evidence](docs/evidence/incremental-rust-frontend-expressions.json),
`bench/incremental.py`):

| `lower/expressions.rs` | gramide | tree-sitter |
|---|---:|---:|
| median | 5.3 µs | 53 µs |
| 90th percentile | 7.5 µs | 74 µs |
| a whole parse, for scale | 1.7 ms | |

Nine times ahead at the median. The tail was 383 µs before match arms and
impl members were items of their own, 219 µs before an edit in a doc
comment, which touches no token, stopped reading the item before it, and
137 µs before a letter typed into a name, which retypes one token,
stopped reading the item holding it; the median was 53 µs until the
engine stopped cloning its grammar table on the way to the edit.
Over the compiler's 1,015 tracked `.rs` files, ten random edits each
(10,000 edits, every one checked token for token and node for node against
a whole parse of the same text) gave no difference; no edit was
read as a whole file
([evidence](docs/evidence/incremental-corpus-almide-compiler-rs.json)).
`ci/incremental_check.py` runs this; `reparse --edit START:OLD_END:NEW_END --new FILE`
is the one-edit command.

Structured ranges keep an item's envelope: `#[inline] pub fn read` starts at
the attribute, and a method is named with the type it is implemented on —
`S::fmt` under `impl fmt::Display for S`, whose trait and type are kept apart
the way `rustc_ast::ast::Impl` keeps `of_trait` and `self_ty`, and qualified
by its module path in flat output: `outer::inner::S::fmt`, while the outline
shows the same nesting by indentation. A function written inside a method
body is a function, not a method. Each of these is a test in
`src/symbols.almd` and a fixture in `ci/symbols.py`.

### A broken file

An editor's file is broken more often than not. `bench/recovery.py` breaks every
file of the corpus in four ways, one at a time — a `{` typed at the start of a
word, a `}` deleted, a `)` deleted, a `(` typed — and compares what each tool
still lists (gramide's `outline`, which reads the recovered parse; tree-sitter's
tree through the same harness, `--recover`) with its own listing of the whole
file, by kind, name and start line. A declaration whose lines hold the break is
expected to go; a break is *clean* when nothing else is lost and nothing new
appears ([evidence](docs/evidence/recovery-almide-compiler-rs.json), [how it recovers](https://github.com/O6lvl4/gramide/blob/main/docs/recovery.md)):

| Almide compiler `crates/`: 663 files, 2,632 breaks | gramide | tree-sitter |
|---|---:|---:|
| declarations kept, all breaks | 99.9% | 97.5% |
| clean breaks (nothing lost beyond the break, nothing invented) | 99.8% | 94.9% |
| clean breaks, `insert {` | 99.8% | 97.1% |
| clean breaks, `delete }` | 99.4% | 94.5% |
| clean breaks, `delete )` | 100.0% | 92.7% |
| clean breaks, `insert (` | 100.0% | 95.2% |

gramide is ahead on every kind of break. A `}` deleted resumes at the next
`fn` or item, where tree-sitter nests what follows into the open body; a `)`
deleted costs gramide nothing beyond the item that holds it.

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
