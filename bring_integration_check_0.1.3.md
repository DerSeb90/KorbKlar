# Bring-Integrationsprüfung 0.1.3

KorbKlar verwendet weiterhin ausschließlich Web Share beziehungsweise die
Zwischenablage. Es gibt keine Zugangsdaten, keine direkte Bring-API und keine
zweite Einkaufsliste.

Übergeben werden offene Artikel mit Menge, Produktname, optionaler Marke,
Packungsgröße, optionaler EAN und Händler. Die KorbKlar-Kategorie wird bewusst
nicht in den Bring-Text geschrieben, damit eine fehlerhafte oder abweichende
Kategorie Brings eigene Produkterkennung nicht beeinflusst.

Die lokale Liste bleibt die führende Datenquelle. Abbruch oder fehlendes Web
Share führt auf die bestehende Zwischenablage zurück.
