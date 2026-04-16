# Aggiornamento database di copertura

Attualmente sono supportati solo gli _operatori mobile_ e l'estrazione dei dati da file Netmonster (_ntm_), con possibilità di implementare un parser specifico per altre eventuali estensioni.
Se non ti interessa il funzionamento salta direttamente al punto **"Come utilizzarlo?"**. In parole semplici, funziona nel seguente modo:
1. Cerca i file contenenti i nuovi dati di copertura nella cartella `data/<operatore>/inbox`. È possibile filtrare la ricerca per un'estensione specifica (es. .ntm).
2. In base all'estensione del file, istanzia automaticamente il parser corretto (es. NetmonsterParser per i file .ntm).
3. Avvia il processo di parsing, passa i dati al sincronizzatore del database e, in caso di successo, rinomina e sposta il file originale nella cartella `data/<operatore>/archive`, aggiungendo un timestamp.


# LTE Italy

Nel file `utils/lte_specs.py` si trovano tutti i dati e le logiche necessarie a modellare le specifiche delle reti mobili in Italia. Di seguito i componenti principali:
1. **Operatori mobile (MobileOperator)**

    I dettagli del singolo operatore sono specificati nella classe MobileOperator (un Enum). Ogni operatore ha i seguenti dati:
    - **name**: Identifica l'operatore come ENUM (es. VODAFONE).
    - **value**: Nome dell'operatore reale (es. Vodafone).
    - **mncs (Mobile Network Code)**: Codice univoco che identifica ogni operatore mobile. Da notare che un operatore può avere più di un MNC (esempio WindTre ha 88 e 99).
    - **specs**: Una struttura a dizionario che associa ogni banda supportata dall'operatore alle relative specifiche di ampiezza e velocità.
    - **db_columns**: Nomi delle colonne nel database usate per quello specifico operatore.
    
    Oltre ai dati statici, la classe automatizza diverse operazioni:
    - **Gestione Database**: Genera dinamicamente i nomi delle tabelle (`base_table`, `tmp_table`, `old_table`) basandosi sulle variabili d'ambiente.
    - **Gestione Percorsi (Path)**: Fornisce i percorsi assoluti standardizzati per leggere, archiviare o loggare i dati relativi all'operatore (base_path, inbox_path, archive_path, log_path).
    - **Metodi di Ricerca**: Offre i metodi from_mnsc e from_identifier per risolvere e trovare in modo sicuro un oggetto Operatore partendo dal suo codice di rete o dal nome (case-insensitive), includendo un sistema di logging in caso di errore.

2. **Specifiche Tecniche della Rete**

    - **Bande LTE (LTEBand)**: Un Enum di tipo stringa che mappa le bande LTE usate in Italia (es. B28, B20, B3). Sovrascrivendo la creazione dell'oggetto, ad ogni stringa viene agganciata automaticamente la sua rispettiva frequenza in MHz (es. B20 = 800 MHz).
    - **Ampiezza di Banda (Bandwidth)**: Un Enum intero che cataloga i tagli di banda disponibili espressi in MHz (5, 10, 15, 20).
    - **Specifiche Congiunte (Spec)**: Una dataclass che mette in stretta correlazione una banda (LTEBand) con la sua relativa ampiezza (Bandwidth). Include la proprietà speed, che calcola automaticamente la velocità teorica in Mbps basandosi sulla regola generale di Wiki LTE Italy (1 MHz = 10 Mbps).

## Come funziona?

### 1. Orchestrazione (CoverageOrchestrator)
Si occupa di coordinare l'intero flusso di lavoro per ogni singolo operatore telefonico:

1. Cerca i file contenenti i nuovi dati di copertura nella cartella `data/<operatore>/inbox`. È possibile filtrare la ricerca per un'estensione specifica (es. .ntm).
2. In base all'estensione del file, istanzia automaticamente il parser corretto (es. NetmonsterParser per i file .ntm).
3. Avvia il processo di parsing, passa i dati al sincronizzatore del database e, in caso di successo, rinomina e sposta il file originale nella cartella `data/<operatore>/archive`, aggiungendo un timestamp.

### 2. Estrazione e trasformazione dati (Parsing)
#### 2.1 NetmonsterParser
Responsabile della lettura e pulizia dei dati grezzi provenienti dai dati di copertura forniti dall'operatore.

