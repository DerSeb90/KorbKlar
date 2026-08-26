import 'dart:io';

import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../api/models.dart';

/// The ways this app can get collected offers out to a shopping list.
enum BringRoute {
  /// Hand the text to the platform share sheet, where Bring registers as a
  /// receiver. Works offline and needs no token, but carries only text.
  share,

  /// Go through the KorbKlar server's Home Assistant integration, which
  /// writes a proper article plus a note. Needs the server to be reachable.
  server,

  /// Copy the list to the clipboard. The fallback on desktop, where there is
  /// no share sheet and no Bring app to receive one.
  clipboard,
}

/// Formats offers for sharing and hands them to the platform.
///
/// Bring has no documented public write API for third-party apps, so the
/// share sheet is the honest route on a phone: Bring accepts plain text and
/// adds the shared items. The server route stays available for the richer
/// article-plus-note form.
class BringShare {
  const BringShare();

  /// Whether a share sheet exists on this platform.
  bool get isSupported => Platform.isAndroid || Platform.isIOS;

  /// One offer as a single line: product, pack, retailer and price.
  ///
  /// Only values the offer actually carries are included, matching how the
  /// server builds its note.
  static String lineFor(Offer offer) {
    final price = offer.effectivePriceText.isNotEmpty
        ? offer.effectivePriceText
        : offer.regularPriceText;
    final parts = [
      offer.product,
      if (offer.pack.isNotEmpty) offer.pack,
      if (offer.retailerText.isNotEmpty) offer.retailerText,
      if (price.isNotEmpty) price,
    ];
    return parts.join(' · ');
  }

  static String textFor(List<Offer> offers) => offers.map(lineFor).join('\n');

  /// Opens the share sheet. Returns false only if the user dismissed it.
  ///
  /// `ShareResult.unavailable` comes back on platforms that cannot report
  /// what the user picked; that is not a failure.
  Future<bool> share(List<Offer> offers) async {
    if (offers.isEmpty) return false;
    final result = await Share.share(
      textFor(offers),
      subject: offers.length == 1
          ? offers.first.product
          : '${offers.length} Angebote von KorbKlar',
    );
    return result.status != ShareResultStatus.dismissed;
  }

  /// Puts the same text on the clipboard.
  Future<void> copy(List<Offer> offers) async {
    if (offers.isEmpty) return;
    await Clipboard.setData(ClipboardData(text: textFor(offers)));
  }
}
