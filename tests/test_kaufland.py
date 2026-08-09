from datetime import date

from supermarkt.sources.kaufland import OfficialKauflandSource


def test_kaufland_keeps_current_thursday_week_on_sunday():
    assert 'kloffer-week=current' in OfficialKauflandSource._overview_url(date(2026, 8, 9))
    assert 'kloffer-week=current' in OfficialKauflandSource._overview_url(date(2026, 8, 10))


def test_kaufland_parser_stops_before_xtra_duplicate_section():
    page = '''
    <html><body>
      <h2>Aktuelle Angebote</h2>
      <div>
        <a href="/a"><img src="https://img.example/a.jpg">KNÜLLER TEST Kaffee je 500-g-Packg. nur 4,99</a>
        <a href="/b"><img src="https://img.example/b.jpg">TEST Milch je 1-l-Packg. nur 0,99</a>
        <a href="#more">Weitere Angebote anzeigen</a>
      </div>
      <h2>Aktuelle Angebote im Prospekt zum Blättern</h2>
      <a href="/prospekt">Prospekt ansehen</a>
      <h2>Aktuelle Kaufland Card XTRA Angebote</h2>
      <a href="/a-xtra"><img src="https://img.example/a.jpg">KNÜLLER TEST Kaffee je 500-g-Packg. nur 4,99 Mit Kaufland Card XTRA nur 4,49</a>
    </body></html>
    '''
    source = OfficialKauflandSource.__new__(OfficialKauflandSource)
    offers = source._parse_page(page, OfficialKauflandSource.CURRENT_OVERVIEW_URL)
    assert [offer.name for offer in offers] == ['TEST Kaffee', 'TEST Milch']
    assert all(not offer.benefits for offer in offers)


def test_kaufland_primary_section_excludes_later_offer_anchors():
    page = '''
    <h2>Aktuelle Angebote</h2>
    <section><a href="/weekly">Produkt nur 1,99</a></section>
    <h2>Aktuelle Kaufland Card XTRA Angebote</h2>
    <section><a href="/duplicate">Produkt nur 1,99</a></section>
    '''
    section = OfficialKauflandSource._offer_section_html(page)
    assert '/weekly' in section
    assert '/duplicate' not in section


def test_kaufland_category_headings_do_not_truncate_weekly_grid():
    page = '''
    <h2>Aktuelle Angebote</h2>
    <a href="/a">Produkt A nur 1,99</a>
    <h2>Obst und Gemüse</h2>
    <a href="/b">Produkt B nur 2,99</a>
    <h2>Aktuelle Kaufland Card XTRA Angebote</h2>
    <a href="/duplicate">Produkt A nur 1,99</a>
    '''
    section = OfficialKauflandSource._offer_section_html(page)
    assert '/a' in section
    assert '/b' in section
    assert '/duplicate' not in section
