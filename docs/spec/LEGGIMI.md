# PARK/REVIVE — pacchetto per Codex

Versione 1.0, 16 ottobre 2026.

## Contenuto

- `PARK_REVIVE_Theory_and_Codex_Specification.pdf`: documento teorico e operativo di 28 pagine. Include T1–T4 con dimostrazioni, ipotesi, limiti, DGP unico, benchmark e criteri di accettazione.
- `PARK_REVIVE_Theory_and_Codex_Specification.tex`: sorgente LaTeX completo, utile per leggere le formule senza ambiguità di estrazione.
- `CODEX_PROMPT.md`: incarico dettagliato da fornire a Codex. Il launcher lo passa automaticamente come prompt iniziale.
- `REPOSITORY_STATUS.md`: stato effettivamente verificato del repository e dati da proteggere.
- `start_codex.sh`: prepara un branch locale di sviluppo e avvia Codex interattivo.
- `SHA256SUMS.txt`: impronte dei file del pacchetto, escluso il manifest stesso.

Non sono inclusi dati empirici, vecchi output pilota o risultati della nuova simulazione. Il codice della simulazione dovrà essere implementato da Codex. Il PDF è stato compilato e controllato nelle pagine renderizzate; il launcher ha superato il controllo sintattico Bash ma non è stato eseguito in questa sessione.

## Stato del repository

È stato creato il backup remoto `archive/pre-rebuild-20261016`, al commit `db5c37ab3e23a7818869d32ba35f22d51c3a89b2`.

**Main non è stato svuotato.** La richiesta di pulizia è stata bloccata. Il vecchio codice rimane su main e nel backup. Il prompt fa preparare a Codex un piano di rimozione da sottoporre ad approvazione; nel frattempo il nuovo package vive nel namespace isolato `src/park_revive/`.

I dati raw risultano esclusi dal tracking. Un clone nuovo contiene la documentazione e i manifesti presenti in Git, non necessariamente gli archivi sul tuo computer. Non assumere che un backup Git copi file ignorati. Il launcher non cancella o scarica sopra archivi esistenti.

## Avvio rapido su macOS/Linux

Servono Git, unzip e Codex CLI già installato e autenticato. Non è richiesto installare Python globalmente; Codex riceve istruzioni per creare un ambiente locale.

Scarica `PARK_REVIVE_HANDOFF.zip` in `~/Downloads`, poi incolla nel terminale:

```bash
(
  set -e
  HANDOFF="$(mktemp -d "$HOME/Downloads/park-revive.XXXXXX")"
  unzip -q "$HOME/Downloads/PARK_REVIVE_HANDOFF.zip" -d "$HANDOFF"
  bash "$HANDOFF/PARK_REVIVE_HANDOFF/start_codex.sh"
)
```

Il launcher usa per default `~/Projects/E-value-codex`. Se la directory non esiste, clona il repository pubblico. Verifica origin, stato pulito, coincidenza del checkout con origin/main e backup atteso; in caso di ambiguità si ferma, senza reset o stash automatici. Crea un branch `codex/park-revive-<timestamp>-<pid>`, copia la specifica in `docs/spec/` e apre Codex con il prompt completo.

Il launcher non esegue push, merge o cancellazioni della vecchia implementazione. Il comando Codex usa `--sandbox workspace-write`; ulteriori permessi dipendono dalla configurazione locale e dalle richieste esplicite di Codex.

## Checkout già esistente

Per usare un checkout che contiene dati raw locali, imposta `PARK_REVIVE_REPO` al percorso assoluto del repository quando avvii il launcher:

```bash
PARK_REVIVE_REPO="/percorso/assoluto/E-value" bash "/percorso/del/pacchetto/start_codex.sh"
```

Il checkout deve essere pulito per i file tracciati/non tracciati e avere HEAD uguale a origin/main. I raw ignorati non vengono rimossi. Se il controllo fallisce, non forzare un reset per proseguire: prima inventaria e metti al sicuro i dati.

## Uso senza launcher

In un branch di sviluppo del repository, copia PDF, sorgente e `REPOSITORY_STATUS.md` dentro `docs/spec/`. Quindi copia il contenuto integrale di `CODEX_PROMPT.md` in una sessione Codex collegata a quel repository. Il prompt dichiara che la pulizia non è stata eseguita e vieta rimozioni non approvate.

## Rigenerare il PDF

Con una distribuzione LaTeX che includa i pacchetti standard usati nel sorgente:

```bash
pdflatex -interaction=nonstopmode -halt-on-error PARK_REVIVE_Theory_and_Codex_Specification.tex
pdflatex -interaction=nonstopmode -halt-on-error PARK_REVIVE_Theory_and_Codex_Specification.tex
```

Le formule di T3 valgono nel caso dichiarato senza ulteriori vincoli. T2 non dimostra automaticamente potenza sotto alpha decay. Il limite di momento deve essere valido, non una varianza campionaria chiamata bound. Il documento e il prompt indicano questi confini: non rimuoverli nel paper finale.
