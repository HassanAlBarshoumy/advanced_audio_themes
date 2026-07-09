# Temi Audio Avanzati (Advanced Audio Themes)

Questo componente aggiuntivo offre un'esperienza audio immersiva per gli utenti dello screen reader NVDA riproducendo suoni per vari eventi dell'interfaccia utente. Consente la creazione, l'installazione e la personalizzazione di temi audio, migliorando il feedback uditivo dell'interfaccia utente.

## Caratteristiche

- **Effetti audio:** Riproduce suoni per eventi dell'interfaccia utente, come la focalizzazione sui controlli, la navigazione negli elenchi e altro ancora.
- **Audio 3D:** Utilizza Steam Audio per fornire audio posizionale 3D, dando un'idea della posizione dei controlli sullo schermo.
- **DSP audio avanzato:** Elaborazione audio in tempo reale che include potenziamento dei bassi (Bass Boost), noise gate, ritaglio del silenzio (Silence Trimming), normalizzazione intelligente del volume ed inviluppi fluidi (Smooth Envelopes).
- **Attenuazione audio (Ducking):** Abbassa automaticamente il volume del tema quando NVDA parla per garantire la chiarezza vocale.
- **Riverbero:** Aggiunge effetti di riverbero all'audio per un'esperienza più immersiva.
- **Temi personalizzabili:** Consente agli utenti di creare, installare e passare da un tema audio all'altro.
- **Audio Themes Studio V2:** Uno strumento integrato per creare nuovi temi audio o modificare quelli esistenti direttamente dal microfono o tramite trascinamento (drag & drop).
- **Formati audio estesi:** Supporto FFmpeg integrato per MP3, FLAC, OGG, M4A e altro.
- **Suoni di digitazione avanzati:** Simula la digitazione su una tastiera fisica con posizionamento audio spaziale, regolazione dinamica del volume in base alla velocità (velocity) e mappatura intelligente dei tasti per tasti speciali (Invio, Backspace, Spazio, Maiusc, Ctrl, Alt).
- **Digitazione contestuale:** Opzione per limitare la riproduzione dei suoni di digitazione solo all'interno dei campi di testo modificabili.
- **Barre di avanzamento intelligenti:** Variazione dinamica dell'intonazione (pitch shifting) per le barre di avanzamento (tonalità più alta = percentuale più alta).
- **Rilevamento del primo/ultimo elemento:** Riproduce uno specifico suono di "urto" (bump) quando si raggiunge il limite di un elenco o di un menu.
- **Segnale/Sonar audio:** Rilascia un segnale audio spaziale in qualsiasi punto dello schermo e naviga intorno per ascoltare echi sonar in tempo reale che ti guidano rispetto al segnale.
- **Navigazione avanzata:** Motori SentenceNav e BrowserNav integrati per una navigazione fluida nel testo e nel web senza conflitti con i tasti freccia.
- **Livello di navigazione:** Premi NVDA+Win+N per accedere a una modalità di navigazione rapida in cui i tasti freccia si muovono per frasi, paragrafi o altri elementi senza tenere premuti i modificatori.
- **Store dei temi nel cloud:** Scarica, ascolta in anteprima e installa i temi creati dalla comunità direttamente dall'interno di Audio Themes Studio.
- **Profili specifici dell'app:** Passa automaticamente a un tema audio e a un pacchetto di suoni di digitazione specifici in base all'applicazione attiva.

- **Suoni di Stato del Sistema (System Status Sounds):** Riproduce segnali audio per eventi a livello di sistema come variazioni di alimentazione CA, stato della batteria, connessione di dispositivi USB e connettività di rete.
- **Miglioramento Emoji:** Motore di elaborazione emoji che migliora la pronuncia e la gestione degli emoji nell'intera interfaccia.
- **Annunci degli Appunti:** Riproduce segnali audio quando si copia, taglia o incolla contenuto negli appunti.

## Sviluppo e Riconoscimenti

