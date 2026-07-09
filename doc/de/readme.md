# Erweiterte Audio-Themes (Advanced Audio Themes)

Dieses Add-on bietet ein immersives Audio-Erlebnis für Nutzer des NVDA-Screenreaders, indem es Klänge für verschiedene UI-Ereignisse abspielt. Es ermöglicht die Erstellung, Installation und Anpassung von Audio-Themes, was das akustische Feedback der Benutzeroberfläche verbessert.

## Funktionen

- **Audio-Effekte:** Spielt Töne für UI-Ereignisse ab, wie z.B. beim Fokussieren von Steuerelementen, Navigieren in Listen und mehr.
- **3D-Audio:** Nutzt Steam Audio, um positionsbezogenes 3D-Audio bereitzustellen, was ein Gefühl dafür vermittelt, wo sich die Steuerelemente auf dem Bildschirm befinden.
- **Fortschrittliche Audio-DSP:** Echtzeit-Audioverarbeitung einschließlich Bassverstärkung, Noise Gate (Rauschunterdrückung), Stille-Zuschnitt, intelligenter Lautstärkenormalisierung und weicher Hüllkurven (Smooth Envelopes).
- **Audio-Ducking:** Senkt automatisch die Theme-Lautstärke, wenn NVDA spricht, um die Sprachverständlichkeit zu gewährleisten.
- **Reverb (Hall):** Fügt den Tönen Hall-Effekte hinzu, um ein noch immersiveres Erlebnis zu schaffen.
- **Anpassbare Themes:** Ermöglicht Benutzern das Erstellen, Installieren und Wechseln zwischen verschiedenen Audio-Themes.
- **Audio Themes Studio V2:** Ein integriertes Werkzeug, um neue Audio-Themes zu erstellen oder bestehende direkt über das Mikrofon oder per Drag & Drop zu bearbeiten.
- **Erweiterte Audioformate:** Integrierte FFmpeg-Unterstützung für MP3, FLAC, OGG, M4A und mehr.
- **Erweiterte Tippgeräusche:** Simuliert physische Tastatureingaben mit räumlicher Audiopositionierung, dynamischer Lautstärkeanpassung nach Anschlagstärke und intelligenter Tastenbelegung für spezielle Tasten (Eingabe, Rücktaste, Leertaste, Umschalt, Strg, Alt).
- **Kontextbezogenes Tippen:** Option, um Tippgeräusche nur innerhalb bearbeitbarer Textfelder abzuspielen.
- **Intelligente Fortschrittsbalken:** Dynamische Tonhöhenverschiebung für Fortschrittsbalken (höhere Tonhöhe = höherer Prozentsatz).
- **Erkennung des ersten/letzten Elements:** Spielt einen spezifischen Anschlagton ab, wenn die Grenze einer Liste oder eines Menüs erreicht wird.
- **Audio-Bake / Sonar:** Platzieren Sie eine räumliche Audio-Bake an einer beliebigen Stelle auf dem Bildschirm und navigieren Sie herum, um Echtzeit-Sonar-Pings zu hören, die Sie relativ zur Bake führen.
- **Erweiterte Navigation:** Integrierte SentenceNav- und BrowserNav-Engines für nahtlose Text- und Webnavigation ohne Konflikte bei den Pfeiltasten.
- **Navigationsebene:** Drücken Sie NVDA+Win+N, um in einen schnellen Navigationsmodus zu wechseln, in dem Pfeiltasten nach Sätzen, Absätzen oder anderen Elementen navigieren, ohne dass Modifikatortasten gehalten werden müssen.
- **Cloud Theme Store:** Laden Sie von der Community erstellte Themes direkt aus dem Audio Themes Studio herunter, hören Sie sie vor und installieren Sie sie.
- **App-spezifische Profile:** Wechselt automatisch zu einem bestimmten Audio-Theme und Tippgeräusch-Paket basierend auf der aktiven Anwendung.

- **Systemstatus-Sounds:** Spielt Audiohinweise für Ereignisse auf Systemebene ab, z. B. Änderungen der Stromversorgung, Akkustatus, USB-Geräteverbindung und Netzwerkkonnektivität.
- **Emoji-Verbesserung:** Erweiterte Emoji-Unterstützung mit verbesserter Erkennung, Aussprache und akustischem Feedback für Emoji-Zeichen.
- **Zwischenablage-Benachrichtigungen:** Akustische Benachrichtigungen beim Kopieren, Ausschneiden und Einfügen von Inhalten über die Zwischenablage.

## Entwicklung & Credits

Die Entwicklung und Konsolidierung dieses Add-ons begann Anfang Mai (genauer gesagt am 3. Mai 2026) exklusiv durch **Hassan AlBarshoumy**.

