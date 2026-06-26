# Aggiornamento database di copertura

# Introduzione
Attualmente sono supportati tutti gli _operatori mobile e non_ con l'estrazione dei dati da file Netmonster (_ntm_) e file _csv_ (il parser csv presuppone che le colonne del file corrispondano a quelle nella tabella), con possibilità di implementare un parser specifico per altre eventuali estensioni.
Se non ti interessa il funzionamento salta direttamente al punto **"Come utilizzarlo?"**. In parole semplici, funziona nel seguente modo:
1. Cerca i file contenenti i nuovi dati di copertura nella cartella `data/<tipo di operatore: "mobile" o "simple">/<operatore>/inbox`. È possibile filtrare la ricerca per un'estensione specifica (es. .ntm).
2. In base all'estensione del file, istanzia automaticamente il parser corretto (es. NetmonsterParser per i file .ntm).
3. Avvia il processo di parsing, passa i dati al sincronizzatore del database e, in caso di successo, rinomina e sposta il file originale nella cartella `data/<tipo di operatore: "mobile" o "simple">/<operatore>/archive`, aggiungendo un timestamp.

# Come collegare il database
La configurazione del database deve essere inserita in un file `.env` (che ovviamente viene escluso da git) posto nella cartella principale del progetto. 

Dati da inserire:
```
DB_HOST="X.X.X.X"
DB_USER="root"
DB_PASSWORD=".rombo."
DB_NAME="check_coverage"
```

Ricordarsi di chiamare la funzione `load_dotenv(".env")` all'inizio di ogni script. Per il resto, non serve preoccuparsi di nulla, è tutto gestito dal `utils/database/db_connect.py`.

# Operatori
Nel file `utils/operator.py` si trovano tutti i dati e le logiche necessarie a modellare gli operatori. Di seguito i componenti principali:
1. **Operatore base (BaseOperator)**

   Rappresenta un generico operatore tramite una classe BaseOperator (un Enum).
   La classe automatizza diverse operazioni:
    - **Gestione Database**: Genera dinamicamente i nomi delle tabelle (`base_table`, `tmp_table`, `old_table`) basandosi sulle variabili d'ambiente.
    - **Gestione Percorsi (Path)**: Fornisce i percorsi assoluti standardizzati per leggere, archiviare o loggare i dati relativi all'operatore (base_path, inbox_path, archive_path, log_path).
    - **Metodi di Ricerca**: Offre il from_identifier per risolvere e trovare in modo sicuro un oggetto Operatore partendo dal suo nome (case-insensitive), includendo un sistema di logging in caso di errore.

2. **Operatori mobile (MobileOperator)**

    I dettagli del singolo operatore mobile sono specificati nella classe MobileOperator (una _sottoclasse_ di BaseOperator). Ogni operatore ha i seguenti dati:
    - **name**: Identifica l'operatore come ENUM (es. WINDTRE).
    - **value**: Nome dell'operatore come stringa identificativa (es. windtre).
    - **display_name**: Nome visualizzato (es. WindTre).
    - **mncs (Mobile Network Code)**: Codice univoco che identifica ogni operatore mobile. Da notare che un operatore può avere più di un MNC (esempio WindTre ha 88 e 99).
    - **specs**: Una struttura a dizionario che associa ogni banda supportata dall'operatore alle relative specifiche di ampiezza e velocità.
    - **db_columns**: Nomi delle colonne nel database usate per quello specifico operatore.
    
    Oltre ai dati statici, la classe automatizza diverse operazioni:
    - **Metodi di Ricerca**: Offre il metodi from_mnsc per risolvere e trovare in modo sicuro un oggetto Operatore partendo dal suo codice di rete, includendo un sistema di logging in caso di errore.

3. **Operatore (SimpleOperator)**
   
   Rappresenta un operatore NON-mobile. I dettagli del singolo operatore mobile sono specificati nella classe SimpleOperator (una _sottoclasse_ di BaseOperator). Ogni operatore ha i seguenti dati:
    - **name**: Identifica l'operatore come ENUM (es. FASTWEB_ONNET).
    - **value**: Nome dell'operatore come stringa identificativa (es. fastweb_onnet).
    - **display_name**: Nome visualizzato (es. Fastweb ONNET).
    - **db_columns**: Nomi delle colonne nel database usate per quello specifico operatore.
    

Per quanto riguarda gli operatori **mobile**, nel file `utils/lte_specs.py` si trovano tutti i dati e le logiche necessarie a modellare le specifiche delle reti mobili in Italia. Di seguito i componenti principali:

1 **Specifiche Tecniche della Rete**

    - **Bande LTE (LTEBand)**: Un Enum di tipo stringa che mappa le bande LTE usate in Italia (es. B28, B20, B3). Sovrascrivendo la creazione dell'oggetto, ad ogni stringa viene agganciata automaticamente la sua rispettiva frequenza in MHz (es. B20 = 800 MHz).
    - **Ampiezza di Banda (Bandwidth)**: Un Enum intero che cataloga i tagli di banda disponibili espressi in MHz (5, 10, 15, 20).
    - **Specifiche Congiunte (Spec)**: Una dataclass che mette in stretta correlazione una banda (LTEBand) con la sua relativa ampiezza (Bandwidth). Include la proprietà speed, che calcola automaticamente la velocità teorica in Mbps basandosi sulla regola generale di Wiki LTE Italy (1 MHz = 10 Mbps).