Lo sviluppo e il consolidamento di questo componente aggiuntivo sono iniziati all'inizio di maggio (precisamente il 3 maggio 2026) esclusivamente da parte di **Hassan AlBarshoumy**.

Tutto il refactoring del codice, i consolidamenti strutturali e le integrazioni della GUI (incluso Audio Themes Studio V2 e le finestre di dialogo delle impostazioni unificate) sono stati eseguiti per garantire la massima stabilità e compatibilità con NVDA 2026.1+.

**Sviluppatore principale e consolidatore:**
* Hassan AlBarshoumy

**Crediti e Ringraziamenti:**
Questo componente aggiuntivo ha beneficiato notevolmente della fusione e dello sviluppo di precedenti progetti open source nella comunità NVDA. Un ringraziamento speciale agli sviluppatori originali:
* **Ahmed Sami:** Sviluppatore originale del componente aggiuntivo navSounds (Navigation Sound Effects) e per i suoi contributi.
* **Musharraf Omer:** Sviluppatore originale del componente aggiuntivo Audio Themes 3D.
* **Tony Malykh:** Sviluppatore originale dei componenti aggiuntivi Earcons and Speech Rules, BrowserNav, SentenceNav e TextNav.
* **Austin Hicks e Bryan Smart:** Sviluppatori originali del componente aggiuntivo Unspoken.

