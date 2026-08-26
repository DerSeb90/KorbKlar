import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../main.dart';
import '../services/settings.dart';
import '../theme.dart';
import 'results_screen.dart';

/// Postal-code entry and live search progress, mirroring the web home page.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.settings});

  final Settings settings;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final TextEditingController _postalCode = TextEditingController(
    text: widget.settings.postalCode,
  );
  late final TextEditingController _server = TextEditingController(
    text: widget.settings.serverUrl,
  );

  StreamSubscription<SearchProgress>? _watch;
  SearchProgress? _progress;
  String _error = '';
  bool _busy = false;

  @override
  void dispose() {
    _watch?.cancel();
    _postalCode.dispose();
    _server.dispose();
    super.dispose();
  }

  bool get _serverConfigured => widget.settings.serverUrl.isNotEmpty;

  Future<void> _saveServer() async {
    final normalized = KorbKlarClient.normalizeBaseUrl(_server.text);
    if (normalized.isEmpty) {
      setState(() => _error = 'Bitte die Adresse deines KorbKlar-Servers eingeben.');
      return;
    }
    setState(() {
      _busy = true;
      _error = '';
    });
    final client = KorbKlarClient(baseUrl: normalized);
    try {
      final ok = await client.ping();
      if (!ok) {
        setState(() => _error = 'Unter dieser Adresse antwortet kein KorbKlar.');
        return;
      }
      await widget.settings.setServerUrl(normalized);
      _server.text = normalized;
      setState(() {});
    } on KorbKlarException catch (exception) {
      setState(() => _error = exception.message);
    } finally {
      client.close();
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _search() async {
    final postalCode = _postalCode.text.trim();
    if (!RegExp(r'^\d{5}$').hasMatch(postalCode)) {
      setState(() => _error = 'Bitte eine gültige fünfstellige deutsche Postleitzahl eingeben.');
      return;
    }
    FocusScope.of(context).unfocus();
    await widget.settings.setPostalCode(postalCode);

    final client = KorbKlarClient(baseUrl: widget.settings.serverUrl);
    setState(() {
      _busy = true;
      _error = '';
      _progress = null;
    });

    try {
      final jobId = await client.startSearch(postalCode);
      _watch = client.watchSearch(jobId).listen(
        (progress) async {
          if (!mounted) return;
          setState(() => _progress = progress);
          if (progress.isFailed) {
            setState(() {
              _busy = false;
              _error = progress.error.isNotEmpty
                  ? progress.error
                  : 'Die Suche ist fehlgeschlagen.';
            });
            client.close();
            return;
          }
          if (!progress.isDone) return;

          final handle = ResultHandle.parse(progress.resultPath);
          if (handle == null) {
            setState(() {
              _busy = false;
              _error = 'Der Server lieferte keinen gültigen Ergebnislink.';
            });
            client.close();
            return;
          }
          setState(() => _busy = false);
          await Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => ResultsScreen(
                client: client,
                handle: handle,
                settings: widget.settings,
              ),
            ),
          );
          client.close();
        },
        onError: (Object error) {
          if (!mounted) return;
          setState(() {
            _busy = false;
            _error = '$error';
          });
          client.close();
        },
      );
    } on KorbKlarException catch (exception) {
      client.close();
      if (mounted) {
        setState(() {
          _busy = false;
          _error = exception.message;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Center(child: KorbKlarWordmark(fontSize: 34)),
                  const SizedBox(height: 8),
                  Center(
                    child: Text(
                      'Regionale Supermarktangebote vergleichen',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: colors.muted, fontSize: 15),
                    ),
                  ),
                  const SizedBox(height: 28),
                  if (!_serverConfigured) ..._serverSetup(colors) else ..._searchForm(colors),
                  if (_error.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    _ErrorBox(message: _error),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _serverSetup(KorbColors colors) => [
    _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Server verbinden',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          Text(
            'Adresse deiner KorbKlar-Instanz. Die App rechnet nichts selbst, '
            'sie zeigt den Vergleich deines Servers.',
            style: TextStyle(color: colors.muted, fontSize: 14),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _server,
            autocorrect: false,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(
              hintText: 'http://192.0.2.10:8000',
              prefixIcon: Icon(Icons.dns_outlined),
            ),
            onSubmitted: (_) => _saveServer(),
          ),
          const SizedBox(height: 14),
          FilledButton(
            onPressed: _busy ? null : _saveServer,
            child: _busy
                ? const _ButtonSpinner()
                : const Text('Verbindung prüfen'),
          ),
        ],
      ),
    ),
  ];

  List<Widget> _searchForm(KorbColors colors) => [
    _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _postalCode,
            keyboardType: TextInputType.number,
            maxLength: 5,
            enabled: !_busy,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            style: const TextStyle(fontSize: 22, letterSpacing: 4),
            decoration: const InputDecoration(
              labelText: 'Postleitzahl',
              hintText: '26188',
              counterText: '',
            ),
            onSubmitted: (_) => _search(),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _busy ? null : _search,
            child: _busy
                ? const _ButtonSpinner()
                : const Text('Angebote vergleichen'),
          ),
        ],
      ),
    ),
    if (_progress != null) ...[
      const SizedBox(height: 16),
      _ProgressPanel(progress: _progress!),
    ],
    const SizedBox(height: 16),
    Center(
      child: TextButton.icon(
        onPressed: _busy
            ? null
            : () async {
                await widget.settings.setServerUrl('');
                setState(() {});
              },
        icon: const Icon(Icons.dns_outlined, size: 18),
        label: Text(
          widget.settings.serverUrl,
          style: TextStyle(color: colors.muted, fontSize: 13),
        ),
      ),
    ),
  ];
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: colors.panel,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.line),
      ),
      child: child,
    );
  }
}

class _ProgressPanel extends StatelessWidget {
  const _ProgressPanel({required this.progress});

  final SearchProgress progress;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final total = progress.totalSources > 0 ? progress.totalSources : 6;
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  progress.step,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              Text(
                '${progress.progress}%',
                style: TextStyle(color: colors.muted),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: progress.progress <= 0 ? null : progress.progress / 100,
              minHeight: 8,
              backgroundColor: colors.chip,
              valueColor: AlwaysStoppedAnimation(colors.accent),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            [
              if (progress.source.isNotEmpty) progress.source,
              if (progress.retailer.isNotEmpty) progress.retailer,
              '${progress.processedSources}/$total Quellen',
              '${progress.processedProducts} Angebote',
            ].join(' · '),
            style: TextStyle(color: colors.muted, fontSize: 13),
          ),
        ],
      ),
    );
  }
}

class _ErrorBox extends StatelessWidget {
  const _ErrorBox({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.error.withValues(alpha: 0.4)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.error_outline, color: colors.error, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(message, style: TextStyle(color: colors.error)),
          ),
        ],
      ),
    );
  }
}

class _ButtonSpinner extends StatelessWidget {
  const _ButtonSpinner();

  @override
  Widget build(BuildContext context) => const SizedBox(
    height: 20,
    width: 20,
    child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white),
  );
}
