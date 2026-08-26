import 'package:shared_preferences/shared_preferences.dart';

/// Locally remembered preferences. Nothing here leaves the device except the
/// server address the user typed themselves.
class Settings {
  Settings._(this._prefs);

  static Future<Settings> load() async =>
      Settings._(await SharedPreferences.getInstance());

  final SharedPreferences _prefs;

  static const _serverUrl = 'server_url';
  static const _postalCode = 'postal_code';
  static const _loyalty = 'loyalty_programs';
  static const _listEntity = 'shopping_list_entity';
  static const _apiKey = 'api_key';
  static const _basket = 'collected_offers';

  String get serverUrl => _prefs.getString(_serverUrl) ?? '';
  Future<void> setServerUrl(String value) => _prefs.setString(_serverUrl, value);

  /// Bearer token for a publicly reachable instance. Empty when the server
  /// is only used over VPN.
  String get apiKey => _prefs.getString(_apiKey) ?? '';
  Future<void> setApiKey(String value) => _prefs.setString(_apiKey, value);

  String get postalCode => _prefs.getString(_postalCode) ?? '';
  Future<void> setPostalCode(String value) =>
      _prefs.setString(_postalCode, value);

  List<String> get loyaltyPrograms => _prefs.getStringList(_loyalty) ?? const [];
  Future<void> setLoyaltyPrograms(List<String> value) =>
      _prefs.setStringList(_loyalty, value);

  /// Offers the user collected but has not sent anywhere yet, as JSON.
  ///
  /// Persisted so a reload of the results, or closing the app, does not throw
  /// the collection away.
  List<String> get collectedOffers => _prefs.getStringList(_basket) ?? const [];
  Future<void> setCollectedOffers(List<String> value) =>
      _prefs.setStringList(_basket, value);

  String get shoppingListEntity => _prefs.getString(_listEntity) ?? '';
  Future<void> setShoppingListEntity(String value) =>
      _prefs.setString(_listEntity, value);
}
