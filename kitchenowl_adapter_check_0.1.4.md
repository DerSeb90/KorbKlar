# KitchenOwl-Adapterprüfung 0.1.4

Stand: 28. August 2026

## Installierter Stand

Auf der geprüften VM existiert bereits genau ein KitchenOwl-Stack. Der
Anwendungscontainer ist gesund und die Oberfläche antwortet über den intern
konfigurierten Zugriff. Offene Registrierung ist deaktiviert. Der bestehende
Stack, seine Volumes und Nutzerdaten wurden nicht verändert.

## API-Grenze

Die installierte Controller- und Schema-Version bestätigt den authentifizierten
Endpunkt `POST /api/shoppinglist/{id}/add-item-by-name` mit genau den Feldern
`name` und optional `description`. Long-Lived Tokens werden nach Anmeldung über
`POST /api/auth/llt` erzeugt. KorbKlar hält deshalb nur eine lokale Abbildung
auf dieses Schema bereit und speichert weder URL noch Token.

`kitchenOwlItem()` überträgt den Produktnamen einschließlich Marke als `name`.
Menge, Einheit, Packung, Kategorie, Händler, Angebotspreis, Zeitraum und EAN
werden in `description` abgebildet, weil das Add-by-name-Schema keine separaten
Preis- oder Mengenfelder besitzt.

## Teststatus

Die Weboberfläche, Container-Health und interne Anbindung sind erreichbar.
Das Schema wurde mit FUNNY-FRISCH Pom-Bär, Menge 1, Kategorie Snacks, ALDI Nord
und 0,99 € als automatisierter KorbKlar-Test geprüft. Ein schreibender Test in
eine bestehende persönliche Liste wurde bewusst nicht ausgeführt: Im Projekt
liegt kein KitchenOwl-Token vor, und vorhandene Konten oder Passwörter werden
nicht zurückgesetzt. Nach manueller Tokenbereitstellung kann eine spätere
Connector-Ausbaustufe diesen Endpunkt verwenden.
