#!/usr/bin/env python3
"""porting-status — porteringsstatus per modul för DEN HÄR grenen.

Beskriver bara den utcheckade grenens utgåva. Skriver om avsnittet
``## Porteringsstatus`` i README.md och lämnar allt före orört.

Repo-agnostisk: läser repo-namnet ur ``git remote``. Samma fil kan committas
i varje repo som använder formatet.

Se skillen ``odoo-pfiles`` avsnitt 5c för formatet.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys

CORE = "/usr/share/core-odoo/addons"
ADDON_ROOTS = ["/usr/share"]
SECTION = "## Porteringsstatus"

# Klassning av blockerare (design D2)
KLASS_TOM_GREN = "tom gren"
KLASS_FINNS_INTE = "finns inte"
KLASS_SAKNAS_I_UTGAVAN = "saknas i utgåvan"


def sh(*args: str, cwd: str | None = None) -> str:
    """Kör ett kommando och returnera stdout. Kastar vid fel."""
    res = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}: {res.stderr.strip()}")
    return res.stdout


def git(*args: str) -> str:
    return sh("git", *args)


def repo_name() -> str:
    """Repo-namnet ur git remote — aldrig hårdkodat (design D10)."""
    try:
        url = git("remote", "get-url", "origin").strip()
    except RuntimeError:
        url = os.path.basename(git("rev-parse", "--show-toplevel").strip())
    name = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def current_branch() -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD").strip()


def edition_of(branch: str) -> str:
    """Grennamnet är utgåvan om det ser ut som en utgåva."""
    if re.fullmatch(r"\d{2}\.0", branch):
        return branch
    raise RuntimeError(
        f"grenen '{branch}' är ingen utgåva — porteringsstatus kräver en "
        f"utgåvegren (18.0/19.0/20.0)"
    )


# ---------------------------------------------------------------- datainsamling


def _resolve_ref(ref: str) -> str:
    """'20.0' ska slås upp som origin/20.0 om den lokala grenen saknas."""
    try:
        git("rev-parse", "--verify", "-q", ref)
        return ref
    except RuntimeError:
        alt = f"refs/remotes/origin/{ref}"
        git("rev-parse", "--verify", "-q", alt)
        return alt


def module_dirs(ref: str = "HEAD") -> list[str]:
    """Modulkataloger på ref: kataloger med __manifest__.py, utan punkt/scripts."""
    ref = _resolve_ref(ref)
    names = git("ls-tree", "-d", "--name-only", ref).split()
    out = []
    for name in names:
        if name.startswith(".") or name == "scripts":
            continue
        try:
            git("cat-file", "-e", f"{ref}:{name}/__manifest__.py")
        except RuntimeError:
            continue
        out.append(name)
    return sorted(out)


def read_manifest(module: str, ref: str = "HEAD") -> dict:
    """Läs manifestet med ast.literal_eval — inte import (p-filer är inte giltig Python)."""
    ref = _resolve_ref(ref)
    src = git("show", f"{ref}:{module}/__manifest__.py")
    try:
        return ast.literal_eval(src)
    except (ValueError, SyntaxError) as exc:
        raise RuntimeError(f"{module}/__manifest__.py går inte att parsa: {exc}")


def pfile_count(module: str, ref: str = "HEAD") -> int:
    ref = _resolve_ref(ref)
    files = git("ls-tree", "-r", "--name-only", ref, f"{module}/").splitlines()
    return sum(1 for f in files if re.search(r"\.p\.(py|xml|csv|js)$", f))


def edition_modules(edition: str) -> set[str]:
    """Alla moduler som finns för en utgåva: kärnan + alla repo-grenar."""
    have: set[str] = set()
    if os.path.isdir(CORE):
        have |= {n for n in os.listdir(CORE) if os.path.isdir(os.path.join(CORE, n))}
    for root in ADDON_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not (name.startswith("odoo-") or name.startswith("odooext-")):
                continue
            path = os.path.join(root, name)
            if not os.path.isdir(os.path.join(path, ".git")):
                continue
            ref = f"refs/remotes/origin/{edition}"
            try:
                git("-C", path, "rev-parse", "--verify", "-q", ref)
            except RuntimeError:
                continue
            try:
                have |= set(git("-C", path, "ls-tree", "-d", "--name-only", ref).split())
            except RuntimeError:
                continue
    return have


# -------------------------------------------------------------------- klassning


def find_module_repo(module: str, edition: str) -> str | None:
    """Vilket repo har modulen på den utgåvan? None = ingenstans."""
    if os.path.isdir(os.path.join(CORE, module)):
        return "kärnan"
    for root in ADDON_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not (name.startswith("odoo-") or name.startswith("odooext-")):
                continue
            path = os.path.join(root, name)
            if not os.path.isdir(os.path.join(path, ".git")):
                continue
            ref = f"refs/remotes/origin/{edition}"
            try:
                tree = git("-C", path, "ls-tree", "-d", "--name-only", ref).split()
            except RuntimeError:
                continue
            if module in tree:
                return name
    return None


def classify(module: str, edition: str) -> tuple[str, str]:
    """Returnera (klass, repo) enligt design D2.

    - **tom gren**: modulen finns i ett repo som HAR en gren för utgåvan, men
      katalogen står inte i trädet (grenen är tom eller porterad utan den).
    - **saknas i utgåvan**: modulen finns i en lägre utgåva, men inget repo
      som har den har en gren för den här utgåvan.
    - **finns inte**: modulen finns inte i någon utgåva alls.
    """
    if find_module_repo(module, edition):
        return ("", "")

    tomma: list[str] = []
    lagre: list[str] = []
    for root in ADDON_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not (name.startswith("odoo-") or name.startswith("odooext-")):
                continue
            path = os.path.join(root, name)
            if not os.path.isdir(os.path.join(path, ".git")):
                continue
            # Vilka utgåvor har detta repo modulen i?
            editions_with_module = [
                ed for ed in ("18.0", "19.0", "20.0")
                if module in _repo_tree(path, ed)
            ]
            if not editions_with_module:
                continue
            if edition in _repo_branches(path):
                tomma.append(name)
            else:
                lagre.append(name)

    if tomma:
        return (KLASS_TOM_GREN, tomma[0])
    if lagre:
        return (KLASS_SAKNAS_I_UTGAVAN, lagre[0])
    return (KLASS_FINNS_INTE, "")


def _repo_branches(path: str) -> set[str]:
    try:
        refs = git("-C", path, "for-each-ref", "--format=%(refname)").splitlines()
    except RuntimeError:
        return set()
    out = set()
    for ref in refs:
        m = re.fullmatch(r"refs/remotes/origin/(\d{2}\.0)", ref)
        if m:
            out.add(m.group(1))
    return out


def _repo_tree(path: str, edition: str) -> set[str]:
    try:
        return set(
            git("-C", path, "ls-tree", "-d", "--name-only",
                f"refs/remotes/origin/{edition}").split()
        )
    except RuntimeError:
        return set()


# -------------------------------------------------------------------- rendering


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text.replace("|", "/")


def description(manifest: dict) -> str:
    summary = clean_text(manifest.get("summary") or "")
    if summary and len(summary) > 12:
        return _clip(summary, DESC_MAX)
    desc = clean_text(manifest.get("description") or "")
    if desc:
        return _clip(desc, DESC_MAX)
    return "(no description in manifest)"


def blocker_text(module: str, edition: str) -> str:
    klass, repo = classify(module, edition)
    if not klass:
        return ""
    if klass == KLASS_FINNS_INTE:
        return f"`{module}` (finns inte i något addons-repo)"
    if klass == KLASS_TOM_GREN:
        return f"`{module}` ({repo}; {edition}-grenen är tom)"
    return f"`{module}` ({repo}; saknas i {edition})"


REPO_TYPES = (("odooext-OCA-", "OCA"), ("odoo-", "Vertel"))
REASON_MAX = 55
DESC_MAX = 80


def _clip(text: str, limit: int) -> str:
    """Klipp en mening vid ordgräns — tabellen ska rymmas på en skärm."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + " …"


