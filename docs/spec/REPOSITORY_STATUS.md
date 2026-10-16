# Stato verificato del repository

Data: 16 ottobre 2026.
Repository: https://github.com/ENRICOBIGNOZZI/E-value
Branch principale: main.
Commit osservato: db5c37ab3e23a7818869d32ba35f22d51c3a89b2.

## Operazioni effettuate

È stato creato il branch remoto di archivio `archive/pre-rebuild-20261016`, a partire dal commit sopra. La richiesta di creazione di un nuovo tree per ripulire main è stata bloccata. Non è stata eseguita alcuna cancellazione su main. Non sono state eseguite simulazioni per questo nuovo disegno.

## Dati osservati

La directory tracciata data contiene README.md e source_manifest_20261006.json. Il README indica che i raw sono intenzionalmente untracked. Il manifest riguarda USA monthly capped-value JKP: availability.json, all_factors.zip, mkt.zip, all_themes.zip. Contiene hash e provenienza delle acquisizioni storiche. Gli archivi raw non sono stati scaricati o copiati da questa sessione. Eventuali file ignorati presenti sul computer dell'utente devono essere inventariati e preservati da Codex.

Blob originali da non alterare:
- data/README.md: 05a118ae4160fe3da3b15f9ecb06eb76b1b4374c
- data/source_manifest_20261006.json: cc2ea8eaab42f521ef7c3a6ecb3ee9a8c718f6a4
Tree data: 4c71e7e81dff383d6993663948e9cf86f9b2def5.

Le fonti di verifica sono le risposte del connettore GitHub a repository metadata, branches/main, git trees, data/README.md e data/source_manifest_20261006.json. I file pubblici possono essere ricontrollati dal commit immutabile sopra.

## Politica operativa

Il launcher crea un branch locale nuovo e copia la specifica. Non cancella la vecchia implementazione. Codex deve preparare un piano di pulizia, preservare i dati e attendere l'approvazione prima delle rimozioni. Il package nuovo deve essere isolato dal vecchio. Nessun force push o cancellazione di storia.
