"""Structured ranges and names for Rust items; no model calls."""
from pathlib import Path
import json, subprocess, tempfile
BIN = Path(__file__).resolve().parents[1] / 'gramide_rust'
def symbols(path):
    p = subprocess.run([str(BIN), 'symbols', str(path)], capture_output=True, text=True, check=True)
    d = json.loads(p.stdout); assert d['schema_version'] == 1 and d['complete'] is True
    return d['symbols']
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    rust = root / 'ranges.rs'
    rust.write_text("// 日本語\nimpl Box {\n #[inline]\n pub fn\n read<'a>(&'a self) -> &'a str {\n r##\"}\nfn phantom() {}\n\"##\n }\n}\n")
    syms = symbols(rust); method = next(s for s in syms if s['name'] == 'Box::read')
    assert (method['owner'], method['start'], method['end']) == ('Box', 3, 9), method
    assert rust.read_bytes()[method['start_byte']:method['end_byte']].startswith(b'#[inline]')
    assert not any('phantom' in s['name'] for s in syms)
    rust.write_text('#[repr(C)]\npub struct\nBox { x: i32 }\n')
    box = next(s for s in symbols(rust) if s['name'] == 'Box')
    assert (box['start'], box['end'], box['start_byte']) == (1, 3, 0), box
    rust.write_text('mod outer {\n mod inner {\n  impl fmt::Display for S {\n   fn fmt(&self) {}\n  }\n  fn free() {}\n }\n}\nmod other { fn free() {} }\n')
    syms = symbols(rust)
    method = next(s for s in syms if s['name'] == 'outer::inner::S::fmt')
    assert method['owner'] == 'S' and method['start'] == 4 and method['end'] == 4, method
    tags = subprocess.check_output([str(BIN), 'tags', str(rust)], text=True)
    assert 'def impl fmt::Display for outer::inner::S L3-5' in tags, tags
    assert 'def function outer::inner::free L6-6' in tags and 'def function other::free L9-9' in tags, tags
    outline = subprocess.check_output([str(BIN), 'outline', str(rust)], text=True)
    assert 'L3-5 impl fmt::Display for S' in outline and 'L4-4 method S::fmt' in outline, outline
    assert 'L6-6 function free' in outline and 'outer::inner::free' not in outline, outline
    broken = root / 'broken.rs'; broken.write_text('fn real() {}\nfn broken(\n')
    p = subprocess.run([str(BIN), 'symbols', str(broken)], capture_output=True, text=True)
    assert p.returncode != 0 and not p.stdout, (p.returncode, p.stdout, p.stderr)
print('Structured ranges passed: attributes and visibility in envelopes, raw strings, module paths, trait impls, invalid input')
