/// Helpers for working with Bunny.net Stream CDN video URLs.
///
/// Lesson videos appear in two shapes:
///  - Raw HLS from the pull zone:
///    `https://<pull-zone>.b-cdn.net/<video-guid>/playlist.m3u8`
///  - Bunny's embed/player links (sometimes stored in the "youtube" field):
///    `https://iframe.mediadelivery.net/embed/<library-id>/<video-guid>`
///    `https://player.mediadelivery.net/play/<library-id>/<video-guid>`
///
/// Before playback the app exchanges the GUID for a (possibly signed,
/// short-lived) URL via the backend `/api/v1/bunny/video/{guid}/playback`
/// endpoint.
class BunnyVideo {
  BunnyVideo._();

  /// True for Bunny Stream CDN URLs (`*.b-cdn.net`) and Bunny embed/player
  /// URLs (`*.mediadelivery.net`).
  static bool isBunnyUrl(String? url) {
    if (url == null || url.isEmpty) return false;
    final uri = Uri.tryParse(url);
    if (uri == null) return false;
    final host = uri.host.toLowerCase();
    return host.endsWith('b-cdn.net') || host.endsWith('mediadelivery.net');
  }

  /// Extract the Bunny video GUID from a stored URL.
  ///  - CDN HLS (`.../<guid>/playlist.m3u8`)        → first path segment
  ///  - embed/player (`.../<verb>/<lib>/<guid>`)     → last path segment
  /// Returns null when [url] is not a recognisable Bunny URL.
  static String? extractGuid(String? url) {
    if (!isBunnyUrl(url)) return null;
    final uri = Uri.parse(url!);
    final segments = uri.pathSegments.where((s) => s.isNotEmpty).toList();
    if (segments.isEmpty) return null;
    final host = uri.host.toLowerCase();
    // mediadelivery: /embed|play/<lib>/<guid> → guid is last.
    // b-cdn:         /<guid>/playlist.m3u8    → guid is first.
    return host.endsWith('mediadelivery.net') ? segments.last : segments.first;
  }

  /// Extract the numeric library id embedded in a Bunny embed/player URL
  /// (`.../<verb>/<library-id>/<guid>`). Returns null for CDN URLs (their
  /// library id is not in the path — callers fall back to the configured one).
  static int? extractLibraryId(String? url) {
    if (url == null || url.isEmpty) return null;
    final uri = Uri.tryParse(url);
    if (uri == null || !uri.host.toLowerCase().endsWith('mediadelivery.net')) {
      return null;
    }
    final segments = uri.pathSegments.where((s) => s.isNotEmpty).toList();
    // Expect [embed|play, <lib>, <guid>]: the library id sits before the guid.
    if (segments.length < 2) return null;
    return int.tryParse(segments[segments.length - 2]);
  }
}