**Contatti e aggiornamenti:** [https://t.me/HassanAlBarshoumy](https://t.me/HassanAlBarshoumy)

## Installazione

1. Scarica l'ultima versione del componente aggiuntivo dal canale ufficiale di Hassan.
2. Apri il file `.nvda-addon` scaricato.
3. NVDA ti chiederà di confermare l'installazione. Scegli "Sì".
4. Riavvia NVDA per completare l'installazione.

## Come si usa

### Abilitazione/Disabilitazione dei temi audio

Puoi abilitare o disabilitare la funzionalità dei temi audio nelle impostazioni di NVDA:

1. Apri il menu NVDA (NVDA+N).
2. Vai su "Preferenze" -> "Impostazioni".
3. Nella finestra di dialogo delle impostazioni, seleziona la categoria "Temi audio".
4. Seleziona o deseleziona la casella di controllo "Abilita temi audio".

### Selezione e gestione dei temi

- **Informazioni su un tema:** Fai clic sul pulsante "Informazioni" per visualizzare le informazioni sul tema selezionato.

### Panoramica delle schede delle impostazioni

Il pannello delle impostazioni Temi audio avanzati contiene diverse schede per personalizzare ogni aspetto dell'esperienza audio. Di seguito un approfondimento su ogni opzione disponibile:

#### 1. Scheda Generale
- **Abilita temi audio:** Interruttore principale per accendere o spegnere il motore dei temi audio.
- **Seleziona tema:** Menu a discesa per scegliere il tema audio attivo tra quelli installati.
- **Informazioni / Rimuovi / Aggiungi nuovo:** Gestisci i tuoi temi. Puoi installare nuovi temi da file `.atp` o `.zip`.
- **Store dei temi:** Apre lo store integrato per scaricare i temi creati dalla community.
- **Theme Studio:** Apre lo studio per modificare o remixare il tema attualmente selezionato.
- **Anteprima:** Riproduce una sequenza di suoni campione del tema attivo.
- **Riproduci i suoni in modalità 3D:** Abilita l'elaborazione dell'audio spaziale.
- **Annuncia i ruoli:** Scegli se NVDA deve pronunciare i ruoli dei controlli (come "pulsante", "link").
- **Annuncia i ruoli durante leggi tutto:** Abilita o disabilita la pronuncia dei ruoli durante la lettura continua. Puoi usare il pulsante "Seleziona ruoli..." per specificare esattamente quali ruoli pronunciare.
- **Usa il volume del sintetizzatore vocale:** Collega il volume del tema al volume della voce di NVDA. Disabilitalo per usare il cursore manuale.
- **Attenuazione audio (Ducking):** Abbassa il volume dell'audio di sottofondo quando NVDA parla. Puoi scegliere quali categorie di suoni attenuare e impostare la percentuale del volume attenuato.
- **Comportamenti di fallback:** Definisce cosa succede quando manca un suono per un ruolo specifico o per un primo/ultimo elemento (ad esempio, riproduci silenzio, riproduci un suono personalizzato o riproduci il primo suono disponibile).
- **I suoni di stato sopprimono il suono del ruolo:** Se un elemento ha un suono di stato (ad es. casella di controllo attivata), impedirà la riproduzione del suono del ruolo per evitare confusione audio.
- **Lista nera (Blacklist) applicazioni:** Un elenco separato da virgole di eseguibili di applicazioni in cui i temi audio devono essere completamente disabilitati. Puoi anche personalizzare quali categorie specifiche di suoni vengono soppresse in queste app.
- **Suoni di digitazione:** Abilita i suoni della macchina da scrivere o della tastiera meccanica. Le opzioni includono la digitazione spaziale (simulazione delle posizioni fisiche sulla tastiera), la mappatura spaziale intelligente, la restrizione dei suoni alle caselle di modifica, la selezione di pacchetti di suoni e la regolazione del volume.
- **Gestione della configurazione:** Cerca aggiornamenti, includi le versioni beta ed esporta/importa l'intera configurazione (inclusi temi, regole e suoni) in un singolo file `.atcfg`.

#### 2. Scheda Motore Audio
- **Normalizzazione intelligente del volume:** Regola dinamicamente i suoni deboli e forti a un livello costante.
- **Inviluppo fluido:** Applica micro dissolvenze in apertura e in chiusura per evitare crepitii o clic audio.
- **Panning 3D fluido:** Crea un effetto di scivolamento quando gli oggetti si spostano sullo schermo invece di saltare istantaneamente.
- **Caching in RAM:** Carica i suoni in memoria per una riproduzione a latenza zero.
- **Ritaglia silenzio:** Rimuove automaticamente gli spazi silenziosi all'inizio e alla fine dei file audio in base a una soglia personalizzabile.
- **Noise Gate:** Elimina il sibilo di sottofondo di basso livello dai temi audio registrati male. Include i cursori per Soglia, Attacco e Rilascio.
- **Potenziamento dei bassi (Bass Boost):** Migliora le basse frequenze per dare più corpo ai suoni. Include cursori per Guadagno e Frequenza di taglio.
- **Modalità di uscita audio:** Passa dall'audio spaziale 3D completo (Stereo) a quello centrato (Mono).
- **Audio spaziale della barra di avanzamento:** Scegli se le barre di avanzamento eseguono il panning da sinistra a destra in base alla loro percentuale di avanzamento o in base alla loro posizione fisica sullo schermo. Include anche un interruttore per alzare la tonalità all'aumentare dell'avanzamento.

#### 3. Scheda Riverbero
Simula l'acustica ambientale per far sembrare i suoni riprodotti in una stanza fisica.
- **Abilita riverbero:** Interruttore principale per gli effetti ambientali.
- **Dimensioni della stanza:** Regola la dimensione percepita della stanza virtuale.
- **Smorzamento (Damping):** Controlla la rapidità con cui le alte frequenze vengono assorbite (simulando pareti morbide rispetto a quelle dure).
- **Livello bagnato / Livello asciutto (Wet/Dry):** Bilancia la quantità di riverbero elaborato rispetto al suono pulito originale.
- **Ampiezza (Width):** Regola la diffusione stereo della coda del riverbero.

#### 4. Scheda Formati Audio
- **Usa FFmpeg:** Abilita il supporto per formati audio compressi come MP3, FLAC, M4A e OGG.
- **Stato FFmpeg:** Mostra se FFmpeg è installato. In caso contrario, viene fornito un pulsante per scaricarlo ed estrarlo automaticamente (~12 MB).

#### 5. Scheda Earcons & Regole di Pronuncia
Un potente motore di regole per la pronuncia fonetica e i suoni di stato personalizzati.
- **Elenco delle regole:** Mostra tutte le regole attive filtrate per categoria (Ruolo, Stato, Testo, Carattere, ecc.).
- **Editor delle regole:** Quando aggiungi o modifichi una regola, puoi definire:
  - **Modello / Valore:** Il modello Regex, il ruolo o lo stato da far corrispondere.
  - **Tipo di azione:** Scegli di riprodurre un wave integrato, un file wav personalizzato, un segnale acustico, regolare la prosodia (tono/velocità), sostituire il testo o non fare nulla.
  - **Azione vocale:** Decidi se NVDA deve mantenere il testo originale, modificare il testo pronunciato o essere completamente silenziato quando la regola corrisponde.
  - **Regolazioni audio:** Cursore del volume, offset di ritaglio iniziale/finale (in millisecondi), tonalità/durata per i segnali acustici.
  - **Filtri:** Limita la regola ad applicazioni specifiche, titoli di finestre o URL di siti Web (è supportata l'espressione regolare Regex).
- **Operazioni batch:** Esporta/importa dizionari di regole, abilita/disabilita tutte le regole o testa le regole direttamente dall'interfaccia.

#### 6. Scheda Varie
Configurazione avanzata per i moduli di navigazione.
- **Navigazione per frasi (Alt+Frecce):** Regola il volume dei segnali acustici per i confini dei paragrafi, attiva gli annunci di formattazione, configura l'omissione dei riferimenti di Wikipedia, regola la ricostruzione della frase tra i paragrafi e definisci caratteri di punteggiatura personalizzati per la suddivisione di frasi/proposizioni.
- **Navigazione del testo (Alt+Maiusc+Frecce):** Regola il volume del crepitio e configura i comportamenti del segnale acustico di fine testo.
- **Navigazione web avanzata (BrowserNav):** Regola il volume del crepitio e dei segnali acustici durante la navigazione QuickSearch, e imposta il volume del segnale per saltare il disordine (Skip Clutter).
- **Livello di navigazione (NVDA+Win+N):** Configura i timeout di uscita automatica, i suoni delle azioni del livello, i tasti pass-through (ignora tasto) e attiva o disattiva modalità di navigazione specifiche.

#### 7. Scheda Ordine di Lettura
- **Formato di annuncio globale:** Cambia il modo in cui NVDA legge gli elementi a livello globale (es. Predefinito: Nome -> Ruolo -> Stato, o Stato -> Ruolo -> Nome).
- **Personalizzazione per ruolo:** Usa la casella di ricerca per trovare ruoli specifici (come Casella di controllo o Link) e assegna loro un formato di annuncio univoco.

#### 8. Scheda Profili App
- Cambia automaticamente le esperienze audio in base all'applicazione attiva.
- **Aggiungi profilo:** Inserisci l'eseguibile di un'applicazione (es. `chrome.exe`) e assegna uno specifico Tema Audio e/o un Pacchetto Suoni di Digitazione che si attiverà istantaneamente quando passi a quell'app.

#### 9. Scheda Ricerca Rapida e Segnalibri
- Gestisci regole di navigazione specifiche per dominio per la navigazione web.
- Assegna tasti (come J o K) per passare rapidamente a elementi specifici (QuickJump), saltare automaticamente i menu disordinati (SkipClutter) o eseguire script Python personalizzati su siti Web specifici.

#### 10. Scheda Primo/Ultimo Elemento
- **Abilita il rilevamento del primo/ultimo elemento:** Riproduce un suono di "urto" (bump) unico quando raggiungi l'inizio o la fine di un elenco, di un menu o di una visualizzazione ad albero.
- **Ambito di rilevamento:** Applica questo universalmente a tutti i ruoli o selettivamente a ruoli specifici (utilizzando il pulsante "Seleziona ruoli").
- **Comportamento per gli elementi singoli:** Decidi se gli elementi che sono gli unici presenti in un elenco devono essere trattati come il primo, l'ultimo o essere ignorati completamente.

#### 12. Scheda Appunti
- Configura gli annunci sonori degli appunti per le operazioni di copia, taglio e incollaggio del contenuto. Consente di selezionare suoni personalizzati e regolare il volume delle notifiche degli appunti.

#### 13. Scheda Emoji
- Configura il motore di miglioramento degli emoji. Consente di regolare la pronuncia, la sostituzione del testo e il comportamento dell'elaborazione degli emoji nell'intera interfaccia.

### Utilizzo di Audio Themes Studio V2

Audio Themes Studio consente di creare e modificare temi audio. Per aprire lo studio:

1. Apri il menu NVDA (NVDA+N).
2. Seleziona "Audio Themes Studio".

Nello studio puoi:

- **Creare un nuovo tema audio:** Questo ti guiderà attraverso il processo di creazione di un nuovo tema da zero.
- **Personalizzare un tema audio esistente:** Seleziona questa opzione per modificare i suoni di un tema installato.
- **Registrare dal microfono:** Ora puoi registrare nativamente la tua voce o qualsiasi suono direttamente dal tuo microfono per assegnarlo a un evento dell'interfaccia utente!
- **Trascina e rilascia (Drag & Drop):** Puoi trascinare e rilasciare file audio direttamente nella finestra di Studio per assegnarli rapidamente.
- **Store dei temi nel cloud:** Sfoglia, ascolta in anteprima e scarica i temi creati dalla community direttamente da Studio, senza bisogno di browser esterni.

### Esportazione del tuo Tema

Dopo aver creato o modificato un tema, puoi esportarlo come file `.atp` per condividerlo con altri. Troverai l'opzione di esportazione nella schermata di modifica.

## Regole avanzate e Punteggiatura fonetica

Le regole per Earcons e Speech consentono a NVDA di riprodurre earcons (icone acustiche) e altri effetti vocali, come i cambiamenti di prosodia.

### Utilizzo
1. Assicurati che il componente aggiuntivo sia abilitato. Premi NVDA+Alt+P per attivarlo/disattivarlo.
2. Le regole possono essere configurate tramite una finestra di dialogo nel menu delle preferenze di NVDA.
3. Per impostazione predefinita, avrai un set di regole audio predefinite.
4. Le regole vengono salvate in un file denominato `earconsAndSpeechRules.json` nella directory di configurazione utente di NVDA.

### Verbosità dello stato (State Verbosity)
Il componente aggiuntivo include una funzione che ti consente di silenziare e nascondere il parlato o i suoni per gli stati che potrebbero causare fastidio costante (ad esempio, gli stati "espanso" o "non selezionato").
Per utilizzare questa funzione:
1. Vai alle impostazioni delle Regole vocali e modifica lo stato che desideri silenziare.
2. Seleziona l'opzione denominata **"Sopprimi disordine di stato" (Suppress state clutter)**.
3. Ora puoi usare la scorciatoia rapida per cambiare il livello di verbosità ogni volta che lo desideri.
* Puoi attivare/disattivare questa opzione tramite la scorciatoia del livello **(NVDA+Maiusc+A poi s)** o tramite la scorciatoia diretta **(NVDA+Alt+[)**.
* Quando riduci la verbosità, qualsiasi stato per cui hai abilitato questa opzione verrà silenziato. Quando aumenti di nuovo la verbosità, il componente aggiuntivo tornerà a leggere normalmente tutti gli stati.

## Funzionalità avanzate e Segreti

In questo componente aggiuntivo sono integrate una serie di funzionalità altamente avanzate che potrebbero non essere evidenti a prima vista:

### 1. Livello di Navigazione
- **Scorciatoia:** `NVDA+Win+N`
- **Descrizione:** Una volta entrato in questo livello (layer), non hai più bisogno di tenere premuto `Alt`, `Maiusc` o qualsiasi tasto modificatore per navigare. Puoi usare solo i tasti freccia!
- **Come si usa:**
  - Usa le Frecce Sinistra/Destra per scorrere tra **27 diverse modalità di navigazione** (Carattere, Parola, Riga, Frase, Paragrafo, Intestazione, Link, Pulsante, Campo di modifica, Tabella, ecc.).
  - Usa le Frecce Su/Giù per saltare all'elemento precedente/successivo in base alla modalità corrente.
  - Premi `C` per copiare l'elemento corrente negli appunti.
  - Premi `S` per sillabare l'elemento corrente.
  - Premi `R` per leggere tutto partendo dall'elemento corrente.
  - Premi `Esc` per uscire dal livello.

### 2. Sonar Audio
- **Scorciatoia:** `NVDA+Alt+R` (o `NVDA+Maiusc+A` poi `r`)
- **Descrizione:** Una funzione incredibile che analizza l'intera finestra attiva, raccoglie tutti i controlli al suo interno (pulsanti, elenchi, testi) e riproduce rapidamente i loro suoni associati da sinistra a destra nello spazio 3D. Questo ti dà una "immagine" sonora del layout della finestra e di quanto è popolata!

### 3. Segnale Audio (Beacon)
- **Scorciatoia:** `NVDA+Maiusc+B` (o `NVDA+Maiusc+A` poi `a`)
- **Descrizione:** Puoi "rilasciare" un segnale audio (beacon) nella posizione corrente dell'oggetto navigatore. Questo è utile per marcare un oggetto e seguirlo contestualmente durante un'analisi del Sonar Audio.

### 4. Livello di Comando Temi Audio
- **Scorciatoia:** `NVDA+Maiusc+A`
- **Descrizione:** Invece di memorizzare dozzine di scorciatoie, entra in questo livello e premi un solo tasto per eseguire un comando:
  - `t` : Attiva/disattiva i temi audio.
  - `p` : Attiva/disattiva regole vocali e Earcons.
  - `n` e `b` : Tema successivo/precedente.
  - `Freccia Su` e `Freccia Giù` : Aumenta/diminuisci il volume del tema.
  - `s` : Attiva/disattiva verbosità di stato.
  - `o` : Scorri rapidamente l'ordine di pronuncia (es. Nome poi Ruolo, o Ruolo poi Nome).
  - `c` : Pronuncia il livello di intestazione corrente.
  - `y` : Scorri i temi.
  - `i` : Scorri i suoni di digitazione.
  - `u` : Attiva/disattiva i suoni di digitazione.
  - `h` : Aiuto.

### 5. Segnalazione Oggetti 3D
- **Scorciatoia:** `NVDA+Tab`
- **Descrizione:** Riporta l'oggetto corrente sotto il cursore, ma mappa perfettamente le sue coordinate audio spaziali 3D in modo che tu possa sentire la sua esatta posizione fisica sullo schermo rispetto al centro.

### 6. Integrazione nel vassoio di sistema (System Tray)
- **Descrizione:** Il componente aggiuntivo inietta opzioni di accesso rapido direttamente nel menu della barra delle applicazioni di NVDA (System Tray). Puoi fare clic con il pulsante destro del mouse sull'icona di NVDA accanto all'orologio sulla barra delle applicazioni per accedere istantaneamente ad "Audio Themes Studio" o per attivare/disattivare i temi senza dover aprire la finestra di dialogo completa delle preferenze.

### 7. Suoni di Stato del Sistema (System Status Sounds)
- **Descrizione:** Riproduce segnali audio per eventi a livello di sistema come connessione/disconnessione di dispositivi USB, variazioni di alimentazione CA, stato della batteria, connettività di rete e sospensione/riattivazione del sistema. Tutti gli eventi sono monitorati tramite notifiche native di Windows (nessun polling).
- **Eventi:**
  - **Alimentazione CA collegata/scollegata:** Riproduce un suono quando colleghi o scolleghi il cavo di alimentazione del portatile.
  - **Batteria scarica/critica/carica:** Riproduce avvisi basati su soglie quando il livello della batteria scende sotto percentuali configurabili o quando è completamente carica.
  - **Dispositivo USB collegato/scollegato:** Rileva qualsiasi connessione o rimozione di un dispositivo USB (tastiere, mouse, chiavette USB, ecc.).
  - **Montaggio/Smontaggio volume di archiviazione:** Rileva l'assegnazione di lettere di unità per chiavette USB, dischi rigidi esterni e schede SD.
  - **Rete connessa/disconnessa:** Controlla lo stato della connettività a intervalli configurabili e riproduce un suono ai cambiamenti di stato.
  - **Riattivazione/sospensione del sistema:** Riproduce suoni quando il computer si riprende dalla modalità di sospensione o vi entra.
- **Suoni personalizzati:** Posiziona i file `.wav` nella cartella del tuo tema con questi nomi:
  `sys_ac_plug.wav`, `sys_ac_unplug.wav`, `sys_battery_low.wav`, `sys_battery_critical.wav`, `sys_battery_full.wav`, `sys_usb_plug.wav`, `sys_usb_unplug.wav`, `sys_volume_plug.wav`, `sys_volume_unplug.wav`, `sys_network_connect.wav`, `sys_network_disconnect.wav`, `sys_wake.wav`, `sys_sleep.wav`
- **Configurazione:** Apri Impostazioni NVDA -> Temi Audio Avanzati -> scheda "Stato del Sistema" per abilitare/disabilitare i singoli eventi, regolare il volume e impostare le soglie della batteria.

## Scorciatoie da tastiera

| Tasto | Azione |
| --- | ------ |
| **NVDA+Alt+N** | Attiva/disattiva i temi audio. Premi due volte in rapida successione per attivare/disattivare i suoni di digitazione. |
| **NVDA+Alt+T** | Scorri i temi audio disponibili. |
| **NVDA+Alt+Y** | Scorri i pacchetti di suoni di digitazione disponibili. |
| **NVDA+Alt+K** | Attiva/disattiva i suoni di digitazione. |
| **NVDA+Alt+R** | Sonar audio: analizza la finestra attiva per creare una mappa audio dei suoi elementi. |
| **NVDA+Maiusc+B** | Rilascia/rimuove un segnale audio in corrispondenza dell'oggetto navigatore corrente. |
| **NVDA+Maiusc+A** | Accedi al livello dei comandi dei temi audio (premi questo, poi: h per aiuto, t per alternare, p per regole, n/b per tema successivo/precedente, frecce su/giù per il volume, y/i/u per scorrere/alternare temi/digitazione, a/r per segnale/sonar, s per verbosità, c per intestazione, o per ordine di lettura). |
| **NVDA+Alt+P** | Attiva/disattiva il componente aggiuntivo earcons e regole vocali. |
| **NVDA+Alt+[** | Attiva o disattiva la modalità concisa di segnalazione dello stato (verbosità dello stato). |
| **NVDA+H** | Pronuncia il livello di intestazione corrente. |
| **NVDA+Tab** | Riporta l'oggetto sotto il cursore con coordinate audio 3D complete. |
| **NVDA+Alt+S** | Pronuncia la frase corrente (SentenceNav). |
| **Alt+Frecce** | Navigazione avanzata per frasi. |
| **Alt+Win+Frecce** | Navigazione avanzata per proposizioni. |
| **Alt+Maiusc+Frecce** | Navigazione avanzata per paragrafi. |
| **NVDA+Alt+Frecce** | Navigazione web avanzata (BrowserNav). |
| **NVDA+Win+N** | Attiva il livello di navigazione (navigazione veloce senza modificatori). |

## Compatibility & Requirements
- **NVDA Version:** Requires NVDA 2024.1.0 or later.
- **Last Tested NVDA Version:** 2026.2.0
- **Operating System:** Windows 10 or Windows 11.

## Source Code & Repository
You can view the source code, report issues, or contribute to the project on GitHub:
[Advanced Audio Themes Repository](https://github.com/HassanAlBarshoumy/advanced_audio_themes)

## Change Log

### Version 9.33
- **Motore Emoji:** Nuovo motore di elaborazione emoji per migliorare la pronuncia e la gestione degli emoji.
- **Annunci Appunti:** Segnali audio durante le operazioni di copia, taglio e incollaggio.
- **Nuovo Tema:** Tema audio futuristico HAS Future Sound incluso di serie.
- **Correzione ZIP:** Risolto un problema con l'importazione dei temi in formato ZIP.
- **Rafforzamento stato sistema:** Migliorata la stabilità dei suoni di stato del sistema.
- **Prestazioni:** Miglioramenti generali delle prestazioni e ottimizzazione del motore audio.
- **Gesti di input:** Nuovi gesti di input e miglioramenti nell'assegnazione delle scorciatoie da tastiera.

### Version 9.32
- **Suoni di stato del sistema: Added a completely new module to monitor and play sounds for system-level events (USB plug/unplug, AC power changes, battery status, network connectivity, and system wake/sleep) using native Windows notifications for zero lag.
- **Audio DSP Enhancements:** Completely rewrote the Bass Boost (Low-shelf filter) and Noise Gate algorithms to support correct attack/release times and improved sound quality. Added a full UI in the settings panel to control these DSP effects.
- **3D Spatial Audio Fixes:** Resolved an issue causing lag in 3D audio playback for progress bars.

### Version 9.30 - 9.31
- **Universal First/Last Item Detection:** Added support for first/last item detection for *all* NVDA roles, instead of just lists and menus.
- **Advanced Detection Modes:** Introduced 3 detection modes (smart, strict, any_sibling) with multi-hop traversal to guarantee accurate detection of the first and last elements even in complex web layouts.

### Version 9.27 - 9.28
- **Role vs State Sounds Priority:** Fixed an issue where state sounds (like "checked") were wrongly suppressing role sounds (like "checkbox").
- **Fallback Behaviors:** Added custom fallback settings for first/last item sounds, allowing users to select custom sounds or bypass missing roles.
- **Heading Support:** Added support for Heading levels 7, 8, and 9.

### Version 9.23 - 9.26
- **Sentence Navigation Fixes:** Fixed a bug causing NVDA to endlessly repeat sentences when reading Arabic text in VirtualBuffers.
- **NVDA 2026.2 Compatibility:** Migrated to the new `NVDAHelper.localLib.generateBeep` API to resolve deprecation warnings and ensure stability on future NVDA versions.
- **Auto-Update Fix:** Resolved a critical freeze in NVDA during the auto-update download process.

## Novità

### Versione 9.33
- **Motore Emoji:** Nuovo motore di elaborazione emoji.
- **Annunci Appunti:** Segnali audio per le operazioni degli appunti.
- **Nuovo Tema:** HAS Future Sound incluso di serie.
- **Correzione ZIP:** Risolto problema di importazione temi ZIP.
- **Rafforzamento stato sistema:** Maggiore stabilità dello stato del sistema.
- **Prestazioni:** Ottimizzazione generale del motore audio.
- **Gesti di input:** Nuovi gesti di input.

### Versione 9.32
- **Suoni di stato del sistema:** Nuovo motore di monitoraggio per batteria, USB, rete e alimentazione.
- **Miglioramenti DSP:** Filtri Bass Boost e Noise Gate riscritti.
- **Audio 3D:** Risolti i ritardi nelle barre di avanzamento.

### Versione 9.30 - 9.31
- **Identificazione universale:** Rilevazione del primo/ultimo elemento per tutti i ruoli.

### Versione 9.27 - 9.28
- **Suoni di riserva:** Aggiunti suoni di riserva.
- **Intestazioni:** Supporto per intestazioni di livello 7, 8 e 9.

### Versione 9.23 - 9.26
- **Correzioni:** Correzione di bug nella navigazione e compatibilità con NVDA 2026.2.

## Traduttori
- **Spagnolo:** Hassan AlBarshoumy, Luis Carlos González Morales
- **Italiano:** Christian Cantelmi, Ciro Cantelmi
- **Russo:** Valentin Kupriyanov
- **Cinese:** Cary-rowen, Jerry
- **Tedesco:** René L

