import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../services/bring.dart';
import '../services/settings.dart';
import '../theme.dart';
import '../widgets/offer_card.dart';

const _sortLabels = {
  'price': 'Preis mit Auswahl',
  'unit_price': 'Grundpreis mit Auswahl',
  'retailer': 'Händler',
  'product': 'Produktname',
};

/// The result list, mirroring the web results page: text filter, retailer
/// chips, category, sorting, duplicate view, loyalty programs, warnings and
/// endless scrolling.
class ResultsScreen extends StatefulWidget {
  const ResultsScreen({
    super.key,
    required this.client,
    required this.handle,
    required this.settings,
  });

  final KorbKlarClient client;
  final ResultHandle handle;
  final Settings settings;

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  final _scroll = ScrollController();
  final _search = TextEditingController();
  final _offers = <Offer>[];
  final _picked = <String, Offer>{};

  ResultPage? _page;
  ShoppingListInfo _shoppingList = ShoppingListInfo.disabled;

  String _retailer = '';
  String _category = '';
  String _sort = 'price';
  String _view = 'best_only';
  late List<String> _loyalty = [...widget.settings.loyaltyPrograms];

  int _nextPage = 1;
  bool _loading = false;
  bool _refreshing = false;
  bool _done = false;
  String _error = '';
  Timer? _debounce;

