# Bild-Audit KorbKlar 0.1.4

Stand: 28. August 2026

| Händler | geprüfter Bildpfad | Ergebnis |
|---|---|---|
| Globus | offizielles `pageitems.json`, optional KaufDA und danach Marktguru nur fürs Bild | Die Live-Daten für 93073/Neutraubling enthalten Seitenbilder und PDFs nur auf Seitenebene; aktuelle Artikel besitzen keine eigenen Bildfelder. Seitenbilder werden nicht mehr übernommen. Explizite künftige Produkt-/Artikel-/Angebotsbilder werden priorisiert. KaufDA/Marktguru dürfen nur bei eindeutig gleichem Namen, Preis, Packung und Zeitraum eine Bild-URL ergänzen. Der Live-Abgleich 93073 lieferte 6 eindeutige KaufDA-Bilder für 477 offizielle Angebote; Marktguru lieferte 0 Globus-Datensätze. |
| REWE | Bildcontainer der einzelnen Angebotskarte | Nur Bilder vom REWE-Produktbildhost; Logos, Bonusgrafiken, Platzhalter und Header werden verworfen. |
| Kaufland | Angebotskarte beziehungsweise `listImage` des einzelnen Artikels | Artikelbezogene Bilder werden normalisiert; bekannte Werbe-, Logo- und Platzhalterbilder werden verworfen. |
| ALDI Nord/Süd | strukturierter Produktdatensatz beziehungsweise einzelne Produktkarte | Bildauswahl erfolgt am Produkt; bekannte Werbe-, Logo- und Platzhalterbilder werden verworfen. |
| EDEKA / Marktkauf | Bildfelder des einzelnen Angebotsdokuments | Priorität `bild_app`, `bild_web130`, `bild_web90`; kein Seitenbild-Fallback. |
| Rossmann | Bild der einzelnen als Werbung markierten Produktkarte | Kein Prospektseiten-Fallback gefunden. |
| Müller | bevorzugt Produktbild der einzelnen Produktkarte | Kein Prospektseiten-Fallback gefunden. |

Es wurde kein weiterer Adapter gefunden, der ein übergeordnetes Prospekt-, PDF-
oder Kategorie-Seitenbild pauschal jedem Angebot zuordnet. Deshalb wurde die
Änderung auf den nachgewiesenen Globus-Fehler begrenzt.
