import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';
import 'package:chewie/chewie.dart';
import 'package:youtube_player_flutter/youtube_player_flutter.dart';
import '../../../core/utils/bunny_video.dart';
import '../../../config/app_config.dart';
import 'bunny_video_player_widget.dart';

/// Plays a lesson/course video.
///
/// Supports YouTube links (via [youtubeUrl]) and direct network videos
/// (via [videoUrl]) — including Bunny.net HLS `.m3u8` streams. For Bunny.net
/// videos, it uses the specialized [BunnyVideoPlayerWidget] for native
/// features like quality switching and anti-screenshot protection.
class VideoPlayerWidget extends StatefulWidget {
  final String? videoUrl;
  final String? youtubeUrl;
  final bool autoPlay;

  /// When set, playback is capped to this many seconds (a free preview): the
  /// video auto-plays and is replaced by an "enroll to continue" overlay once
  /// the cap elapses.
  final int? previewMaxSeconds;

  /// Override to force portrait (9/16) or landscape (16/9) aspect ratio.
  /// If null, auto-detects from the video size.
  final bool? isPortrait;

  /// Fallback duration in seconds, useful for players like Bunny that don't
  /// expose exact duration to Dart.
  final int? videoDuration;

  /// The title of the next video to display in the autoplay countdown.
  final String? nextVideoTitle;

  /// Callback when the autoplay countdown completes or the user clicks "Play Now".
  final VoidCallback? onPlayNext;

  /// Callback when playback finishes naturally.
  final VoidCallback? onEnded;

  const VideoPlayerWidget({
    super.key,
    this.videoUrl,
    this.youtubeUrl,
    this.autoPlay = false,
    this.previewMaxSeconds,
    this.isPortrait,
    this.videoDuration,
    this.nextVideoTitle,
    this.onPlayNext,
    this.onEnded,
  });

  @override
  State<VideoPlayerWidget> createState() => _VideoPlayerWidgetState();
}

class _VideoPlayerWidgetState extends State<VideoPlayerWidget> {
  VideoPlayerController? _videoPlayerController;
  ChewieController? _chewieController;
  YoutubePlayerController? _youtubePlayerController;
  Timer? _previewTimer;
  Timer? _countdownTimer;
  Timer? _bunnyDurationTimer;
  String? _error;
  bool _previewEnded = false;
  // Set when the resolved source is a Bunny.net URL (rendered natively).
  String? _bunnyUrl;

  // Autoplay countdown state
  bool _showCountdown = false;
  int _secondsLeft = 5;
  bool _isEndedTriggered = false;

  bool get _isPreview => widget.previewMaxSeconds != null;

  @override
  void initState() {
    super.initState();
    _initializePlayer();
  }

