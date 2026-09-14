# gramide-rust

[gramide-cli](https://github.com/O6lvl4/gramide-cli) の Rust。字句解析の spec、値としての文法、その文法を
コンパイルした表、そしてどのノードが名前を宣言するかの規則。ひとつの Almide パッケージ
`gramide_rust` で、依存は [gramide](https://github.com/O6lvl4/gramide) だけです。
`gramide` コマンド（[gramide-cli](https://github.com/O6lvl4/gramide-cli)）はこれを出荷し、このリポジトリはこれ単体をテスト・計測・リリースする場所です。

[English](README.md)

```
almide build cli/main.almd -o gramide_rust     # .rs だけの gramide
./gramide_rust check src/*.rs
./gramide_rust outline src/lib.rs              # `L3-5 impl fmt::Display for S` の下に `L4-4 method S::fmt`
./gramide_rust gen-table > src/table.almd      # 文法を変えたら
```

## カバー範囲

[Almide](https://github.com/almide/almide) コンパイラの `crates`・`tests`・`runtime`・`src`・`tools`
配下の全 `.rs` ファイル — 827 ファイル、15.7 MB:

| ファイル | 結果 |
|---|---|
| 826 ファイル | すべてパース。`rustfmt --edition 2024` が受理するのもちょうどこの 826 |
| `rustfmt` が拒否する 1 ファイル | パースは通る — 予約された edition で `gen` を名前に使っており、構文ではなく名前解決の問題 |

保証は一方向です。このパッケージが拒否するファイルは `rustfmt` にとっても壊れている。今日の
コンパイラリポジトリの全 `.rs` — 1,022 ファイル、17.3 MB — は 1 プロセス **0.104 秒**、166 MB/s で
検査でき、下記の式の梯子を畳む前後で拒否する 4 ファイルは同じです
（[証拠](docs/evidence/corpus-check-rust.json)）。この文法を書いた時点では同じコーパスが 1 コア
2.4 秒で、[gramide](https://github.com/O6lvl4/gramide/blob/main/docs/design.md) に記録された
エンジンの仕事がその差です。

構造化範囲は item のエンベロープを保ちます。`#[inline] pub fn read` は属性から始まり、
メソッドは実装先の型で名付けられます — `impl fmt::Display for S` の下の `S::fmt`。trait と型は
`rustc_ast::ast::Impl` が `of_trait` と `self_ty` を分けるのと同じように分けて保持し、平らな出力では
モジュールパスで修飾します: `outer::inner::S::fmt`。アウトラインは同じ入れ子をインデントで示します。
メソッド本体の中に書かれた関数はメソッドではなく関数です。これらはそれぞれ `src/symbols.almd` の
テストと `ci/symbols.py` のフィクスチャになっています。

## 書き方

- **`src/lexer.almd`** — 34 行の `Spec` と、共用字句解析器に Rust 自身が持ち込んだ 2 つの族。
  型接尾辞付きの数値（`1u8`、`2.0f32`、`1.` は浮動小数だが `1.max` は違う）と、開いたときの
  ハッシュでしか閉じない `r##"…"##`、bytes の `b"…"`、未終端の文字ではなくライフタイムである
  `'a` — 何で閉じるかで見分けます。`NL_NONE`: 改行は意味を持たず、文は `;` かブロックで終わる。
  `>>` は意図的に演算子から外してあります。`Vec<Vec<T>>` の 2 つの括弧の片方しか閉じられない
  からで、文法はシフトを `>` 2 つとして綴ります。
- **`src/grammar.almd`** — item、型、パターン、優先順位の梯子としての式、クロージャ、let チェーン、
  修飾パス。文脈に依存する唯一の箇所は構造体リテラルで、Go とまったく同じです。`if x == T { }` で
  `T { }` を値として読んではいけないので、式の規則を 1 つの関数から 2 通り生成し、`if`・`while`・
  `for`・`match` のヘッダは後者を使います。二項演算子の 9 段は、梯子に乗らない 1 段（シフトの `>>`
  は `Vec<Vec<T>>` を閉じるために `>` 2 トークン）を挟んだ 3 つの `prec` 梯子で、`cmp` は `let`
  チェーンの被検査式がそこで止まるので独立した規則のままです。マクロ本体と属性の中身は読まずに、
  括弧の釣り合ったトークンの並びとして扱います。`decl_head` 規則は書きかけの item の名前を残します。
- **`src/symbols.almd`** — 関数・メソッド・trait のメソッドシグネチャ・型・let・variant・field・
  impl・mod・macro が名前を宣言し、`impl` と型がメソッドを所有し、`mod` はその中を修飾し、
  `item_envelope` は包む宣言に開始位置を貸します。
- **`src/table.almd`** — `gen-table` の生成物。古ければ CI が落ちます。

## 検査

`bash ci/check.sh`: `almide test`（56 テスト — ライフタイムと文字、raw 文字列、接尾辞付き数値、
全 item 種、`>>`、`union`、クロージャ、マクロ本体、回復、読み手の出力）、表の一致検査、バイナリの
スモーク、構造化範囲のフィクスチャ（[ci/README.md](ci/README.md)）。

## ライセンス

MIT または Apache-2.0、お好みで。
