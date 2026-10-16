#!/usr/bin/env bash
# Avvio locale sicuro: non cancella dati, non riscrive storia, non fa push.
set -euo pipefail

fail() { printf '\nERRORE: %s\n' "$*" >&2; exit 1; }
for program in git codex; do
  command -v "$program" >/dev/null 2>&1 || fail "$program non trovato. Installa/configura lo strumento prima di rilanciare."
done
BUNDLE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for name in PARK_REVIVE_Theory_and_Codex_Specification.pdf PARK_REVIVE_Theory_and_Codex_Specification.tex CODEX_PROMPT.md REPOSITORY_STATUS.md; do
  [[ -s "$BUNDLE_DIR/$name" ]] || fail "File del pacchetto mancante: $name"
done
REPO_DIR="${PARK_REVIVE_REPO:-$HOME/Projects/E-value-codex}"
if [[ ! -e "$REPO_DIR" ]]; then
  mkdir -p -- "$(dirname -- "$REPO_DIR")"
  git clone -- https://github.com/ENRICOBIGNOZZI/E-value.git "$REPO_DIR"
fi
[[ -d "$REPO_DIR" ]] || fail "Il percorso scelto non è una directory: $REPO_DIR"
ROOT="$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)" || fail "Non è un checkout Git: $REPO_DIR"
ORIGIN="$(git -C "$ROOT" remote get-url origin)"
case "$ORIGIN" in
  https://github.com/ENRICOBIGNOZZI/E-value|https://github.com/ENRICOBIGNOZZI/E-value.git|git@github.com:ENRICOBIGNOZZI/E-value.git) ;;
  *) fail "Origin inatteso ($ORIGIN). Nessuna modifica eseguita." ;;
esac
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)" ]] || fail "Il checkout ha modifiche o file non tracciati. Nessuno stash/reset automatico. Usa un checkout pulito oppure un nuovo PARK_REVIVE_REPO."
git -C "$ROOT" fetch origin
BACKUP="refs/remotes/origin/archive/pre-rebuild-20261016"
git -C "$ROOT" rev-parse --verify "$BACKUP" >/dev/null || fail "Backup remoto non trovato. Fermarsi e verificare il repository."
EXPECTED="db5c37ab3e23a7818869d32ba35f22d51c3a89b2"
[[ "$(git -C "$ROOT" rev-parse "$BACKUP")" == "$EXPECTED" ]] || fail "Il branch di backup non coincide con il commit documentato. Verificare prima di proseguire."
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$(git -C "$ROOT" rev-parse origin/main)" ]] || fail "Il checkout non coincide con origin/main. Nessun cambio di branch automatico fra tree diversi. Usa un nuovo percorso PARK_REVIVE_REPO."
BRANCH="codex/park-revive-$(date +%Y%m%d-%H%M%S)-$$"
git -C "$ROOT" switch -c "$BRANCH" origin/main
SPEC_DIR="$ROOT/docs/spec"
mkdir -p -- "$SPEC_DIR"
for name in PARK_REVIVE_Theory_and_Codex_Specification.pdf PARK_REVIVE_Theory_and_Codex_Specification.tex CODEX_PROMPT.md REPOSITORY_STATUS.md; do
  [[ ! -e "$SPEC_DIR/$name" ]] || fail "Non sovrascrivo un file esistente: $SPEC_DIR/$name"
  cp -- "$BUNDLE_DIR/$name" "$SPEC_DIR/$name"
done
printf '\nRepository: %s\nBranch: %s\nSpecifica: %s\n' "$ROOT" "$BRANCH" "$SPEC_DIR"
printf 'Main remoto non viene modificato. Nessun file dati viene cancellato.\n'
printf 'Un clone nuovo non contiene eventuali raw ignorati presenti in altri checkout.\n\n'
cd -- "$ROOT"
exec codex --sandbox workspace-write "$(cat -- "$SPEC_DIR/CODEX_PROMPT.md")"