Sämtliches Code-Refactoring, strukturelle Zusammenführungen und GUI-Integrationen (einschließlich des Audio Themes Studio V2 und der vereinheitlichten Einstellungsdialoge) wurden durchgeführt, um maximale Stabilität und Kompatibilität mit NVDA 2026.1+ zu gewährleisten.

**Hauptentwickler und Konsolidator:**
* Hassan AlBarshoumy

**Danksagungen:**
Dieses Add-on profitierte stark von der Zusammenführung und Entwicklung früherer Open-Source-Projekte in der NVDA-Community. Besonderer Dank geht an die ursprünglichen Entwickler:
* **Ahmed Sami:** Ursprünglicher Entwickler des navSounds (Navigation Sound Effects) Add-ons und für seine Beiträge.
* **Musharraf Omer:** Ursprünglicher Entwickler des Audio Themes 3D Add-ons.
* **Tony Malykh:** Ursprünglicher Entwickler der Add-ons Earcons and Speech Rules, BrowserNav, SentenceNav und TextNav.
* **Austin Hicks & Bryan Smart:** Ursprüngliche Entwickler des Unspoken Add-ons.

**Kontakt & Updates:** [https://t.me/HassanAlBarshoumy](https://t.me/HassanAlBarshoumy)

## Installation

1. Laden Sie die neueste Version des Add-ons über Hassans offiziellen Kanal herunter.
2. Öffnen Sie die heruntergeladene `.nvda-addon`-Datei.
3. NVDA wird Sie bitten, die Installation zu bestätigen. Wählen Sie "Ja".
4. Starten Sie NVDA neu, um die Installation abzuschließen.

## Verwendung

### Audio-Themes aktivieren/deaktivieren

Sie können die Audio-Themes-Funktion in den NVDA-Einstellungen aktivieren oder deaktivieren:

1. Öffnen Sie das NVDA-Menü (NVDA+N).
2. Gehen Sie zu "Optionen" -> "Einstellungen".
3. Wählen Sie im Einstellungsdialog die Kategorie "Audio-Themes".
4. Aktivieren oder deaktivieren Sie das Kontrollkästchen "Audio-Themes aktivieren".

### Themes auswählen und verwalten

- **Über ein Theme:** Klicken Sie auf die Schaltfläche "Über", um Informationen zum ausgewählten Theme anzuzeigen.

### Was ist neu

### Version 9.33
- **Emoji-Engine:** Neue Emoji-Verarbeitungs-Engine für verbesserte Erkennung und akustisches Feedback.
- **Zwischenablage-Benachrichtigungen:** Akustische Benachrichtigungen beim Kopieren, Ausschneiden und Einfügen.
- **Neues Theme HAS Future Sound:** Ein brandneues Audio-Theme mit futuristischen Klängen.
- **ZIP-Import-Fix:** Behebung eines Fehlers beim Importieren von Themes aus ZIP-Dateien.
- **Systemstatus-Härtung:** Verbesserte Stabilität und Zuverlässigkeit der Systemstatus-Überwachung.
- **Leistung:** Allgemeine Leistungsoptimierungen für schnellere Reaktionszeiten.
- **Eingabegesten:** Verbesserte Eingabegesten-Zuordnung und -Verwaltung.

### Version 9.32
- **Systemstatus-Töne:** Einführung einer umfassenden Systemüberwachung für Akku, USB, Netzwerk und Stromversorgung.
- **DSP-Verbesserungen:** Komplett überarbeitete Bass Boost- und Noise Gate-Filter.
- **3D-Audio:** Behebung von Verzögerungen bei Fortschrittsbalken.

### Version 9.30 - 9.31
- **Erstes/Letztes Element:** Universelle Erkennung für erstes/letztes Element.

### Version 9.27 - 9.28
- **Fallback-Töne:** Fallback-Töne hinzugefügt.
- **Überschriften:** Unterstützung für Überschriftenebenen 7, 8 und 9.

### Version 9.23 - 9.26
- **Fehlerbehebungen:** Fehler bei Satznavigation und NVDA 2026.2-Kompatibilität behoben.

## Übersicht der Einstellungs-Tabs

Das Einstellungsfeld "Erweiterte Audio-Themes" enthält mehrere Reiter (Tabs), um jeden Aspekt des Audioerlebnisses anzupassen. Im Folgenden finden Sie einen tiefen Einblick in jede verfügbare Option:

#### 1. Reiter "Allgemein"
- **Audio-Themes aktivieren:** Hauptschalter zum Ein- oder Ausschalten der Audio-Themes-Engine.
- **Theme auswählen:** Dropdown-Menü zur Auswahl des aktiven Audio-Themes aus den installierten Themes.
- **Über / Entfernen / Neu hinzufügen:** Verwalten Sie Ihre Themes. Sie können neue Themes aus `.atp`- oder `.zip`-Dateien installieren.
- **Theme Store:** Öffnet den integrierten Store zum Herunterladen von der Community erstellter Themes.
- **Theme Studio:** Öffnet das Studio, um das aktuell ausgewählte Theme zu bearbeiten oder neu zu mischen.
- **Vorschau:** Spielt eine Sequenz von Beispielklängen des aktiven Themes ab.
- **Töne im 3D-Modus abspielen:** Aktiviert die räumliche Audioverarbeitung.
- **Rollen ansagen:** Umschalten, ob NVDA Steuerelementrollen (wie "Schaltfläche", "Link") anspricht.
- **Rollen beim fortlaufenden Lesen ansagen:** Schaltet die Rollenansage beim fortlaufenden Lesen ein oder aus. Mit der Schaltfläche "Rollen auswählen..." können Sie genau festlegen, welche Rollen angesagt werden sollen.
- **Lautstärke des Sprachausgabegeräts verwenden:** Verknüpft die Theme-Lautstärke mit der NVDA-Stimmenlautstärke. Deaktivieren Sie dies, um den manuellen Schieberegler zu verwenden.
- **Audio-Ducking:** Senkt die Lautstärke des Hintergrund-Audios, wenn NVDA spricht. Sie können wählen, welche Klangkategorien abgedämpft werden sollen und den Prozentsatz der abgedämpften Lautstärke festlegen.
- **Ersatzverhalten (Fallback):** Legen Sie fest, was passiert, wenn ein Ton für eine bestimmte Rolle oder ein erstes/letztes Element fehlt (z. B. Stille abspielen, einen benutzerdefinierten Ton abspielen oder den ersten verfügbaren Ton abspielen).
- **Status-Töne unterdrücken den Rollenton:** Wenn ein Element einen Status-Ton hat (z.B. aktiviertes Kontrollkästchen), wird verhindert, dass der Rollenton abgespielt wird, um akustische Überladung zu vermeiden.
- **Anwendungs-Sperrliste (Blacklist):** Eine kommagetrennte Liste ausführbarer Anwendungsdateien, bei denen Audio-Themes vollständig deaktiviert werden sollen. Sie können auch anpassen, welche spezifischen Klangkategorien in diesen Apps unterdrückt werden.
- **Tipp-Sounds:** Aktivieren Sie Schreibmaschinen- oder mechanische Tastaturgeräusche. Zu den Optionen gehören räumliches Tippen, intelligente räumliche Zuordnung, Beschränkung der Töne auf Eingabefelder, Auswahl von Soundpaketen und Lautstärkeanpassung.
- **Konfigurationsmanagement:** Suchen Sie nach Updates, schließen Sie Beta-Versionen ein und Exportieren/Importieren Sie Ihre gesamte Konfiguration in eine einzige `.atcfg`-Datei.

#### 2. Reiter "Audio-Engine"
- **Intelligente Lautstärkenormalisierung:** Passt leise und laute Töne dynamisch an ein konstantes Niveau an.
- **Weiche Hüllkurve:** Wendet Mikro-Fade-Ins und Fade-Outs an, um Audio-Knacksen oder -Klicken zu verhindern.
- **Weiches 3D-Panning:** Erzeugt einen Gleiteffekt, wenn sich Objekte über den Bildschirm bewegen, anstatt sofort zu springen.
- **RAM-Caching:** Lädt Töne für eine latenzfreie Wiedergabe in den Arbeitsspeicher.
- **Stille zuschneiden:** Entfernt automatisch stille Pausen am Anfang und Ende von Audiodateien basierend auf einem anpassbaren Schwellenwert.
- **Noise Gate (Rauschunterdrückung):** Beseitigt geringfügiges Hintergrundrauschen aus schlecht aufgenommenen Audio-Themes. Beinhaltet Schieberegler für Schwellenwert, Attack und Release.
- **Bassverstärkung:** Verstärkt tiefe Frequenzen, um Klängen mehr Durchschlagskraft zu verleihen. Beinhaltet Schieberegler für Verstärkung (Gain) und Grenzfrequenz (Cutoff).
- **Audio-Ausgabemodus:** Wechseln Sie zwischen vollem 3D-Raumklang (Stereo) und zentriertem (Mono) Audio.
- **Räumliches Audio für Fortschrittsbalken:** Wählen Sie, ob Fortschrittsbalken basierend auf ihrem Fortschrittsprozentsatz oder ihrer physischen Position auf dem Bildschirm von links nach rechts schwenken. Enthält auch einen Schalter, um die Tonhöhe mit zunehmendem Fortschritt zu erhöhen.

#### 3. Reiter "Reverb (Hall)"
Simuliert Umgebungsakustik, damit Klänge wirken, als würden sie in einem physischen Raum abgespielt.
- **Reverb aktivieren:** Hauptschalter für Umgebungseffekte.
- **Raumgröße:** Passt die wahrgenommene Größe des virtuellen Raums an.
- **Dämpfung (Damping):** Steuert, wie schnell hohe Frequenzen absorbiert werden.
- **Wet Level / Dry Level:** Balanciert die Menge an verarbeitetem Hall im Vergleich zum originalen sauberen Klang.
- **Breite (Width):** Passt die Stereobreite des Hallfahne an.

#### 4. Reiter "Audioformate"
- **FFmpeg verwenden:** Aktiviert die Unterstützung für komprimierte Audioformate wie MP3, FLAC, M4A und OGG.
- **FFmpeg-Status:** Zeigt an, ob FFmpeg installiert ist. Falls nicht, steht eine Schaltfläche zum automatischen Herunterladen und Extrahieren zur Verfügung (~12MB).

#### 5. Reiter "Earcons & Sprachregeln"
Eine leistungsstarke Regel-Engine für phonetische Aussprache und benutzerdefinierte Status-Töne.
- **Regel-Liste:** Zeigt alle aktiven Regeln, gefiltert nach Kategorie (Rolle, Status, Text, Zeichen usw.) an.
- **Regel-Editor:** Beim Hinzufügen oder Bearbeiten einer Regel können Sie definieren:
  - **Muster / Wert:** Das Regex-Muster, die Rolle oder der Status, der übereinstimmen soll.
  - **Aktionstyp:** Wählen Sie aus, ob ein integriertes Wave, eine benutzerdefinierte WAV-Datei, ein Signalton, eine Prosodie-Anpassung (Tonhöhe/Geschwindigkeit), Textersetzung abgespielt oder nichts unternommen werden soll.
  - **Sprachaktion:** Entscheiden Sie, ob NVDA den Originaltext beibehalten, den gesprochenen Text bearbeiten oder vollständig verstummen soll, wenn die Regel zutrifft.
  - **Audioanpassungen:** Lautstärkeregler, Start-/End-Trimm-Offsets (in Millisekunden), Tonhöhe/Dauer für Signaltöne.
  - **Filter:** Beschränken Sie die Regel auf bestimmte Anwendungen, Fenstertitel oder Website-URLs (Regex unterstützt).
- **Stapelverarbeitung:** Regel-Wörterbücher exportieren/importieren, alle Regeln aktivieren/deaktivieren oder Regeln direkt über die Benutzeroberfläche testen.

#### 6. Reiter "Sonstiges"
Erweiterte Konfiguration für Navigationsmodule.
- **Satznavigation (Alt+Pfeiltasten):** Lautstärke für Absatzgrenzen-Signale anpassen, Formatierungsansagen umschalten, Wikipedia-Referenz-Überspringen konfigurieren, Satzrekonstruktion über Absätze hinweg anpassen und benutzerdefinierte Satz-/Phrasen-Trennzeichen definieren.
- **Textnavigation (Alt+Umschalt+Pfeiltasten):** Knisterlautstärke anpassen und das Verhalten der Signaltöne am Textende konfigurieren.
- **Erweiterte Browser-Navigation (BrowserNav):** Lautstärke von Knistern und Piepen während der QuickSearch-Navigation anpassen und Lautstärke für das Überspringen von unübersichtlichen Bereichen (Skip Clutter) einstellen.
- **Navigationsebene (NVDA+Windows+N):** Auto-Exit-Timeouts konfigurieren, Töne für Ebenenaktionen, durchzureichende Tasten (Pass-through) und bestimmte Navigationsmodi ein- oder ausschalten.

#### 7. Reiter "Sprachreihenfolge"
- **Globale Ansageformat:** Ändern Sie global, wie NVDA Elemente vorliest (z.B. Standard: Name -> Rolle -> Status oder Status -> Rolle -> Name).
- **Rollen-spezifische Anpassung:** Verwenden Sie das Suchfeld, um bestimmte Rollen (wie Kontrollkästchen oder Link) zu finden und ihnen ein individuelles Ansageformat zuzuweisen.

#### 8. Reiter "App-Profile"
- Wechseln Sie Audioerlebnisse automatisch basierend auf der aktiven Anwendung.
- **Profil hinzufügen:** Geben Sie eine ausführbare Anwendungsdatei ein (z. B. `chrome.exe`) und weisen Sie ein spezifisches Audio-Theme und/oder Tippgeräusch-Paket zu, das sofort aktiviert wird, wenn Sie zu dieser App wechseln.

#### 9. Reiter "QuickSearch & Lesezeichen"
- Verwalten Sie domänenspezifische Navigationsregeln für das Webbrowsing.
- Weisen Sie Tasten (wie J oder K) zu, um schnell zu bestimmten Elementen zu springen (QuickJump), unübersichtliche Menüs automatisch zu überspringen (SkipClutter) oder benutzerdefinierte Python-Skripte auf bestimmten Websites auszuführen.

#### 10. Reiter "Erstes/Letztes Element"
- **Erkennung des ersten/letzten Elements aktivieren:** Spielt einen einzigartigen Anschlagton ab, wenn Sie den Anfang oder das Ende einer Liste, eines Menüs oder einer Baumansicht erreichen.
- **Erkennungsbereich:** Wenden Sie dies universell auf alle Rollen an oder selektiv auf bestimmte Rollen (mithilfe der Schaltfläche "Rollen auswählen").
- **Verhalten bei einzelnen Elementen:** Entscheiden Sie, ob Elemente, die das einzige in einer Liste sind, als erstes Element, letztes Element oder gar nicht behandelt werden sollen.

#### 12. Zwischenablage-Registerkarte
- **Zwischenablage-Benachrichtigungen aktivieren:** Hauptschalter zum Ein- oder Ausschalten der akustischen Rückmeldungen bei Zwischenablage-Operationen.
- **Ereignisse:** Individuelle Steuerung der Töne für Kopieren, Ausschneiden und Einfügen.
- **Lautstärke:** Anpassung der Lautstärke für Zwischenablage-Benachrichtigungen.

#### 13. Emoji-Registerkarte
- **Emoji-Verbesserung aktivieren:** Hauptschalter zum Ein- oder Ausschalten der erweiterten Emoji-Unterstützung.
- **Akustisches Feedback:** Konfiguration der Töne, die beim Erkennen von Emoji-Zeichen abgespielt werden.
- **Aussprache:** Einstellungen zur verbesserten Aussprache und Beschreibung von Emojis.

### Verwendung des Audio Themes Studio V2

Mit dem Audio Themes Studio können Sie Audio-Themes erstellen und bearbeiten. So öffnen Sie das Studio:

1. Öffnen Sie das NVDA-Menü (NVDA+N).
2. Wählen Sie "Audio Themes Studio".

Im Studio können Sie Folgendes tun:

- **Ein neues Audio-Theme erstellen:** Dies führt Sie durch den Prozess der Erstellung eines neuen Themes von Grund auf.
- **Ein bestehendes Audio-Theme anpassen:** Wählen Sie diese Option, um die Klänge eines installierten Themes zu ändern.
- **Vom Mikrofon aufnehmen:** Sie können nun nativ Ihre Stimme oder jedes beliebige Geräusch direkt von Ihrem Mikrofon aufnehmen, um es einem UI-Ereignis zuzuweisen!
- **Drag & Drop:** Sie können Audiodateien direkt in das Studio-Fenster ziehen, um sie schnell zuzuweisen.
- **Cloud Theme Store:** Durchsuchen, hören Sie vor und laden Sie von der Community erstellte Themes direkt im Studio herunter, ohne externe Browser zu benötigen.

### Theme exportieren

Nach dem Erstellen oder Bearbeiten eines Themes können Sie es als `.atp`-Datei exportieren, um es mit anderen zu teilen. Die Exportoption finden Sie im Bearbeitungsbildschirm.

## Erweiterte Regeln & Phonetische Interpunktion

Earcons und Sprachregeln ermöglichen es NVDA, Earcons (Ohrsymbole) sowie andere Spracheffekte wie Prosodie-Änderungen abzuspielen.

### Verwendung
1. Stellen Sie sicher, dass das Add-on aktiviert ist. Drücken Sie NVDA+Alt+P, um es umzuschalten.
2. Regeln können über ein Dialogfeld im NVDA-Einstellungsmenü konfiguriert werden.
3. Standardmäßig verfügen Sie über eine Reihe vordefinierter Audio-Regeln.
4. Die Regeln werden in einer Datei namens `earconsAndSpeechRules.json` in Ihrem NVDA-Benutzerkonfigurationsverzeichnis gespeichert.

### Status-Ausführlichkeit (Verbosity)
Das Add-on enthält eine Funktion, mit der Sie die Sprache oder Klänge für Statusmeldungen stummschalten und ausblenden können, die ständige Belästigung verursachen könnten (z. B. die Statusmeldungen "erweitert" oder "nicht ausgewählt").
Um diese Funktion zu nutzen:
1. Gehen Sie zu den Sprachregel-Einstellungen und bearbeiten Sie den Status, den Sie stummschalten möchten.
2. Aktivieren Sie die Option **"Status-Unübersichtlichkeit unterdrücken" (Suppress state clutter)**.
3. Jetzt können Sie die schnelle Tastenkombination verwenden, um die Ausführlichkeitsstufe jederzeit umzuschalten.
* Sie können diese Option entweder über die Ebenen-Verknüpfung **(NVDA+Umschalt+A dann s)** oder über die direkte Verknüpfung **(NVDA+Alt+[)** umschalten.
* Wenn Sie die Ausführlichkeit reduzieren, wird jeder Status, für den Sie diese Option aktiviert haben, stummgeschaltet. Wenn Sie die Ausführlichkeit wieder erhöhen, kehrt das Add-on zum normalen Vorlesen aller Statusmeldungen zurück.

## Erweiterte Funktionen & Geheimnisse

In dieses Add-on ist eine Reihe hochgradig erweiterter Funktionen integriert, die auf den ersten Blick möglicherweise nicht offensichtlich sind:

### 1. Navigationsebene
- **Verknüpfung:** `NVDA+Win+N`
- **Beschreibung:** Sobald Sie diese Ebene betreten, müssen Sie `Alt`, `Umschalt` oder andere Modifikatortasten nicht mehr gedrückt halten, um zu navigieren. Sie können einfach die Pfeiltasten verwenden!
- **Verwendung:**
  - Verwenden Sie den Links-/Rechtspfeil, um durch **27 verschiedene Navigationsmodi** zu blättern (Zeichen, Wort, Zeile, Satz, Absatz, Überschrift, Link, Schaltfläche, Eingabefeld, Tabelle usw.).
  - Verwenden Sie den Auf-/Abwärtspfeil, um zum vorherigen/nächsten Element basierend auf dem aktuellen Modus zu springen.
  - Drücken Sie `C`, um das aktuelle Element in die Zwischenablage zu kopieren.
  - Drücken Sie `S`, um das aktuelle Element zu buchstabieren.
  - Drücken Sie `R`, um beginnend beim aktuellen Element alles vorzulesen.
  - Drücken Sie `Escape`, um die Ebene zu verlassen.

### 2. Audio-Sonar
- **Verknüpfung:** `NVDA+Alt+R` (oder `NVDA+Umschalt+A` dann `r`)
- **Beschreibung:** Eine unglaubliche Funktion, die das gesamte aktive Fenster abtastet, alle darin enthaltenen Steuerelemente (Schaltflächen, Listen, Texte) sammelt und ihre zugehörigen Klänge schnell von links nach rechts im 3D-Raum abspielt. Dies gibt Ihnen ein klangliches "Bild" vom Layout des Fensters und davon, wie stark es gefüllt ist!

### 3. Audio-Bake (Beacon)
- **Verknüpfung:** `NVDA+Umschalt+B` (oder `NVDA+Umschalt+A` dann `a`)
- **Beschreibung:** Sie können eine Audio-Bake an der Position des aktuellen Navigator-Objekts "abwerfen". Dies ist nützlich, um ein Objekt zu markieren und es während eines Audio-Sonar-Durchlaufs kontextuell zu verfolgen.

### 4. Befehlsebene für Audio-Themes
- **Verknüpfung:** `NVDA+Umschalt+A`
- **Beschreibung:** Anstatt Dutzende von Verknüpfungen auswendig zu lernen, betreten Sie diese Ebene und drücken Sie eine einzelne Taste, um einen Befehl auszuführen:
  - `t` : Audio-Themes ein-/ausschalten.
  - `p` : Earcons & Sprachregeln umschalten.
  - `n` und `b` : Nächstes/Vorheriges Theme.
  - `Aufwärtspfeil` und `Abwärtspfeil` : Theme-Lautstärke erhöhen/verringern.
  - `s` : Status-Ausführlichkeit umschalten.
  - `o` : Sprachreihenfolge schnell durchschalten (z.B. Name dann Rolle oder Rolle dann Name).
  - `c` : Aktuelle Überschriftenebene ansagen.
  - `y` : Durch Themes blättern.
  - `i` : Durch Tippgeräusche blättern.
  - `u` : Tippgeräusche umschalten.
  - `h` : Hilfe.

### 5. 3D-Objektberichterstellung
- **Verknüpfung:** `NVDA+Tab`
- **Beschreibung:** Meldet das aktuelle Objekt unter dem Cursor, ordnet aber seine räumlichen 3D-Audiokoordinaten perfekt zu, sodass Sie seine genaue physische Position auf Ihrem Bildschirm relativ zum Zentrum hören können.

### 6. System-Tray-Integration
- **Beschreibung:** Das Add-on fügt Schnellzugriffsoptionen direkt in das NVDA-System-Tray-Menü ein. Sie können mit der rechten Maustaste auf das NVDA-Symbol neben der Uhr in Ihrer Taskleiste klicken, um sofort auf das "Audio Themes Studio" zuzugreifen oder die Themes ein- und auszuschalten, ohne den vollständigen Einstellungsdialog öffnen zu müssen.

### 7. Systemstatus-Sounds
- **Beschreibung:** Spielt Audiohinweise für Ereignisse auf Systemebene ab, z. B. USB-Geräte anschließen/entfernen, Änderungen der Stromversorgung, Akkustatus, Netzwerkkonnektivität und Systemruhezustand/-aufwachen. Alle Ereignisse werden durch native Windows-Benachrichtigungen überwacht (kein Polling).
- **Ereignisse:**
  - **Netzstrom angeschlossen/getrennt:** Spielt einen Ton ab, wenn Sie das Stromkabel Ihres Laptops anschließen oder abziehen.
  - **Akku niedrig/kritisch/voll:** Spielt schwellenwertbasierte Warnungen ab, wenn der Akkustand unter konfigurierbare Prozentsätze fällt oder wenn er vollständig aufgeladen ist.
  - **USB-Gerät angeschlossen/getrennt:** Erkennt jede Verbindung oder Entfernung eines USB-Geräts (Tastaturen, Mäuse, Flash-Laufwerke usw.).
  - **Speichervolumen bereitgestellt/ausgeworfen:** Erkennt die Zuweisung von Laufwerksbuchstaben für Flash-Laufwerke, externe Festplatten und SD-Karten.
  - **Netzwerk verbunden/getrennt:** Überprüft den Verbindungsstatus in konfigurierbaren Intervallen und spielt bei Statusänderungen einen Ton ab.
  - **System aufwachen/Ruhezustand:** Spielt Töne ab, wenn der Computer aus dem Ruhezustand zurückkehrt oder in diesen wechselt.
- **Benutzerdefinierte Sounds:** Platzieren Sie `.wav`-Dateien mit diesen Namen in Ihrem Theme-Ordner:
  `sys_ac_plug.wav`, `sys_ac_unplug.wav`, `sys_battery_low.wav`, `sys_battery_critical.wav`, `sys_battery_full.wav`, `sys_usb_plug.wav`, `sys_usb_unplug.wav`, `sys_volume_plug.wav`, `sys_volume_unplug.wav`, `sys_network_connect.wav`, `sys_network_disconnect.wav`, `sys_wake.wav`, `sys_sleep.wav`
- **Konfiguration:** Öffnen Sie NVDA-Einstellungen -> Erweiterte Audio-Themes -> Registerkarte "Systemstatus", um einzelne Ereignisse zu aktivieren/deaktivieren, die Lautstärke anzupassen und Akkuschwellenwerte festzulegen.

## Tastenkombinationen

| Taste | Aktion |
| --- | ------ |
| **NVDA+Alt+N** | Audio-Themes ein-/ausschalten. Zweimal schnell drücken, um Tippgeräusche umzuschalten. |
| **NVDA+Alt+T** | Durch verfügbare Audio-Themes blättern. |
| **NVDA+Alt+Y** | Durch verfügbare Tipp-Soundpakete blättern. |
| **NVDA+Alt+K** | Tippgeräusche ein-/ausschalten. |
| **NVDA+Alt+R** | Audio-Sonar: Tastet das aktive Fenster ab, um eine Audio-Karte seiner Elemente zu erstellen. |
| **NVDA+Umschalt+B** | Audio-Bake am aktuellen Navigator-Objekt ablegen/entfernen. |
| **NVDA+Umschalt+A** | Befehlsebene für Audio-Themes betreten (dies drücken, dann: h für Hilfe, t zum Umschalten, p für Regeln, n/b für nächstes/vorheriges Theme, Auf-/Abwärtspfeile für Lautstärke, y/i/u zum Blättern/Umschalten von Themes/Tippen, a/r für Bake/Sonar, s für Ausführlichkeit, c für Überschrift, o für Reihenfolge). |
| **NVDA+Alt+P** | Add-on Earcons und Sprachregeln umschalten. |
| **NVDA+Alt+[** | Präzisen Status-Berichtsmodus umschalten (Status-Ausführlichkeit). |
| **NVDA+H** | Aktuelle Überschriftenebene ansagen. |
| **NVDA+Tab** | Das Objekt unter dem Cursor mit vollständigen 3D-Audiokoordinaten melden. |
| **NVDA+Alt+S** | Aktuellen Satz ansagen (SentenceNav). |
| **Alt+Pfeiltasten** | Erweiterte Satznavigation. |
| **Alt+Win+Pfeiltasten** | Erweiterte Phrasennavigation. |
| **Alt+Umschalt+Pfeiltasten** | Erweiterte Absatznavigation. |
| **NVDA+Alt+Pfeiltasten** | Erweiterte Webnavigation (BrowserNav). |
| **NVDA+Win+N** | Navigationsebene umschalten (schnelle Navigation ohne Modifikatoren). |

## Compatibility & Requirements
- **NVDA Version:** Requires NVDA 2024.1.0 or later.
- **Last Tested NVDA Version:** 2026.2.0
- **Operating System:** Windows 10 or Windows 11.

## Source Code & Repository
You can view the source code, report issues, or contribute to the project on GitHub:
[Advanced Audio Themes Repository](https://github.com/HassanAlBarshoumy/advanced_audio_themes)

## Change Log

### Version 9.33
- **Emoji-Engine:** Neue Emoji-Verarbeitungs-Engine für verbesserte Erkennung und akustisches Feedback.
- **Zwischenablage-Benachrichtigungen:** Akustische Benachrichtigungen beim Kopieren, Ausschneiden und Einfügen.
- **Neues Theme HAS Future Sound:** Ein brandneues Audio-Theme mit futuristischen Klängen.
- **ZIP-Import-Fix:** Behebung eines Fehlers beim Importieren von Themes aus ZIP-Dateien.
- **Systemstatus-Härtung:** Verbesserte Stabilität und Zuverlässigkeit der Systemstatus-Überwachung.
- **Leistung:** Allgemeine Leistungsoptimierungen für schnellere Reaktionszeiten.
- **Eingabegesten:** Verbesserte Eingabegesten-Zuordnung und -Verwaltung.

### Version 9.32
- **Systemstatus-Töne:** Added a completely new module to monitor and play sounds for system-level events (USB plug/unplug, AC power changes, battery status, network connectivity, and system wake/sleep) using native Windows notifications for zero lag.
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

## Was ist neu

### Version 9.33
- **Emoji-Engine:** Neue Emoji-Verarbeitungs-Engine für verbesserte Erkennung und akustisches Feedback.
- **Zwischenablage-Benachrichtigungen:** Akustische Benachrichtigungen beim Kopieren, Ausschneiden und Einfügen.
- **Neues Theme HAS Future Sound:** Ein brandneues Audio-Theme mit futuristischen Klängen.
- **ZIP-Import-Fix:** Behebung eines Fehlers beim Importieren von Themes aus ZIP-Dateien.
- **Systemstatus-Härtung:** Verbesserte Stabilität und Zuverlässigkeit der Systemstatus-Überwachung.
- **Leistung:** Allgemeine Leistungsoptimierungen für schnellere Reaktionszeiten.
- **Eingabegesten:** Verbesserte Eingabegesten-Zuordnung und -Verwaltung.

### Version 9.32
- **Systemstatus-Töne:** Einführung einer umfassenden Systemüberwachung für Akku, USB, Netzwerk und Stromversorgung.
- **DSP-Verbesserungen:** Komplett überarbeitete Bass Boost- und Noise Gate-Filter.
- **3D-Audio:** Behebung von Verzögerungen bei Fortschrittsbalken.

### Version 9.30 - 9.31
- **Erstes/Letztes Element:** Universelle Erkennung für erstes/letztes Element.

### Version 9.27 - 9.28
- **Fallback-Töne:** Fallback-Töne hinzugefügt.
- **Überschriften:** Unterstützung für Überschriftenebenen 7, 8 und 9.

### Version 9.23 - 9.26
- **Fehlerbehebungen:** Fehler bei Satznavigation und NVDA 2026.2-Kompatibilität behoben.

## Übersetzer
- **Spanisch:** Hassan AlBarshoumy, Luis Carlos González Morales
- **Italienisch:** Christian Cantelmi, Ciro Cantelmi
- **Russisch:** Valentin Kupriyanov
- **Chinesisch:** Cary-rowen, Jerry
- **Deutsch:** René L

## Support

Für Probleme, Anfragen oder Fehlerberichte wenden Sie sich bitte an den offiziellen Kontaktpunkt:
**[Hassan AlBarshoumys Telegram](https://t.me/HassanAlBarshoumy)**