def repo_type(repo: str) -> str:
    """Repo-typ för läsaren: OCA, Vertel eller core — inte fullt repnamn (D2)."""
    if repo in ("kärnan", "core", ""):
        return "core"
    for prefix, label in REPO_TYPES:
        if repo.startswith(prefix):
            return label
    return "Vertel"


def blocked_by(dep: str, edition: str) -> str:
    """`<modul> (<repo-typ>)` för ett saknat beroende (design D2)."""
    klass, repo = classify(dep, edition)
    if not klass:
        return f"{dep} (?)"
    return f"{dep} ({repo_type(repo)})"


REASON_CODES = (
    ("DEPRECATED", "deprecated"),
    ("INTE PORTBAR", "unported"),
    ("NOT PORTABLE", "unported"),
    ("BLOCKERAD", "broken"),
    ("BLOCKED", "broken"),
)


def disabled_reason(module: str, ref: str = "HEAD") -> str:
    """Läs orsaken ur kommentarerna ovanför 'installable': False (design D3)."""
    ref = _resolve_ref(ref)
    src = git("show", f"{ref}:{module}/__manifest__.py")
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"'installable':\s*False", line):
            inline = line.split("#", 1)[1].strip() if "#" in line else ""
            above = []
            j = i - 1
            while j >= 0:
                stripped = lines[j].strip()
                if not stripped.startswith("#"):
                    break
                above.insert(0, stripped.lstrip("#").strip())
                j -= 1
            text = " ".join(above + ([inline] if inline else []))
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                return "disabled: no reason in manifest"
            code = "disabled"
            for keyword, label in REASON_CODES:
                if keyword in text.upper():
                    code = label
                    break
            if ":" in text:
                head, tail = text.split(":", 1)
                tail = tail.strip()
                if tail:
                    return f"{code}: {_clip(tail, REASON_MAX)}"
            return f"{code}: {_clip(text, REASON_MAX)}"
    return "disabled: no reason in manifest"