# Come funziona?

## 1. Orchestrazione (CoverageOrchestrator)
Si occupa di coordinare l'intero flusso di lavoro per ogni singolo operatore telefonico:

1. Cerca i file contenenti i nuovi dati di copertura nella cartella `data/<operatore>/inbox`. È possibile filtrare la ricerca per un'estensione specifica (es. .ntm).
2. In base all'estensione del file, istanzia automaticamente il parser corretto (es. NetmonsterParser per i file .ntm).
3. Avvia il processo di parsing, passa i dati al sincronizzatore del database e, in caso di successo, rinomina e sposta il file originale nella cartella `data/<operatore>/archive`, aggiungendo un timestamp.

## 2. Estrazione e trasformazione dati (Parsing)
### 2.1 NetmonsterParser
Responsabile della lettura e pulizia dei dati grezzi provenienti dai dati di copertura forniti dall'operatore.

1. Normalizza la tecnologia, trasformando le etichette 4G in LTE e DSS in 5G.
2. Estrae le combinazioni univoche di mnc e band_id per mappare istantaneamente i dati dell'operatore di riferimento (MobileOperator).
3. Filtra le colonne prelevando solo quelle necessarie al DB restituendo un dataframe.

### 2.2 CsvParser
Responsabile della lettura dei dati provenienti dai dati di copertura fornitri dall'operatore.

Al momento, _partendo dal presupposto che le colonne del file corrispondano con le colonne del db_, semplicemente filtra le colonne prelevando solo quelle necessarie al DB e restituisce un dataframe.

## 3. Sincronizzazione dati sul database (CoverageDbSynchronizer)
Sincronizza i dati sul DB, avendo cura di effettuare lo scambio delle tabelle in una singola transazione (atomic swap)!

1. Elimina eventuali tabelle temporanee residue e crea una nuova tabella _tmp copiando lo schema di quella originale.
2. Esporta il DataFrame in un file CSV temporaneo e utilizza la funzione di importazione massiva del database per popolare rapidamente la tabella _tmp.
3. Con una singola transazione (_atomic swap_), rinomina la tabella di produzione attiva in _old (funzionando da backup) e cambia la tabella _tmp a tabella attiva. Questo garantisce che gli utenti non leggano mai una tabella vuota o mezza aggiornata.
4. Aggiorna la tabella di sistema `check_coverage_coverageupdate` per registrare l'ora esatta dell'ultimo aggiornamento dati (prelevato da un metadata salvato sul dataframe).

## 4. Gestione errori
Sono gestiti i principali errori che possono avvenire durante l'esecuzione del programma. 

1. **Errori di Parsing** (Dati corrotti): Se un singolo file presenta dati malformati o solleva un'eccezione non legata al DB, il file viene spostato nella cartella log con il prefisso `<timestamp>_ERROR_`. Lo script non si ferma e procede con il file o l'operatore successivo.
2. **Errori di Database** (Connessione persa, crash): Se la sincronizzazione fallisce (es. il DB va offline), l'orchestratore elimina eventuali tabelle temporanee "orfane", il CSV temporaneo viene distrutto e il file dei dati viene lasciato nella cartella inbox. La pipeline viene interrotta in modo sicuro (tramite eccezione FATAL) per permettere di riprovare al successivo riavvio senza alcuna perdita di dati.

# Come utilizzarlo?

## Script principale
Lo script principale `sync.py` si trova nella cartella principale del progetto.

| PARAMETRI    | HELP                                                                                                                                                                                                                                             | VALORI                     | OBBLIGATORIO |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|--------------|
| `--operator` | Nome di uno o più operatori, se non specificato sincronizza tutti quelli presenti in OperatorMobile                                                                                                                                              | str                        | nope         |
| `--format`   | Formato dei file con i dati di copertura da prelevare nella cartella `data/<tipo di operatore: "mobile" o "simple">/<operator>/inbox`. Se non specificato preleva tutti i file presenti (anche se attualmente è supportato solo il formato ntm). | str                        | nope         |     
| `--debug`    | Mostra tante righe carine e utili di debug                                                                                                                                                                                                       | boolean, False di default  | nope         |  
| `--dry-run`  | Esegue una simulazione, senza modificare i dati nel database e senza spostare i file                                                                                                                                                             | boolean, False di default  | nope         |

Esempio:
```
# file ntm per vodafone e WindTre
python sync.py --operator vodafone windtre --format ntm

# file ntm per tutti gli operatori con linee di debug
python sync.py --format ntm --debug
```

> **ATTENZIONE**: la prima volta runnare il tool `create_mncs_table` prima di eseguire questo script!

## Eventuali tools
All'interno della cartella `tools` sono presenti tutti gli script che possono tornare utili.

Esempio:
```
python -m tools.my_cool_script --arg1 "hello world!"
```