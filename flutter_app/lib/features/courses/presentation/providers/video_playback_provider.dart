import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/utils/bunny_video.dart';
import '../../domain/usecases/course_usecases.dart';
// Re-uses the generated `courseRepositoryProvider` declared in this library.
import 'course_provider.dart';

final getBunnyPlaybackUrlUseCaseProvider =
    Provider<GetBunnyPlaybackUrlUseCase>((ref) {
  return GetBunnyPlaybackUrlUseCase(ref.watch(courseRepositoryProvider));
});

/// Resolves a stored video URL into a directly playable URL.
///
/// Bunny.net URLs are exchanged for a fresh (possibly signed, short-lived) HLS
/// URL via the backend playback endpoint. On any failure we fall back to the
/// raw stored URL so unsigned libraries and preview videos still play.
/// Non-Bunny URLs (direct links / MP4s) pass through unchanged.
///
/// [preview] selects the public preview endpoint (course intro / preview
/// lessons, no enrollment required) instead of the enrollment-gated one.
Future<String?> _resolvePlayableUrl(
  Ref ref,
  String? rawUrl, {
  required bool preview,
}) async {
  if (rawUrl == null || rawUrl.isEmpty) return null;
  if (!BunnyVideo.isBunnyUrl(rawUrl)) return rawUrl;

  final guid = BunnyVideo.extractGuid(rawUrl);
  if (guid == null) return rawUrl;

  final result = await ref
      .watch(getBunnyPlaybackUrlUseCaseProvider)
      .call(guid, preview: preview);
  return result.fold((_) => rawUrl, (url) => url as String);
}

/// Playable URL for enrolled lesson content (enrollment-gated signing).
final playableVideoUrlProvider =
    FutureProvider.family<String?, String?>((ref, rawUrl) {
  return _resolvePlayableUrl(ref, rawUrl, preview: false);
});

/// Playable URL for public preview content — course intro videos and lessons
/// flagged as previews. Signed without requiring enrollment.
final previewVideoUrlProvider =
    FutureProvider.family<String?, String?>((ref, rawUrl) {
  return _resolvePlayableUrl(ref, rawUrl, preview: true);
});