def status_cell(module: str, edition: str, manifest: dict) -> str:
    """Ett värde: `ok` eller `blocked by <orsak>` (design D1)."""
    if manifest.get("installable", True) is False:
        return f"blocked by {disabled_reason(module)}"

    missing = [d for d in manifest.get("depends", []) if d not in edition_modules(edition)]
    if not missing:
        return "ok"
    parts = [blocked_by(d, edition) for d in missing]
    if len(parts) > 2:
        rest = len(parts) - 2
        parts = parts[:2] + [f"+{rest} more"]
    return "blocked by " + "; ".join(parts)


def render(edition: str) -> str:
    mods = module_dirs()
    cache = edition_modules(edition)
    lines = [
        f"{SECTION} — Odoo {edition}",
        "",
        f"Den här grenen är Odoo {edition}. Tabellen beskriver bara {edition}.",
        "",
        "Genererad av `scripts/porting-status.py` — handredigera inte.",
        "",
        "| Modul | Beskrivning | Porteringsstatus |",
        "|---|---|---|",
    ]
    for mod in mods:
        manifest = read_manifest(mod)
        cell = status_cell(mod, edition, manifest)
        lines.append(f"| `{mod}` | {description(manifest)} | {cell} |")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------- README I/O


def readme_path() -> str:
    return os.path.join(git("rev-parse", "--show-toplevel").strip(), "README.md")


def check_edition_matches(path: str, edition: str) -> None:
    """Avbryt om README-rubriken säger en annan utgåva (design D4)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    match = re.search(rf"^{re.escape(SECTION)} — Odoo (\d+\.0)$", text, re.M)
    if match and match.group(1) != edition:
        raise RuntimeError(
            f"README.md beskriver Odoo {match.group(1)} men grenen är {edition} — "
            f"byta gren eller rätta rubriken först"
        )


def write_section(path: str, body: str) -> None:
    """Ersätt från SECTION till filens slut; lämna allt före orört (design D7)."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = f"# {repo_name()}\n\n"
    idx = text.find(SECTION)
    if idx == -1:
        text = text.rstrip("\n") + "\n\n" + body
    else:
        text = text[:idx] + body
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ------------------------------------------------------------------- drift


