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

  String get serverUrl => _prefs.getString(_serverUrl) ?? '';
  Future<void> setServerUrl(String value) => _prefs.setString(_serverUrl, value);

  String get postalCode => _prefs.getString(_postalCode) ?? '';
  Future<void> setPostalCode(String value) =>
      _prefs.setString(_postalCode, value);

  List<String> get loyaltyPrograms => _prefs.getStringList(_loyalty) ?? const [];
  Future<void> setLoyaltyPrograms(List<String> value) =>
      _prefs.setStringList(_loyalty, value);

  String get shoppingListEntity => _prefs.getString(_listEntity) ?? '';
  Future<void> setShoppingListEntity(String value) =>
      _prefs.setString(_listEntity, value);
}
