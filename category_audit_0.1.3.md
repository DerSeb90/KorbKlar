# Kategorie-Audit 0.1.3

Geprüft wurden 9.921 eindeutige Produkt-/Kategorievarianten aus den vorhandenen
lokalen Angebotssnapshots. Der Audit verändert keine Preise, Händlerdaten oder
Pfandwerte.

| Produkt | Kategorie vor 0.1.3 | Erwartet | Ursache | Fix |
|---|---|---|---|---|
| CLEANMAXX Bodenkehrer | Tierbedarf | Haushalt & Reinigung | Quellkategorie gewann vor dem Produktnamen | Produktart `Bodenkehrer` priorisiert |
| MÄLZER&FU Ice Cream, Franzbrötchen | Backwaren | Tiefkühl / Eis & Dessert | Geschmacksvariante/Quelle schlug die Produktart | `Ice Cream` im Namen gewinnt |
| FUNNY-FRISCH Pom-Bär | Süßwaren & Snacks/Weitere Angebote | Snacks | uneinheitliche Händlergruppen | Produktname `Pom-Bär` normalisiert |
| SHEBA/WHISKAS Katzenfutter | Haushalt & Reinigung | Tierbedarf | kombinierte Quellgruppe wurde zu früh gemappt | konkrete Produktart gewinnt |
| Ital. Bio-Rucola | Getränke | Obst & Gemüse | generische Angebotsgruppe plus Fehlzuordnung | `Rucola` als Produktart erkannt |
| Smarties Riesenrolle | Getränke | Snacks | Quellzuordnung widersprach dem Produkt | konkrete Süßware gewinnt |
| Pain au chocolat | Vorräte | Backwaren | Quellgruppe war zu allgemein | konkrete Backware gewinnt |
| Calippo/Pirulo Cola | Getränke | Tiefkühl / Eis & Dessert | Geschmackswort `Cola` dominierte | eindeutige Eisproduktnamen haben Vorrang |
| Tiefkühlpizza | Backwaren | Tiefkühl / Eis & Dessert | `Pizza`/Backwaren-Quelltext wurde fehlgedeutet | Tiefkühl-Quellgruppe wird kanonisch abgebildet |
| WC-Reiniger | Getränke/Weitere Angebote | Haushalt & Reinigung | Quelle fehlte oder war falsch | konkrete Reinigerbegriffe gewinnen |

Konflikte werden als `category_conflict` zusammen mit `source_category` und
`detected_category` am internen Angebot festgehalten und protokolliert.