def check_drift(edition: str) -> int:
    """Jämför summary för varje modul mellan utgåvorna (design D4)."""
    editions = ("18.0", "19.0", "20.0")
    drift = 0
    for mod in module_dirs(edition):
        texts = {}
        for ed in editions:
            try:
                man = read_manifest(mod, ed)
            except RuntimeError:
                continue
            texts[ed] = clean_text(man.get("summary") or "")
        present = {k: v for k, v in texts.items() if v}
        if len(set(present.values())) > 1:
            drift += 1
            print(f"DRIFT {mod}")
            for ed, text in present.items():
                print(f"  {ed}: {text}")
    print(f"{edition}: {drift} avvikelser över {', '.join(editions)}")
    return 1 if drift else 0


# ------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-only", action="store_true", help="skriv modullistan")
    parser.add_argument("--dump-manifests", action="store_true", help="skriv manifestfält")
    parser.add_argument("--dump-existence", action="store_true", help="skriv om modulen finns")
    parser.add_argument("--deps", metavar="UTGÅVA", help="räkna moduler utan saknade beroenden")
    parser.add_argument("--blockers", metavar="UTGÅVA", help="lista unika blockerare")
    parser.add_argument("--markdown", action="store_true", help="skriv tabellen")
    parser.add_argument("--check-drift", action="store_true",
                        help="jämför summary mellan 18.0/19.0/20.0")
    parser.add_argument("--write", action="store_true", help="skriv om README.md")
    parser.add_argument("--edition", help="överstyr utgåvan (annars ur grennamnet)")
    args = parser.parse_args(argv)

    try:
        branch = current_branch()
        edition = args.edition or edition_of(branch)

        if args.list_only:
            mods = module_dirs()
            print(f"{edition}: {len(mods)} moduler")
            for mod in mods:
                print(mod)
            return 0

        if args.dump_manifests:
            for mod in module_dirs():
                man = read_manifest(mod)
                print(
                    f"{edition}\t{mod}\t{man.get('version', '')}\t"
                    f"{man.get('installable', True)}\t"
                    f"{clean_text(man.get('summary') or '')}\t"
                    f"{','.join(man.get('depends', []))}"
                )
            return 0

        if args.dump_existence:
            cache = edition_modules(edition)
            for mod in module_dirs():
                print(f"{edition}\t{mod}\t{'ja' if mod in cache else 'nej'}")
            return 0

        if args.deps:
            cache = edition_modules(args.deps)
            ok = bad = 0
            for mod in module_dirs(args.deps):
                man = read_manifest(mod, args.deps)
                if man.get("installable", True) is False:
                    ok += 1
                    continue
                if any(d not in cache for d in man.get("depends", [])):
                    bad += 1
                else:
                    ok += 1
            print(f"{args.deps}: {ok} utan saknade beroenden, {bad} med")
            return 0

        if args.blockers:
            cache = edition_modules(args.blockers)
            seen: dict[str, list[str]] = {}
            for mod in module_dirs(args.blockers):
                man = read_manifest(mod, args.blockers)
                for dep in man.get("depends", []):
                    if dep not in cache:
                        seen.setdefault(dep, []).append(mod)
            print(f"{args.blockers}: {len(seen)} unika blockerare")
            for dep, mods in sorted(seen.items(), key=lambda kv: -len(kv[1])):
                klass, repo = classify(dep, args.blockers)
                print(f"  {len(mods):3d}  {dep:45s} {klass or 'ok':18s} {repo}")
            return 0

        body = render(edition)
        if args.check_drift:
            return check_drift(edition)

        if args.markdown:
            print(body)
            return 0

        if args.write:
            path = readme_path()
            check_edition_matches(path, edition)
            write_section(path, body)
            print(f"skrev {SECTION} — Odoo {edition} i {path}")
            return 0

        parser.print_help()
        return 0
    except RuntimeError as exc:
        print(f"FEL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
