# PARK/REVIVE — incarico completo di ricostruzione

Lavora nel repository ENRICOBIGNOZZI/E-value. Non limitarti a proporre un piano: implementa il progetto, verifica le proprietà, esegui i test e produci una pipeline riproducibile. Se una prova o un vincolo di questa specifica non regge, segnala il punto esatto con un controesempio o una correzione motivata. Non inventare risultati per completare il report.

## 0. Documenti vincolanti e obiettivo

Leggi integralmente `docs/spec/PARK_REVIVE_Theory_and_Codex_Specification.pdf` e il corrispondente `.tex`. Il sorgente contiene formule e riferimenti ricercabili: usalo per controllare eventuali ambiguità nell'estrazione del PDF. Questa specifica sostituisce la vecchia teoria e i vecchi risultati del repository. Leggi anche `docs/spec/REPOSITORY_STATUS.md`.

Il problema economico è decidere quali segnali aggiungere, rimuovere o sostituire nel portafoglio che possiamo effettivamente stimare. Il dataset deve contenere molti candidati senza alpha proprio, non cento alpha autentici. Il successo del metodo non è presupposto.

L'output richiesto è codice nuovo, test matematici, backtest rigorosamente OOS, benchmark comparabili, figure e tabelle riproducibili. Il PDF non contiene risultati della nuova simulazione già eseguita. Non riutilizzare file pilota o risultati legacy come prova della nuova versione.

## 1. Branch, backup e protezione dei dati

Il backup remoto creato è `archive/pre-rebuild-20261016`, al commit `db5c37ab3e23a7818869d32ba35f22d51c3a89b2`. Verifica che esista. La pulizia remota di `main` NON è stata eseguita; una richiesta di modifica è stata bloccata. Non assumere una directory vuota.

Lavora sul branch di sviluppo nuovo predisposto dal launcher, o creane uno `codex/park-revive-<timestamp>`. Non fare push, merge, force push, reset distruttivi o riscritture della storia senza nuova autorizzazione. Non cancellare branch o tag di archivio.

Prima di qualsiasi modifica, inventaria file tracciati, non tracciati e ignorati, dati raw/processed, archivi, LFS, dizionari, licenze, manifesti, metadata e script di acquisizione. Crea `reports/data_preservation_manifest.json` con percorsi, dimensioni e SHA-256; i file ambigui si preservano. Non eseguire `git clean -fdx`, cancellazioni ricorsive della radice o comandi che eliminino dati ignorati. Non stampare credenziali o contenuti privati nei log.

Prepara `reports/legacy_cleanup_plan.md` con l'elenco esatto dei file di ricerca obsoleti da rimuovere e dei dati/supporti da conservare. NON eseguire cancellazioni prima che il piano sia approvato esplicitamente. Nel frattempo implementa il package nuovo `src/park_revive/` in modo isolato: niente import o dipendenze implicite dal vecchio package. Nuovi output vanno in `outputs/park_revive_v1/`. Puoi lavorare senza distruggere la vecchia implementazione.

La cartella data tracciata contiene documentazione e manifesti JKP, non necessariamente gli archivi reali. Un clone nuovo non recupera i file raw ignorati su un altro computer. Verifica i byte disponibili e non dichiarare preservati o caricati archivi che non trovi. Non scaricare sopra copie esistenti. Eventuali nuove acquisizioni richiedono directory separate e nuovi manifesti.

## 2. Audit scientifico prima del coding

Scrivi `reports/theory_audit.md` con una mappa T1–T4 -> ipotesi -> formula -> unit test -> modulo. Verifica le prove nel PDF, in particolare:

- T1: supermartingala del singolo confronto/episodio con secondo momento condizionale limitato e lambda prevedibile.
- T2a: lambda oracle delta/(2*nu_squared) ottimizza un bound sulla potenza, non la potenza esatta.
- T2b–c: costo O(log K) e potenza del plug-in richiedono media condizionale costante e nu_squared costante. Non applicare la conclusione automaticamente ai regimi.
- T3: secondo momento M, non covarianza Sigma; stesso stato iniziale; nuova coordinata inizialmente nulla; formule chiuse senza altri vincoli. Con leva attiva risolvi il problema vincolato.
- T4: errore delle politiche rispetto all'oracle; distinguere confronto a stato comune da politiche shadow con stati diversi.

Non dichiarare controllo multiplo, ottimo globale della ricerca, massima potenza universale, identificazione istantanea del regime o nuovo risultato di letteratura senza fondamento. Non modificare la specifica per ottenere questi slogan.

## 3. Funzione economica unica e costi invariati

Implementa una sola funzione condivisa:

C_t(w,b) = c*||w-b||_1 + (eta/2)*(w-b)'*Lambda_t*(w-b).
U_{t+1}(w;b) = r_{t+1} - (gamma/2)*r_{t+1}^2 - C_t(w,b).
r_{t+1} = w' A_{t+1}.
J_t(w;b) = w' mu_t - (gamma/2)*w' M_t w - C_t(w,b).
M_t = E[A_{t+1} A_{t+1}' | F_t].

Solo soluzione A. Non sostituire M con la covarianza e non mettere il rendimento netto dentro il quadrato. La serie di rendimenti per equity/Sharpe è invece r_net=r_gross-C. Non calcolare lo Sharpe dell'utilità.

Stesso modello di costi per tutti. Niente nuovi costi basati su ADV, AUM, ordini azionari o ribilanciamento interno delle sleeve. La convenzione dichiarata è b=w_target_precedente: turnover delle allocazioni target, modello stilizzato già scelto. Gamma, c, eta e Lambda devono avere unità esplicite. Leva lorda ||w||_1<=L comune a tutti.

Supporto iniziale S=insieme vuoto. Non aggiungere un finto segnale risk-free. Il caso vuoto permette solo w=0; da posizioni non nulle si paga la liquidazione. Stime dei momenti expanding, refit ogni 252 osservazioni; shrinkage/stabilizzazione uguali per tutti e determinati nel training.

## 4. Un solo DGP finanziario

Implementa esattamente la struttura:
R_i,t+1^e = beta_i' F_t+1 + sum_j theta_j,t*f_j(Z_i,t) + epsilon_i,t+1.

N=500 azioni, D=30 caratteristiche, p=100 candidati, 4 fattori, 15 anni da 252 giorni. Training iniziale di 252 giorni. Libreria persistente con 20 caratteristiche di segnale e 10 di noise indipendenti dal primo blocco. Caratteristiche latenti AR(1), dipendenza a gruppi e trasformazione tanh; funzioni lineari, saturanti e interazioni come nel PDF. Salva la libreria delle funzioni e i suoi seed.

Composizione inderogabile: 15 persistenti, 10 deboli, 10 decay, 10 revive, 40 puro noise strutturale indipendente e 15 proxy correlate senza coefficiente proprio. Per tutti i 55 nulli strutturali imponi theta_j,t=0 e innovazione del coefficiente zero per ogni t. I loro segnali devono comunque variare: non usare colonne nulle. Le etichette sono riservate a truth/oracle.

Un unico stato Markov persistente controlla stress/recupero; un indicatore di primo deterioramento controlla il gruppo decay. Coefficienti con target di regime, persistenza e proiezione limitata. Non scegliere seed che contengono il numero di transizioni desiderato.

Innovazioni fattoriali e idiosincratiche Laplace simmetriche a varianza uno, scale limitate e maggiori in stress. Beta limitati. Rispetta i parametri iniziali nel PDF; salva ogni valore e ogni convenzione. La scala dei coefficienti può essere calibrata SOLO su seed dedicati, usando plausibilità di volatilità, Sharpe delle sleeve, correlazioni e costi, mai la performance relativa del nostro algoritmo.

Costruisci sleeve long/short dalle funzioni, demean cross-sectional e normalizza per leva lorda <=1. Pesi basati su informazioni al tempo t, rendimento al t+1. Il learner riceve soltanto dati osservabili e limiti pubblici di rischio, non theta, regime nascosto, momenti oracle o etichette. Separa materialmente la vista learner dalla vista truth. Non neutralizzare tutti i fattori di default.

## 5. Confronti, shadow policies e calendario

Ogni confronto ha ID immutabile, data di avvio, S, B, regola di investimento, parametri, stato iniziale e serie di score. Usa sempre Y=U(B)-U(S).

Forward: B=S union {j}. Backward/PARK: B=S minus {j}. Swap: B=(S minus {i}) union {j}. Tutti testano se il candidato migliora il riferimento, senza doppie inversioni del segno.

Due politiche shadow partono dallo stesso stato all'avvio, poi mantengono ciascuna il proprio stato. Ciascuna paga i propri costi. Quando scegli una mossa, ricalcola i pesi dal vero stato del fondo: non trasferire gratuitamente lo stato shadow. Registra separatamente costo ipotetico e costo effettivo.

Training expanding e serie di evidenza non sono lo stesso oggetto. I punteggi OOS vengono prodotti una sola volta e non riscritti dopo il refit. Un cambio di S chiude i vecchi confronti e apre i nuovi sui dati futuri. Un normale aggiornamento dei parametri di una politica adattiva dichiarata può mantenere il confronto. Non usare vecchi score ottenuti per un diverso S.

La specifica operativa iniziale ammette AL MASSIMO UNA MODIFICA STRUTTURALE PER REVISIONE ANNUALE, come esplicitato nel PDF. È un default aggiunto per avere cronologia rigorosa: dichiarane il limite di 14 mosse in 14 anni OOS. Non fare una catena di mosse dentro la stessa revisione usando confronti testati sul precedente riferimento. Se questo limite rende il disegno inadatto, segnala il problema; non aggirarlo con leakage o cambi di protocollo silenziosi.

## 6. Forward–Backward–Swap10

All'inizio del blocco prepara tutti i Forward, tutti i Backward e gli swap con i 10 migliori esclusi secondo il ranking Forward calcolato sul training disponibile. La shortlist deve essere nota prima dei dati che validano gli swap. I pareggi si risolvono con ID del segnale stabili rispetto alla permutazione delle colonne.

A fine blocco scegli prima il miglior Forward eleggibile; in assenza, il miglior Backward; in assenza, il miglior Swap. Fra mosse eleggibili scegli maggiore media OOS positiva e usa tie-breaking stabile. Altrimenti mantieni S. Gli esclusi restano candidati anche dopo PARK. Non eliminare definitivamente i noise usando la loro etichetta vera.

Costo per passata: p+s*min(10,p-s) confronti, oltre al riferimento condiviso. Non chiamarlo tempo totale o O(p) senza condizioni. Usa caching, warm starts e riuso del riferimento senza cambiare i risultati.

## 7. Catoni e lambda stimato

Implementa in log:
phi(x)=sign(x)*log(1+abs(x)+x*x/2).
logE += phi(lambda*Y) - 0.5*lambda^2*nu_squared.

La formula deve essere numericamente stabile anche per x grande: evitare overflow del quadrato, usare log1p e un ramo equivalente per grandi moduli. Verifica disparità e le disuguaglianze del PDF.

La versione principale usa un limite nu_squared costante, valido per la classe DGP e derivato analiticamente da momenti, leva e costi, prima dei seed di test. Non usare la varianza campionaria come bound certificato. Non passare i momenti individuali veri dall'oracle al metodo E. Documenta chiaramente informazione pubblica dell'involucro vs informazione nascosta.

lambda_star = delta/(2*nu_squared) è solo oracle diagnostico. Per k>=2, lambda_hat_k = max(0, mean_Y_del_confronto_fino_al_blocco_precedente)/(2*nu_squared). È ammessa proiezione su [0,1/(2*sqrt(nu_squared))]. Primo blocco: effetto di progetto delta0 e lambda1 fissati prima, dichiarati in config. Nessuna ottimizzazione di lambda sui dati su cui poi riporti significatività. Conserva le somme dal solo episodio corrente.

Decisioni soltanto a fine blocco, soglia corrente logE>=log(20), livello individuale 5%. Nessuna correzione multipla come richiesto; nessuna pretesa di livello globale. Una variante con bound prevedibile più stretto o momenti plug-in va separata e correttamente etichettata: non sostituire il metodo principale senza consenso.

## 8. Benchmark comuni

Implementa i cinque benchmark obbligatori: All Signals, Greedy, Repeated-HAC-p, E-process PARK/REVIVE, Oracle.

All Signals: tutti i 100 segnali disponibili nello stesso ottimizzatore, non equal-weight obbligatorio. Greedy: stessa ricerca e stesso calendario, accetta migliore media OOS positiva senza soglia. P-value: stesse politiche, score, episodi, liste e ranking; t-statistica unilaterale con varianza HAC Bartlett e bandwidth floor(4*(n/100)^(2/9)), p=1-Phi(t). La ripetizione annuale non è corretta; dichiaralo e misurane la calibrazione. Non usare t-test IID se i dati sono dipendenti.

Oracle: veri momenti correnti, stessi vincoli e costi, nessuno shock futuro. È un oracle di utilità di un periodo, non un'upper bound pathwise sull'equity o sullo Sharpe. Calcola anche oracle state-matched per i regret. Tutti hanno le stesse date OOS; non nascondere il costo dell'attesa del metodo E.

## 9. Verità economica, potenza e falsi positivi

Salva separatamente coefficienti/etichette strutturali e contributo economico vero delle politiche implementate. Un theta=0 può coprire rischio o fungere da proxy. Non contarlo automaticamente come falso positivo economico.

Il valutatore calcola E[Y|G_t] e, dove utile, E[Y^2|G_t] con le formule Laplace dell'appendice; verifica contro Monte Carlo condizionale indipendente. Tali quantità non alimentano il learner.

Distingui: potenza del singolo test, probabilità che una mossa sia selezionata, precision/recall strutturali, precision economica, quota di noise selezionato, errori di segno corrente e errori di tipo I dell'intera null di episodio. Non classificare episodi nulli ex post guardando il loro percorso e poi usare quella selezione per affermare controllo nominale.

Per PARK/REVIVE misura ritardi, censura e quota di eventi non rilevati. Non riportare soltanto il ritardo medio fra i successi. L'evidenza vecchia può rallentare il riconoscimento del nuovo regime: non resettarla a posteriori per migliorare i risultati.

## 10. Metriche, equity lines e figure

Primaria: media OOS di U, con costo fuori dal quadrato. Secondarie: rendimento netto, Sharpe annualizzato, drawdown massimo, turnover, costi per componente, leva, giorni inattivi, numero di segnali e mosse, ritardi e runtime.

Equity: W_{t+1}=W_t*(1+r_net). Gestisci insolvenze esplicitamente, senza eliminare seed. Sharpe a varianza nulla = NA, con conteggio dei percorsi inattivi. Aggiungi versione long-run-variance se la dipendenza rende fuorviante la semplice annualizzazione.

Common random numbers per confronti appaiati. Mostra equity di un seed fissato prima, mediana/quantili fra seed, distribuzione Sharpe e differenze appaiate, utilità netta e costi, curve di potenza, precision/recall, noise selezionato, stati ACTIVE/PARK e ritardi censurati. Intervalli sulle repliche/seed, non sui milioni di osservazioni correlate. Nessuna selezione del seed più favorevole.

## 11. Architettura e riproducibilità

Crea i moduli indicati nel PDF con API tipizzate, configurazioni validate, logging, errori espliciti, generatori random indipendenti per DGP/learner/evaluator, checkpoint e resume senza doppio conteggio. Usa un ambiente virtuale locale e registra le versioni realmente installate. Niente installazioni globali, credenziali nel codice o dipendenze inventate.

Config separate smoke/pilot/main/empirical. Salva config, seed, commit, hash, ambiente, runtime e stato completato/interrotto. CLI unica con comandi per audit, simulate, report, empirical e resume. Ogni figura deve derivare dai file numerici prodotti.

Output obbligatori: data_preservation_manifest.json, legacy_cleanup_plan.md, theory_audit.md, config_frozen.json, seed_manifest.json, environment.txt, metrics_by_seed.csv, paired_comparisons.csv, daily_ledger.parquet, comparison_events.parquet, decisions.csv, detection.csv, runtime.csv, report PDF/Markdown e figure. Gli output grandi restano fuori dal tracking ordinario.

## 12. Test di accettazione prima del pilot

Implementa i dodici gruppi di test della sezione software del PDF: phi, T1, T2, T3, T4, momenti Laplace, costi, caso vuoto, causalità, immutabilità dei punteggi, reset, confronto identico, permutazione, noise esatto, separazione learner/oracle, shortlist prevedibile, checkpoint e metriche degeneri.

Un test particolarmente importante modifica il futuro del dataset e verifica che pesi, lambda, shortlist e decisioni precedenti rimangano identici. Verifica anche che le statistiche E e P usino la stessa serie Y per un confronto comune. Solver: tolleranze, fattibilità, PSD, valore obiettivo e residui KKT devono essere controllati.

## 13. Esecuzione graduale, non risultati inventati

Completa audit e test unitari. Esegui tre smoke ridotti con gli stessi meccanismi, dichiarandoli non rappresentativi del DGP principale. Misura costo per seed. Prepara ed esegui il pilot a configurazione principale, iniziando da un batch piccolo e con checkpoint; obiettivo 100 seed. Non lanciare migliaia di solver per ore senza prima misurare e documentare il costo.

Dopo il pilot, produci report di calibrazione, power/runtime, limiti di momento, quante selezioni avvengono e perché. Il main ha 500 seed nuovi e configurazione congelata; rendilo avviabile e riprendibile. Se il limite di esecuzione impedisce di completarlo, lascia comando e stato esatto, non dichiararlo eseguito. Non avviare job in background non tracciati.

Se il metodo resta quasi sempre vuoto, mostralo: non abbassare la soglia, il bound o cambiare la famiglia di DGP per farlo vincere. Ogni modifica successiva deve essere dichiarata, conservare il pilot precedente e usare seed nuovi.

## 14. Empirica reale

Non eliminare né alterare i dati JKP preservati. Verifica file disponibili, hash, unita decimali, segni già applicati, date, duplicati e licenza. Il manifest storico riguarda USA monthly capped-value. Non creare daily sintetici da monthly e non imputare rendimenti pre-lancio.

Implementa un loader in sola lettura e report di disponibilità. Se raw mancanti, descrivi esattamente quali mancano e lascia la pipeline funzionante su input conformi; non inventare dati. Per serie monthly usa h=12 e parametrizzazione alla frequenza corretta, in una pipeline separata dal Monte Carlo daily. Niente pretesa di ricostruire market impact azionario dai soli rendimenti aggregati di fattori.

## 15. Consegna finale di Codex

Restituisci: elenco dei file creati/modificati; branch e commit locale eventuale; stato del piano di pulizia senza cancellazioni non approvate; verifica degli hash dei dati; test passati/falliti; seed davvero eseguiti; configurazione congelata; percorsi dei risultati; comandi esatti per replicare e continuare; limiti economici/statistici osservati.

Il README deve consentire di ricreare l'ambiente e il primo smoke con pochi comandi. Riporta separatamente ciò che è implementato, verificato, eseguito e soltanto predisposto. Non dire che il paper è completo o che il metodo è superiore prima di avere i risultati necessari. Non fare push o merge automatici.
