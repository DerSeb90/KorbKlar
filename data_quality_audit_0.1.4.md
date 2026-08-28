# Datenqualitäts-Audit KorbKlar 0.1.4

Stand: 28. August 2026

| Bereich / Produkt | fehlerhafter Stand | erwarteter Stand | Ursache | Korrektur |
|---|---|---|---|---|
| Globus, PLZ 93073 | ganze Prospektseite je Artikel | echtes Artikelbild oder leer | Seitenfeld `image` wurde pauschal auf Artikel kopiert | nur artikelbezogene Bildfelder; Flyer-/PDF-Muster gesperrt; streng abgeglichene KaufDA-Einzelangebotsbilder zulässig |
| ALDI Süd RIO D'OR Orangennektar 1,5 l | 0,25 € Preis und 0,25 € Pfand; Name teils „Vegan“ | 1,39 € Preis, 0,25 € Pfand, 0,93 €/l | Grundpreis, Verkaufspreis, Altpreis und Pfand wurden als Grenzen mehrerer Produkte interpretiert | Aufteilung nur bei einem erkennbaren nächsten Produkt; Grundpreis und Pfand sind keine Verkaufsgrenze |
| ALDI Süd Walnusskerne 200 g | 12,45 € | 2,49 € | Grundpreis wurde als Produktpreis eines künstlichen Segments übernommen | gleicher struktureller Parserfix |
| ALDI Süd Paranusskerne 200 g | 15,95 € | 3,19 € | Grundpreis wurde als Produktpreis eines künstlichen Segments übernommen | gleicher struktureller Parserfix |

## Weitere Händlerprüfung

- ALDI Nord verwendet das strukturierte `promotionPrices.priceValue`; Pfand und
  Grundpreis bleiben getrennt.
- REWE, Kaufland, EDEKA/Marktkauf, Rossmann und Müller binden Bilder innerhalb
  einer Artikelkarte beziehungsweise eines Produktdokuments. Ein pauschaler
  Prospektseiten-Fallback wurde nicht gefunden.
- REWE Bonus, Kaufland XTRA und Netto+ bleiben getrennte Vorteilstypen und
  überschreiben nicht blind den regulären Preis.
- Explizite Pfandwerte bleiben im separaten Pfandfeld; aus Verpackungsnamen wird
  kein Pfandbetrag geraten.
- Die bestehende Kategorienormalisierung und ihr Konfliktprotokoll bleiben
  unverändert. Im geprüften Pfad wurde keine neue Lebensmittel-/Non-Food-
  Fehlklassifizierung verursacht.

Die Cache-Generation 8 invalidiert sowohl alte Globus-Seitenbilder als auch
alte ALDI-Süd-Fehlsegmente und trennt die neue optionale Bildanreicherung. Es
werden keine Laufzeitdaten pauschal gelöscht.