1. Normalizza la tecnologia, trasformando le etichette 4G in LTE e DSS in 5G.
2. Estrae le combinazioni univoche di mnc e band_id per mappare istantaneamente i dati dell'operatore di riferimento (MobileOperator).
3. Filtra le colonne prelevando solo quelle necessarie al DB restituendo un dataframe.

### 3. Sincronizzazione dati sul database (CoverageDbSynchronizer)
Sincronizza i dati sul DB, avendo cura di effettuare lo scambio delle tabelle in una singola transazione (atomic swap)!

1. Elimina eventuali tabelle temporanee residue e crea una nuova tabella _tmp copiando lo schema di quella originale.
2. Esporta il DataFrame in un file CSV temporaneo e utilizza la funzione di importazione massiva del database per popolare rapidamente la tabella _tmp.
3. Con una singola transazione (_atomic swap_), rinomina la tabella di produzione attiva in _old (funzionando da backup) e cambia la tabella _tmp a tabella attiva. Questo garantisce che gli utenti non leggano mai una tabella vuota o mezza aggiornata.
4. Aggiorna la tabella di sistema `check_coverage_coverageupdate` per registrare l'ora esatta dell'ultimo aggiornamento dati (prelevato da un metadata salvato sul dataframe).

### 4. Gestione errori
Sono gestiti i principali errori che possono avvenire durante l'esecuzione del programma. 

1. **Errori di Parsing** (Dati corrotti): Se un singolo file presenta dati malformati o solleva un'eccezione non legata al DB, il file viene spostato nella cartella log con il prefisso `<timestamp>_ERROR_`. Lo script non si ferma e procede con il file o l'operatore successivo.
2. **Errori di Database** (Connessione persa, crash): Se la sincronizzazione fallisce (es. il DB va offline), l'orchestratore elimina eventuali tabelle temporanee "orfane", il CSV temporaneo viene distrutto e il file dei dati viene lasciato nella cartella inbox. La pipeline viene interrotta in modo sicuro (tramite eccezione FATAL) per permettere di riprovare al successivo riavvio senza alcuna perdita di dati.

## Come utilizzarlo?

### Script principale
Lo script principale `sync.py` si trova nella cartella principale del progetto.

| PARAMETRI    | HELP                                                                                                                                                                                                    | VALORI                     | OBBLIGATORIO |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|--------------|
| `--operator` | Nome di uno o più operatori, se non specificato sincronizza tutti quelli presenti in OperatorMobile                                                                                                     | str                        | nope         |
| `--format`   | Formato dei file con i dati di copertura da prelevare nella cartella `data/<operator>/inbox`. Se non specificato preleva tutti i file presenti (anche se attualmente è supportato solo il formato ntm). | str                        | nope         |     
| `--debug`    | Mostra tante righe carine e utili di debug                                                                                                                                                              | boolean, False di default  | nope         |  
| `--dry-run`  | Esegue una simulazione, senza modificare i dati nel database e senza spostare i file                                                                                                                    | boolean, False di default  | nope         |

Esempio:
```
# file ntm per vodafone e WindTre
python sync.py --operator vodafone windtre --format ntm

# file ntm per tutti gli operatori con linee di debug
python sync.py --format ntm --debug
```

### Eventuali tools
All'interno della cartella `tools` sono presenti tutti gli script che possono tornare utili.

#### Creare tabella mncs e popolarla

Lo script `create_mncs_table` si occupa di creare o aggiornare la tabella `check_coverage_coveragemncs`, inserendo, per ogni operatore:
- **mnc**: codice univoco dell'operatore.
- **supplier_id**: ID relativo all'operatore presente nella tabella `check_coverage_coverageupdate`. _(MyISAM non supporta le foreign key!)_

Se una riga esiste già la ignora senza lanciare alcun errore.

| PARAMETRI    | HELP                                                                                                        | VALORI                     | OBBLIGATORIO |
|--------------|-------------------------------------------------------------------------------------------------------------|----------------------------|--------------|
| `--operator` | Nome di uno o più operatori, se non specificato crea una riga per ogni operatore presente in OperatorMobile | str                        | nope         |

Se ti stessi chiedendo a che serve per inserire correttamente la data di ultimo aggiornamento dei dati degli operatori, facilitando la selezione dell'operatore tramite il codice univoco.
