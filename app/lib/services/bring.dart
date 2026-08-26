import 'dart:io';

import 'package:share_plus/share_plus.dart';

import '../api/models.dart';

/// The two ways this app can get an offer onto a Bring shopping list.
enum BringRoute {
  /// Hand the text to whatever app the user picks, typically Bring itself.
  /// Works offline and needs no token, but carries only text.
  share,

  /// Go through the KorbKlar server's Home Assistant integration, which
  /// writes a proper article plus note. Needs the server to be reachable.
  server,
}

/// Formats offers for sharing and hands them to the platform share sheet.
///
/// Bring has no documented public write API for third-party apps, so the
/// share sheet is the honest route on device: Bring registers as a receiver
/// for plain text and adds the shared item. The server route stays available
/// for the richer article-plus-note form.
class BringShare {
  const BringShare();

  /// Sharing is only meaningful where a share sheet exists.
  bool get isSupported => Platform.isAndroid || Platform.isIOS;

  /// One offer as a single line: product, retailer and price.
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
      if (offer.retailer.isNotEmpty) offer.retailer,
      if (price.isNotEmpty) price,
    ];
    return parts.join(' · ');
  }

  static String textFor(List<Offer> offers) =>
      offers.map(lineFor).join('\n');

  /// Opens the share sheet. Returns false if the user dismissed it.
  ///
  /// `ShareResult.unavailable` is reported on platforms that cannot tell us
  /// what the user picked; that is not a failure, so it counts as success.
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
}