  /// Guards against a slow earlier request overwriting a newer result.
  int _requestSeq = 0;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
    _reload();
    _loadShoppingList();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _scroll.dispose();
    _search.dispose();
    super.dispose();
  }

  Future<void> _loadShoppingList() async {
    try {
      final info = await widget.client.shoppingListTargets(widget.handle);
      if (mounted) setState(() => _shoppingList = info);
    } on KorbKlarException {
      // A server without the integration is normal; the app just hides it.
    }
  }

  void _onScroll() {
    if (_scroll.position.pixels >=
        _scroll.position.maxScrollExtent - 600) {
      _loadMore();
    }
  }

  void _reload() {
    _requestSeq++;
    setState(() {
      _offers.clear();
      _nextPage = 1;
      _done = false;
      _error = '';
    });
    _loadMore();
  }

  Future<void> _loadMore() async {
    if (_loading || _done) return;
    final seq = _requestSeq;
    setState(() => _loading = true);
    try {
      final page = await widget.client.results(
        widget.handle,
        filterText: _search.text,
        retailer: _retailer,
        category: _category,
        page: _nextPage,
        view: _view,
        loyaltyPrograms: _loyalty,
        sort: _sort,
      );
      if (!mounted || seq != _requestSeq) return;
      setState(() {
        _page = page;
        _offers.addAll(page.offers);
        _nextPage = page.page + 1;
        _done = !page.hasNext;
      });
    } on KorbKlarException catch (exception) {
      if (!mounted || seq != _requestSeq) return;
      setState(() {
        _error = exception.message;
        _done = true;
      });
    } finally {
      if (mounted && seq == _requestSeq) setState(() => _loading = false);
    }
  }

  /// Re-queries every source for this postal code, bypassing the server's
  /// snapshot cache, then swaps in the new result.
  Future<void> _hardRefresh() async {
    final postalCode = _page?.postalCode ?? '';
    if (postalCode.isEmpty || _refreshing) return;
    setState(() => _refreshing = true);
    try {
      final jobId = await widget.client.startSearch(postalCode, refresh: true);
      SearchProgress? last;
      await for (final progress in widget.client.watchSearch(jobId)) {
        last = progress;
      }
      if (!mounted || last == null) return;
      if (last.isFailed) {
        _toast(last.error.isEmpty ? 'Neuladen fehlgeschlagen.' : last.error);
        return;
      }
      final handle = ResultHandle.parse(last.resultPath);
      if (handle == null) {
        _toast('Der Server lieferte keinen gültigen Ergebnislink.');
        return;
      }
      await Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(
          builder: (_) => ResultsScreen(
            client: widget.client,
            handle: handle,
            settings: widget.settings,
          ),
        ),
      );
    } on KorbKlarException catch (exception) {
      _toast(exception.message);
    } finally {
      if (mounted) setState(() => _refreshing = false);
    }
  }

  void _onSearchChanged(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), _reload);
  }

  void _toggle(Offer offer) {
    setState(() {
      if (_picked.remove(offer.key) == null) _picked[offer.key] = offer;
    });
  }

  // ---------------------------------------------------------------- Bring

  Future<void> _addToList(List<Offer> offers) async {
    if (offers.isEmpty) return;
    const share = BringShare();
    final canShare = share.isSupported;
    final canServer = _shoppingList.configured && _shoppingList.targets.isNotEmpty;

    if (!canShare && !canServer) {
      _toast('Keine Einkaufslisten-Anbindung verfügbar.');
      return;
    }

    final route = (canShare && canServer)
        ? await _askRoute(offers.length)
        : (canServer ? BringRoute.server : BringRoute.share);
    if (route == null) return;

    if (route == BringRoute.share) {
      final ok = await share.share(offers);
      if (ok && mounted) {
        setState(_picked.clear);
        _toast('An die Einkaufsliste übergeben.');
      }
      return;
    }

    final entity = await _resolveEntity();
    if (entity == null) return;
    try {
      final added = await widget.client.addToShoppingList(
        widget.handle,
        entityId: entity,
        offers: offers,
      );
      if (!mounted) return;
      setState(_picked.clear);
      _toast('$added Angebote übernommen.');
    } on KorbKlarException catch (exception) {
      _toast(exception.message);
    }
  }

  Future<BringRoute?> _askRoute(int count) => showModalBottomSheet<BringRoute>(
    context: context,
    backgroundColor: context.colors.panel,
    builder: (sheetContext) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 6),
            child: Text(
              count == 1 ? 'Angebot übernehmen' : '$count Angebote übernehmen',
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.ios_share),
            title: const Text('An Bring senden'),
            subtitle: const Text('Über das Teilen-Menü, ohne Server'),
            onTap: () => Navigator.pop(sheetContext, BringRoute.share),
          ),
          ListTile(
            leading: const Icon(Icons.dns_outlined),
            title: const Text('Über KorbKlar-Server'),
            subtitle: const Text('Mit Händler, Preis und Gültigkeit als Notiz'),
            onTap: () => Navigator.pop(sheetContext, BringRoute.server),
          ),
          const SizedBox(height: 8),
        ],
      ),
    ),
  );

  Future<String?> _resolveEntity() async {
    final targets = _shoppingList.targets;
    if (targets.isEmpty) return null;

    final remembered = widget.settings.shoppingListEntity;
    final known = targets.map((target) => target.entityId).toSet();
    if (remembered.isNotEmpty && known.contains(remembered)) return remembered;
    if (known.contains(_shoppingList.defaultEntity)) {
      return _shoppingList.defaultEntity;
    }
    if (targets.length == 1) return targets.first.entityId;

    final chosen = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: context.colors.panel,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 18, 20, 6),
              child: Text(
                'Ziel-Liste wählen',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
              ),
            ),
            for (final target in targets)
              ListTile(
                leading: const Icon(Icons.checklist),
                title: Text(target.label),
                onTap: () => Navigator.pop(sheetContext, target.entityId),
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (chosen != null) await widget.settings.setShoppingListEntity(chosen);
    return chosen;
  }

  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  // ------------------------------------------------------------- Sheets

  Future<void> _openLoyalty() async {
    final programs = _page?.availableLoyaltyPrograms ?? const <LoyaltyProgram>[];
    if (programs.isEmpty) return;
    final selected = {..._loyalty};
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: context.colors.panel,
      isScrollControlled: true,
      builder: (sheetContext) => StatefulBuilder(
        builder: (_, setSheetState) => SafeArea(
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Padding(
                  padding: EdgeInsets.fromLTRB(20, 18, 20, 4),
                  child: Text(
                    'Bonusprogramme',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                  ),
                ),
                for (final program in programs)
                  CheckboxListTile(
                    value: selected.contains(program.id),
                    title: Text(program.label),
                    subtitle: program.note.isEmpty ? null : Text(program.note),
                    onChanged: (checked) => setSheetState(() {
                      if (checked == true) {
                        selected.add(program.id);
                      } else {
                        selected.remove(program.id);
                      }
                    }),
                  ),
                if ((_page?.loyaltyNote ?? '').isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 4, 20, 10),
                    child: Text(
                      _page!.loyaltyNote,
                      style: TextStyle(
                        color: context.colors.muted,
                        fontSize: 12,
                      ),
                    ),
                  ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                  child: FilledButton(
                    onPressed: () => Navigator.pop(sheetContext),
                    child: const Text('Übernehmen'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    final next = selected.toList();
    if (next.join(',') == _loyalty.join(',')) return;
    await widget.settings.setLoyaltyPrograms(next);
    setState(() => _loyalty = next);
    _reload();
  }

  Future<void> _openWarnings() async {
    final warnings = _page?.warnings ?? const <String>[];
    if (warnings.isEmpty) return;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: context.colors.panel,
      builder: (_) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.all(20),
          children: [
            const Text(
              'Hinweise oder Fehler',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 10),
            for (final warning in warnings)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(warning),
              ),
          ],
        ),
      ),
    );
  }

  // -------------------------------------------------------------- Build

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final page = _page;
    final warnings = page?.warnings ?? const <String>[];

    return Scaffold(
      appBar: AppBar(
        backgroundColor: colors.bg,
        surfaceTintColor: Colors.transparent,
        title: Text(
          page == null ? 'Angebote' : 'PLZ ${page.postalCode}',
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        actions: [
          IconButton(
            tooltip: 'Quellen neu abrufen',
            onPressed: _refreshing || page == null ? null : _hardRefresh,
            icon: _refreshing
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2.2),
                  )
                : const Icon(Icons.refresh),
          ),
          if (warnings.isNotEmpty)
            IconButton(
              tooltip: 'Hinweise',
              onPressed: _openWarnings,
              icon: Badge(
                label: Text('${warnings.length}'),
                child: const Icon(Icons.warning_amber_rounded),
              ),
            ),
          if ((page?.availableLoyaltyPrograms ?? []).isNotEmpty)
            IconButton(
              tooltip: 'Bonusprogramme',
              onPressed: _openLoyalty,
              icon: Icon(
                _loyalty.isEmpty ? Icons.loyalty_outlined : Icons.loyalty,
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          _controls(colors),
          if (page != null) _chips(page, colors),
          const Divider(height: 1),
          Expanded(child: _list(colors)),
        ],
      ),
      bottomNavigationBar: _picked.isEmpty ? null : _selectionBar(colors),
    );
  }

  Widget _controls(KorbColors colors) => Padding(
    padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
    child: Column(
      children: [
        TextField(
          controller: _search,
          onChanged: _onSearchChanged,
          decoration: InputDecoration(
            hintText: 'Produkt oder Marke filtern',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _search.text.isEmpty
                ? null
                : IconButton(
                    icon: const Icon(Icons.clear),
                    onPressed: () {
                      _search.clear();
                      _reload();
                    },
                  ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _sort,
                isExpanded: true,
                decoration: const InputDecoration(
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                ),
                items: [
                  for (final entry in _sortLabels.entries)
                    DropdownMenuItem(
                      value: entry.key,
                      child: Text(
                        entry.value,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
                onChanged: (value) {
                  if (value == null || value == _sort) return;
                  setState(() => _sort = value);
                  _reload();
                },
              ),
            ),
            const SizedBox(width: 8),
            _ViewToggle(
              view: _view,
              hiddenCount: _page?.hiddenCount ?? 0,
              onChanged: (value) {
                setState(() => _view = value);
                _reload();
              },
            ),
          ],
        ),
      ],
    ),
  );

  Widget _chips(ResultPage page, KorbColors colors) {
    final entries = page.retailerCounts.entries.toList()
      ..sort((a, b) => a.key.toLowerCase().compareTo(b.key.toLowerCase()));
    final total = entries.fold<int>(0, (sum, entry) => sum + entry.value);

    return SizedBox(
      height: 46,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        children: [
          _Chip(
            label: 'Alle Händler · $total',
            active: _retailer.isEmpty,
            onTap: () {
              setState(() {
                _retailer = '';
                _category = '';
              });
              _reload();
            },
          ),
          for (final entry in entries)
            _Chip(
              label: '${entry.key} · ${entry.value}',
              active: _retailer == entry.key,
              onTap: () {
                setState(() {
                  _retailer = entry.key;
                  _category = '';
                });
                _reload();
              },
            ),
        ],
      ),
    );
  }

  Widget _list(KorbColors colors) {
    final page = _page;
    if (_error.isNotEmpty && _offers.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(_error, textAlign: TextAlign.center),
        ),
      );
    }
    if (page == null && _loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_offers.isEmpty && !_loading) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            'Keine Angebote passen zu diesem Filter.',
            style: TextStyle(color: colors.muted),
          ),
        ),
      );
    }

    final canPick =
        (const BringShare()).isSupported || _shoppingList.configured;

    return ListView.separated(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 24),
      itemCount: _offers.length + 1,
      separatorBuilder: (_, _) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        if (index == _offers.length) return _footer(colors);
        final offer = _offers[index];
        return OfferCard(
          offer: offer,
          imageUrl: widget.client.imageUrl(offer.imageUrl),
          showRetailer: _retailer.isEmpty,
          selectable: canPick,
          selected: _picked.containsKey(offer.key),
          onToggleSelected: () => _toggle(offer),
          onAddToList: () => _addToList([offer]),
          onOpenSource: () => launchUrl(
            Uri.parse(offer.sourceUrl),
            mode: LaunchMode.externalApplication,
          ),
        );
      },
    );
  }

  Widget _footer(KorbColors colors) {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    final page = _page;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 20),
      child: Center(
        child: Text(
          _error.isNotEmpty
              ? _error
              : page == null
              ? ''
              : '${page.filteredOfferCount} passende Treffer · '
                    '${page.hiddenCount} teurere Dubletten '
                    '${_view == 'all' ? 'eingeblendet' : 'ausgeblendet'}',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: _error.isNotEmpty ? colors.error : colors.muted,
            fontSize: 13,
          ),
        ),
      ),
    );
  }

  Widget _selectionBar(KorbColors colors) => SafeArea(
    child: Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: colors.panel,
        border: Border(top: BorderSide(color: colors.line)),
      ),
      child: Row(
        children: [
          IconButton(
            tooltip: 'Auswahl leeren',
            onPressed: () => setState(_picked.clear),
            icon: const Icon(Icons.close),
          ),
          Expanded(
            child: Text(
              '${_picked.length} ausgewählt',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          FilledButton.icon(
            onPressed: () => _addToList(_picked.values.toList()),
            icon: const Icon(Icons.add_shopping_cart, size: 18),
            label: const Text('Übernehmen'),
          ),
        ],
      ),
    ),
  );
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.active,
    required this.onTap,
  });

  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Padding(
      padding: const EdgeInsets.only(right: 7),
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: active ? colors.chip : colors.panel,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: active ? colors.accent : colors.line),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: active ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ),
      ),
    );
  }
}

class _ViewToggle extends StatelessWidget {
  const _ViewToggle({
    required this.view,
    required this.hiddenCount,
    required this.onChanged,
  });

  final String view;
  final int hiddenCount;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final showingAll = view == 'all';
    return Tooltip(
      message: showingAll
          ? 'Nur günstigste Treffer zeigen'
          : 'Teurere Dubletten einblenden',
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => onChanged(showingAll ? 'best_only' : 'all'),
        child: Container(
          height: 48,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: showingAll ? colors.chip : colors.panel,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: showingAll ? colors.accent : colors.line),
          ),
          child: Row(
            children: [
              Icon(
                showingAll ? Icons.layers : Icons.layers_outlined,
                size: 18,
                color: showingAll ? colors.accent : colors.muted,
              ),
              if (hiddenCount > 0) ...[
                const SizedBox(width: 6),
                Text('$hiddenCount', style: const TextStyle(fontSize: 13)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
