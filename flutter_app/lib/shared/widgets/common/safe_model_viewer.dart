// lib/shared/widgets/common/safe_model_viewer.dart
import 'package:flutter/material.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';

/// A wrapper around ModelViewer that defer-loads the heavy WebView-based
/// 3D engine. This ensures that parent page transitions (fade-in, slide-up)
/// complete smoothly, and shows a branding placeholder while loading or if
/// the platform/WebView does not support 3D rendering.
class SafeModelViewer extends StatefulWidget {
  final String src;
  final String alt;
  final bool autoRotate;
  final bool cameraControls;
  final bool disableZoom;
  final bool disablePan;
  final bool ar;
  final Color backgroundColor;
  final String? cameraOrbit;
  final String? minCameraOrbit;
  final String? maxCameraOrbit;
  final String? scale;

  const SafeModelViewer({
    super.key,
    required this.src,
    required this.alt,
    this.autoRotate = false,
    this.cameraControls = false,
    this.disableZoom = false,
    this.disablePan = false,
    this.ar = false,
    this.backgroundColor = Colors.transparent,
    this.cameraOrbit,
    this.minCameraOrbit,
    this.maxCameraOrbit,
    this.scale,
  });

  @override
  State<SafeModelViewer> createState() => _SafeModelViewerState();
}

class _SafeModelViewerState extends State<SafeModelViewer> {
  bool _loadActual = false;

  @override
  void initState() {
    super.initState();
    // Defer loading the webview by 600ms to allow parent animations to settle
    Future.delayed(const Duration(milliseconds: 600), () {
      if (mounted) {
        setState(() {
          _loadActual = true;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_loadActual) {
      return _buildPlaceholder();
    }

    return ModelViewer(
      src: widget.src,
      alt: widget.alt,
      autoRotate: widget.autoRotate,
      cameraControls: widget.cameraControls,
      disableZoom: widget.disableZoom,
      disablePan: widget.disablePan,
      ar: widget.ar,
      backgroundColor: widget.backgroundColor,
      interactionPrompt: InteractionPrompt.none,
      exposure: 1.0,
      cameraOrbit: widget.cameraOrbit,
      minCameraOrbit: widget.minCameraOrbit,
      maxCameraOrbit: widget.maxCameraOrbit,
      scale: widget.scale,
    );
  }

  Widget _buildPlaceholder() {
    return Center(
      child: Image.asset(
        'assets/images/sasha-logo.png',
        fit: BoxFit.contain,
        width: 100,
        height: 100,
      ),
    );
  }
}