  @override
  void didUpdateWidget(covariant VideoPlayerWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.videoUrl != widget.videoUrl ||
        oldWidget.youtubeUrl != widget.youtubeUrl) {
      _disposeControllers();
      _previewEnded = false;
      _showCountdown = false;
      _isEndedTriggered = false;
      _initializePlayer();
    }
  }

  Future<void> _initializePlayer() async {
    _isEndedTriggered = false;
    _showCountdown = false;
    final youtubeUrl = widget.youtubeUrl;
    String? videoUrl = widget.videoUrl;

    // A genuine YouTube link plays in the YouTube player. A non-YouTube value
    // in the youtube field (e.g. a Bunny `mediadelivery.net` embed link that
    // the CMS stored there) is NOT a YouTube id — fall through and treat it as
    // a video URL so it still plays instead of erroring "Invalid YouTube URL".
    if (youtubeUrl != null && youtubeUrl.isNotEmpty) {
      final videoId = YoutubePlayer.convertUrlToId(youtubeUrl);
      if (videoId != null) {
        _youtubePlayerController = YoutubePlayerController(
          initialVideoId: videoId,
          flags: YoutubePlayerFlags(
            autoPlay: _isPreview ? true : widget.autoPlay,
            mute: false,
          ),
        );
        _startPreviewTimer();
        if (mounted) setState(() {});
        return;
      }
      videoUrl ??= youtubeUrl;
    }

    if (videoUrl == null || videoUrl.isEmpty) {
      if (mounted) setState(() => _error = 'No video available');
      return;
    }

    if (BunnyVideo.isBunnyUrl(videoUrl)) {
      // Bunny URLs render via the native BunnyVideoPlayerWidget (reliable HLS
      // playback). A preview just adds a timer that ends it at the cap.
      _bunnyUrl = videoUrl;
      _startPreviewTimer();

      // For Bunny Video, we use native callbacks for completion events.
      // We also use the lesson duration (converted from minutes to seconds) as a fallback
      // to trigger the next-video autoplay in case native events are missed.
      final duration = widget.videoDuration;
      if (duration != null && duration > 0 && widget.nextVideoTitle != null) {
        _bunnyDurationTimer?.cancel();
        _bunnyDurationTimer = Timer(Duration(seconds: duration * 60), () {
          _onVideoEnded();
        });
      }

      if (mounted) setState(() {});
      return;
    }

    final controller = VideoPlayerController.networkUrl(Uri.parse(videoUrl));
    _videoPlayerController = controller;

    try {
      await controller.initialize();
      if (!mounted) return;

      // Add listener to detect video completion
      controller.addListener(() {
        if (!mounted) return;
        final value = controller.value;
        if (value.isInitialized &&
            value.position >= value.duration &&
            value.duration > Duration.zero) {
          _onVideoEnded();
        }
      });

      final size = controller.value.size;
      final isPortraitVideo = widget.isPortrait ?? (size.height > size.width && size.width > 0);
      final aspectRatio = controller.value.aspectRatio == 0
          ? (isPortraitVideo ? 9 / 16 : 16 / 9)
          : controller.value.aspectRatio;

      // Restrict orientations during fullscreen based on the video's aspect ratio
      final orientationsOnEnter = isPortraitVideo
          ? const [DeviceOrientation.portraitUp, DeviceOrientation.portraitDown]
          : const [DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight];

      _chewieController = ChewieController(
        videoPlayerController: controller,
        autoPlay: _isPreview ? true : widget.autoPlay,
        looping: false,
        aspectRatio: aspectRatio,
        showControls: !_isPreview, // can't skip past a preview cap
        // Tapping fullscreen rotates the video according to its aspect ratio;
        // exiting returns the app to portrait. Previews stay inline.
        allowFullScreen: !_isPreview,
        deviceOrientationsOnEnterFullScreen: orientationsOnEnter,
        deviceOrientationsAfterFullScreen: const [
          DeviceOrientation.portraitUp,
        ],
        errorBuilder: (context, errorMessage) => Center(
          child: Text(errorMessage,
              style: const TextStyle(color: Colors.white)),
        ),
      );
      _startPreviewTimer();
      setState(() {});
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = 'Unable to play this video');
    }
  }

  /// Ends the preview after [previewMaxSeconds]; pauses any active controller
  /// and flips to the "enroll" overlay.
  void _startPreviewTimer() {
    final cap = widget.previewMaxSeconds;
    if (cap == null) return;
    _previewTimer?.cancel();
    _previewTimer = Timer(Duration(seconds: cap), () {
      _videoPlayerController?.pause();
      _youtubePlayerController?.pause();
      if (mounted) setState(() => _previewEnded = true);
    });
  }

  void _onVideoEnded() {
    if (!mounted) return;
    if (_showCountdown || _previewEnded || _error != null) return;

    if (!_isEndedTriggered) {
      _isEndedTriggered = true;
      widget.onEnded?.call();
    }

    // If nextVideoTitle/onPlayNext is set, show the 5-second countdown overlay
    if (widget.nextVideoTitle != null && widget.onPlayNext != null) {
      setState(() {
        _showCountdown = true;
        _secondsLeft = 5;
      });

      _countdownTimer?.cancel();
      _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (!mounted) return;
        setState(() {
          if (_secondsLeft > 1) {
            _secondsLeft--;
          } else {
            _countdownTimer?.cancel();
            _triggerPlayNext();
          }
        });
      });
    }
  }

  void _cancelCountdown() {
    _countdownTimer?.cancel();
    setState(() {
      _showCountdown = false;
    });
  }

  void _triggerPlayNext() {
    _countdownTimer?.cancel();
    setState(() {
      _showCountdown = false;
    });
    widget.onPlayNext?.call();
  }

  void _disposeControllers() {
    _previewTimer?.cancel();
    _previewTimer = null;
    _countdownTimer?.cancel();
    _countdownTimer = null;
    _bunnyDurationTimer?.cancel();
    _bunnyDurationTimer = null;
    _videoPlayerController?.dispose();
    _chewieController?.dispose();
    _youtubePlayerController?.dispose();
    _videoPlayerController = null;
    _chewieController = null;
    _youtubePlayerController = null;
    _bunnyUrl = null;
    _error = null;
  }

  @override
  void dispose() {
    _disposeControllers();
    super.dispose();
  }

  Widget _previewEndedOverlay() {
    return AspectRatio(
      aspectRatio: 16 / 9,
      child: Container(
        color: Colors.black,
        alignment: Alignment.center,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.lock_outline, color: Colors.white, size: 40),
            const SizedBox(height: 12),
            Text(
              'Preview ended (${widget.previewMaxSeconds}s)',
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            const Text('Enroll to watch the full lesson',
                style: TextStyle(color: Colors.white70, fontSize: 13)),
          ],
        ),
      ),
    );
  }

  Widget _countdownOverlay() {
    return Container(
      color: Colors.black.withOpacity(0.85),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'UP NEXT',
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 12,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(height: 8),
            if (widget.nextVideoTitle != null)
              Text(
                widget.nextVideoTitle!,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            const SizedBox(height: 20),
            Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 60,
                  height: 60,
                  child: CircularProgressIndicator(
                    value: _secondsLeft / 5.0,
                    strokeWidth: 5,
                    valueColor: const AlwaysStoppedAnimation<Color>(Colors.orange),
                    backgroundColor: Colors.white.withOpacity(0.2),
                  ),
                ),
                Text(
                  '$_secondsLeft',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                TextButton(
                  onPressed: _cancelCountdown,
                  style: TextButton.styleFrom(
                    foregroundColor: Colors.white70,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  ),
                  child: const Text(
                    'Cancel',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: _triggerPlayNext,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.orange,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  child: const Text(
                    'Play Now',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_previewEnded) return _previewEndedOverlay();

    Widget playerWidget;

    if (_youtubePlayerController != null) {
      // YoutubePlayerBuilder lets the fullscreen button rotate the video into
      // a real horizontal view (and restore portrait + the system UI on exit).
      playerWidget = YoutubePlayerBuilder(
        onEnterFullScreen: () {
          SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
          SystemChrome.setPreferredOrientations(const [
            DeviceOrientation.landscapeLeft,
            DeviceOrientation.landscapeRight,
            DeviceOrientation.portraitUp,
            DeviceOrientation.portraitDown,
          ]);
        },
        onExitFullScreen: () {
          SystemChrome.setEnabledSystemUIMode(
            SystemUiMode.manual,
            overlays: SystemUiOverlay.values,
          );
          SystemChrome.setPreferredOrientations(const [
            DeviceOrientation.portraitUp,
          ]);
        },
        player: YoutubePlayer(
          controller: _youtubePlayerController!,
          onEnded: (metaData) {
            _onVideoEnded();
          },
        ),
        builder: (context, player) => player,
      );
    } else if (_error != null) {
      playerWidget = AspectRatio(
        aspectRatio: widget.isPortrait == true ? 9 / 16 : 16 / 9,
        child: Container(
          color: Colors.black,
          child: Center(
            child: Text(_error!,
                style: const TextStyle(color: Colors.white)),
          ),
        ),
      );
    } else if (_bunnyUrl != null) {
      final isPortraitVideo = widget.isPortrait ??
          _bunnyUrl!.toLowerCase().contains('portrait');
      playerWidget = BunnyVideoPlayerWidget(
        hlsUrl: _bunnyUrl!,
        autoPlay: _isPreview ? true : widget.autoPlay,
        isPortrait: isPortraitVideo,
        libraryId:
            BunnyVideo.extractLibraryId(_bunnyUrl) ?? AppConfig.bunnyLibraryId,
        onEnded: _onVideoEnded,
      );
    } else if (_chewieController != null) {
      playerWidget = AspectRatio(
        aspectRatio: _chewieController!.aspectRatio ?? 16 / 9,
        child: Chewie(controller: _chewieController!),
      );
    } else {
      playerWidget = AspectRatio(
        aspectRatio: widget.isPortrait == true ? 9 / 16 : 16 / 9,
        child: const ColoredBox(
          color: Colors.black,
          child: Center(child: CircularProgressIndicator()),
        ),
      );
    }

    if (_showCountdown) {
      // Calculate aspect ratio for the overlay container.
      double aspectRatio = 16 / 9;
      if (_chewieController?.aspectRatio != null) {
        aspectRatio = _chewieController!.aspectRatio!;
      } else if (widget.isPortrait == true) {
        aspectRatio = 9 / 16;
      } else if (_bunnyUrl != null &&
          (widget.isPortrait == true || _bunnyUrl!.toLowerCase().contains('portrait'))) {
        aspectRatio = 9 / 16;
      }

      return AspectRatio(
        aspectRatio: aspectRatio,
        child: Stack(
          fit: StackFit.expand,
          children: [
            playerWidget,
            Positioned.fill(child: _countdownOverlay()),
          ],
        ),
      );
    }

    return playerWidget;
  }
}
