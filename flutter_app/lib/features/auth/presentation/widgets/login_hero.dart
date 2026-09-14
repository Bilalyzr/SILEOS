// lib/features/auth/presentation/widgets/login_hero.dart
//
// Login hero: a movable 3D Sasha character standing in front of the scene
// background, with a wave-shaped bottom edge that transitions into the white
// login sheet below. Implements the "Login Page → Hero Section" spec in
// issues/design.md (wave bottom transition + running 3D model + orange/white
// theme).
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:io';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// Bundled character model (byte-identical to the website's logo.glb).
const String _kCharacterModel = 'assets/models/Sasha-Character.glb';

class LoginHero extends StatefulWidget {
  const LoginHero({super.key, required this.height});

  /// Total height of the hero band (including the part the wave dips into).
  final double height;

  @override
  State<LoginHero> createState() => _LoginHeroState();
}

class _LoginHeroState extends State<LoginHero> {
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: widget.height,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // 1) Scene background ONLY — clipped with the wave so the white sheet
          //    below flows up into a gentle crest. The character is layered on
          //    top (next) instead of inside this clip, so the wave never slices
          //    off the model.
          ClipPath(
            clipper: _HeroWaveClipper(),
            child: _buildBackground(),
          ),

          // 2) The movable 3D character — intentionally OUTSIDE the clip so the
          //    full model (its base included) stays visible, standing over the
          //    wave and into the white sheet below. No orange border line.
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(
              bottom: false,
              child: kIsWeb || Platform.isAndroid || Platform.isIOS ? const ModelViewer(
                src: _kCharacterModel,
                alt: 'Sasha character — drag to move',
                // Movable: drag to orbit the camera around the model.
                cameraControls: true,
                autoRotate: false,
                disableZoom: true,
                disablePan: true,
                // No AR launch on the login screen.
                ar: false,
                // Transparent so the scene background shows through.
                backgroundColor: Colors.transparent,
                interactionPrompt: InteractionPrompt.auto,
                exposure: 1.0,
                cameraOrbit: '0deg 75deg auto',
                minCameraOrbit: 'auto 75deg auto',
                maxCameraOrbit: 'auto 75deg auto',
                scale: '0.85 0.85 0.85',
              ) : const Icon(Icons.school_rounded, size: 120, color: Colors.deepOrange),
            ),
          ),
        ],
      ),
    );
  }

  // Returned as a plain (non-Positioned) widget: it's the direct child of the
  // ClipPath above, not a Stack child. A Positioned here is illegal and renders
  // blank in release builds. The ClipPath receives the Stack's expanded
  // constraints, so BoxFit.cover fills the hero.
  Widget _buildBackground() {
    return SizedBox.expand(
      child: SvgPicture.asset(
        'assets/images/room-bg.svg',
        fit: BoxFit.cover,
        alignment: Alignment.topCenter,
      ),
    );
  }
}

/// Clips the hero with a single, smooth, symmetric crest along its bottom edge.
/// The crest peaks at the horizontal centre — directly beneath the character's
/// feet — so Sasha appears to stand *on* the curve, which then eases down to
/// both edges and flows into the white login sheet below.
class _HeroWaveClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final h = size.height;
    final w = size.width;
    // A gentle, symmetric wave that hugs the bottom — a clean base the
    // (floating) character sits above, rather than a tall hump reaching up to
    // it. `edge` = curve height at the left/right sides; `crest` = the centre
    // rise. Lower amplitude + wide eased shoulders reads as an elegant wave.
    const edge = 16.0;
    const crest = 34.0;
    final path = Path()
      ..lineTo(0, h - edge)
      // Wide, eased left shoulder flowing up into the centre.
      ..cubicTo(
        w * 0.20, h - edge,
        w * 0.38, h - crest,
        w * 0.50, h - crest,
      )
      // Symmetric right shoulder easing back down to the edge.
      ..cubicTo(
        w * 0.62, h - crest,
        w * 0.80, h - edge,
        w, h - edge,
      )
      ..lineTo(w, 0)
      ..close();
    return path;
  }

  @override
  bool shouldReclip(covariant _HeroWaveClipper oldClipper) => false;
}
