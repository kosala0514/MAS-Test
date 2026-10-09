"""
Rename namespace PREFIXES consistently across the whole kit, e.g.  ffo: -> ffonto:   and   ffv: -> ffontov:

    python scripts/rename_prefix.py                      # dry run: shows what would change
    python scripts/rename_prefix.py --apply              # writes the changes
    python scripts/rename_prefix.py --apply --map ffo=ffonto           # only rename ffo
    python scripts/rename_prefix.py --apply --map ffo=ffonto ffv=ffontov

Only the prefix NAME changes. The namespace IRIs (http://purl.org/ffonto#, http://purl.org/ffonto/vocab#) stay
exactly the same, so the meaning of every term is unchanged. The script renames the prefix in all forms:
    ffo:Class              (Turtle, SPARQL, JSON-LD values, Python strings, prompts, docs)
    @prefix ffo: / PREFIX ffo:
    "ffo": "http://…"      (JSON-LD context keys, Python prefix dictionaries)
    vann:preferredNamespacePrefix "ffo"
It also repairs damage from an earlier plain-text replace of "ffo" -> "ffonto":
    ffontonto -> ffonto,  ffontontov -> ffontov   (e.g. http://purl.org/ffontonto# -> http://purl.org/ffonto#)
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTS = {".ttl", ".rq", ".py", ".jsonld", ".json", ".md", ".xml", ".html", ".txt", ".sh", ".csv"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "site", "build", "node_modules", "results", "index", "_build"}
REPAIRS = [("ffontontov", "ffontov"), ("ffontonto", "ffonto")]


def files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTS and not (set(p.relative_to(ROOT).parts[:-1]) & SKIP_DIRS):
            if p.resolve() != Path(__file__).resolve():
                yield p


def rename(text, mapping):
    for bad, good in REPAIRS:
        text = text.replace(bad, good)
    for old, new in mapping.items():
        # the prefix as a token: not part of a longer word, IRI path or file name,
        # followed by ":" (prefixed name / declaration) or a quote (JSON / Python key, vann prefix literal)
        text = re.sub(rf"(?<![\w-]){re.escape(old)}(?=:|\"|')", new, text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", nargs="+", default=["ffo=ffonto"], help="old=new pairs (default: ffo=ffonto)")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    a = ap.parse_args()
    mapping = dict(m.split("=", 1) for m in a.map)
    total = 0
    for p in sorted(files()):
        old = p.read_text(encoding="utf-8", errors="ignore")
        new = rename(old, mapping)
        if new != old:
            n = sum(1 for x, y in zip(old.splitlines(), new.splitlines()) if x != y)
            total += 1
            print(f"{'changed' if a.apply else 'would change'}: {p.relative_to(ROOT)}  ({n} lines)")
            if a.apply:
                p.write_text(new, encoding="utf-8")
    print(f"\n{total} files {'changed' if a.apply else 'to change'}; mapping {mapping}")
    if not a.apply:
        print("dry run only - add --apply to write")
    else:
        print("next: delete old generated data and rebuild (see the steps printed below)\n"
              "  rm -rf tests/_build data/jsonld data/graphs data/kg*.ttl\n"
              "  python scripts/make_prompt.py && python scripts/lift.py && python scripts/run_cqs.py\n"
              "  pytest -q tests/ && bash validation/validate_ontology.sh\n"
              "  python graphdb/load_graphdb.py        # reload GraphDB: it still holds data lifted with the old prefixes")


if __name__ == "__main__":
    main()
