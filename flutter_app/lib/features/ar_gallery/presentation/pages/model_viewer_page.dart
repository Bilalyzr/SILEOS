// lib/features/ar_gallery/presentation/pages/model_viewer_page.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'package:url_launcher/url_launcher.dart';

/// Renders a single `.glb` model in an interactive preview, with an "About"
/// section (category, description, how-to) and a hand-off to Google Scene
/// Viewer for immersive AR. [src] is the hosted model URL.
class ModelViewerPage extends StatefulWidget {
  final String name;
  final String src;
  final bool ar;

  const ModelViewerPage({
    super.key,
    required this.name,
    required this.src,
    this.ar = true,
  });

  @override
  State<ModelViewerPage> createState() => _ModelViewerPageState();
}

class _ModelViewerPageState extends State<ModelViewerPage> {
  static const Color _accent = Color(0xFFEA580C); // brand orange

  bool _loading = true;
  Timer? _revealTimer;

  @override
  void initState() {
    super.initState();
    // model_viewer_plus gives Flutter no "loaded" callback, so lift the veil
    // after the viewer has had time to fetch + render.
    _revealTimer = Timer(const Duration(milliseconds: 2600), () {
      if (mounted) setState(() => _loading = false);
    });
  }

  @override
  void dispose() {
    _revealTimer?.cancel();
    super.dispose();
  }

  Future<void> _launchAR() async {
    final intent = 'intent://arvr.google.com/scene-viewer/1.0'
        '?file=${widget.src}'
        '&mode=ar_preferred'
        '#Intent;scheme=https;package=com.google.ar.core;action=android.intent.action.VIEW;'
        'S.browser_fallback_url=${Uri.encodeComponent(widget.src)};end;';
    try {
      if (await launchUrl(Uri.parse(intent), mode: LaunchMode.externalApplication)) {
        return;
      }
    } catch (_) {/* fall through */}
    if (!mounted) return;
    await launchUrl(Uri.parse(widget.src), mode: LaunchMode.externalApplication);
  }

  Future<void> _openInBrowser() async {
    await launchUrl(Uri.parse(widget.src), mode: LaunchMode.externalApplication);
  }

  // Lightweight categorisation derived from the model name, so each model shows
  // a meaningful tag without hand-authoring metadata for all of them.
  String get _category {
    final n = widget.name.toLowerCase();
    bool has(List<String> k) => k.any(n.contains);
    if (has(['sierpinski', 'menger', 'hilbert', 'julia', 'quaternion', 'barth', 'riemann', 'penrose', 'fractal'])) {
      return 'Fractals & Curves';
    }
    if (has(['surface', 'helicoid', 'paraboloid', 'catenoid', 'catenoide', 'minimal', 'enneper', 'dini', 'costa', 'scherk', 'boys', 'cross', 'klein', 'mobius', 'oloid', 'sphericon', 'gyroid'])) {
      return 'Surfaces';
    }
    if (has(['theorem', 'pythagorean', 'divergence', 'dot product', 'lattice', 'sine', 'sextic', 'stereomatria'])) {
      return 'Concepts';
    }
    if (has(['dodecahedron', 'octahedron', 'cube', 'pyramid', 'triangle', 'rings', 'sphere', 'snub', 'polyhedron'])) {
      return 'Geometry';
    }
    return 'Maths Model';
  }

  String get _description =>
      '${widget.name} is an interactive 3D mathematics model. Rotate, zoom and '
      'explore it from every angle in the preview above — or tap "View in AR" to '
      'place it in your real-world space using your camera.';

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final bg = isDark ? const Color(0xFF0B1120) : const Color(0xFFF2F3F7);
    final surface = isDark ? const Color(0xFF111827) : Colors.white;
    final ink = isDark ? Colors.white : const Color(0xFF1E293B);

    return Scaffold(
      backgroundColor: bg,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          tooltip: 'Back',
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        title: Text(widget.name, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            tooltip: 'View in AR',
            icon: const Icon(Icons.view_in_ar_rounded),
            onPressed: _launchAR,
          ),
        ],
      ),
      body: Column(
        children: [
          // ── Preview ───────────────────────────────────────────────────────
          Container(
            height: 320,
            margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            decoration: BoxDecoration(
              color: surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: isDark ? Colors.white10 : const Color(0x14101828)),
            ),
            clipBehavior: Clip.antiAlias,
            child: Stack(
              children: [
                Positioned.fill(
                  child: ModelViewer(
                    src: widget.src,
                    alt: '3D model of ${widget.name}',
                    ar: widget.ar,
                    autoRotate: true,
                    cameraControls: true,
                    disableZoom: false,
                    backgroundColor: surface,
                  ),
                ),
                if (_loading)
                  Positioned.fill(
                    child: Container(
                      color: surface,
                      child: Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 64,
                              height: 64,
                              decoration: BoxDecoration(color: _accent.withOpacity(0.10), shape: BoxShape.circle),
                              child: const Icon(Icons.view_in_ar_rounded, color: _accent, size: 30),
                            ),
                            const SizedBox(height: 16),
                            const SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(strokeWidth: 2.4, color: _accent),
                            ),
                            const SizedBox(height: 14),
                            Text('Loading 3D preview…',
                                style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: ink)),
                          ],
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),

          // ── About / details (scrollable) ──────────────────────────────────
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: _accent.withOpacity(0.12), borderRadius: BorderRadius.circular(20)),
                    child: Text(_category,
                        style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w700, color: _accent)),
                  ),
                  const SizedBox(height: 10),
                  Text(widget.name,
                      style: GoogleFonts.plusJakartaSans(fontSize: 21, fontWeight: FontWeight.w700, height: 1.2, color: ink)),
                  const SizedBox(height: 14),

                  // Quick detail chips.
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _chip(Icons.threed_rotation_rounded, 'Interactive 3D', ink, isDark),
                      _chip(Icons.view_in_ar_rounded, 'AR Ready', ink, isDark),
                      _chip(Icons.layers_rounded, 'GLB format', ink, isDark),
                    ],
                  ),
                  const SizedBox(height: 20),

                  _heading('About this model', ink),
                  const SizedBox(height: 6),
                  Text(_description,
                      style: GoogleFonts.inter(fontSize: 13.5, height: 1.55, color: const Color(0xFF64748B))),
                  const SizedBox(height: 20),

                  _heading('How to explore', ink),
                  const SizedBox(height: 8),
                  _howRow(Icons.threesixty_rounded, 'Drag with one finger to rotate the model.', ink),
                  _howRow(Icons.zoom_in_rounded, 'Pinch to zoom in and out for a closer look.', ink),
                  _howRow(Icons.view_in_ar_rounded, 'Tap "View in AR" to place it in your room.', ink),
                  const SizedBox(height: 22),

                  // Actions.
                  Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: ElevatedButton.icon(
                          onPressed: _launchAR,
                          icon: const Icon(Icons.view_in_ar_rounded, size: 18),
                          label: const Text('View in AR'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _accent,
                            foregroundColor: Colors.white,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            textStyle: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w700),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _openInBrowser,
                          icon: const Icon(Icons.open_in_new_rounded, size: 16),
                          label: const Text('Web'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: _accent,
                            side: BorderSide(color: _accent.withOpacity(0.4)),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            textStyle: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w700),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _heading(String text, Color ink) => Text(
        text,
        style: GoogleFonts.plusJakartaSans(fontSize: 15.5, fontWeight: FontWeight.w600, color: ink),
      );

  Widget _chip(IconData icon, String label, Color ink, bool isDark) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        decoration: BoxDecoration(
          color: isDark ? Colors.white10 : const Color(0xFFEEF1F6),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: _accent),
            const SizedBox(width: 6),
            Text(label, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: ink.withOpacity(0.8))),
          ],
        ),
      );

  Widget _howRow(IconData icon, String text, Color ink) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(color: _accent.withOpacity(0.10), borderRadius: BorderRadius.circular(9)),
              child: Icon(icon, size: 16, color: _accent),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(top: 5),
                child: Text(text, style: GoogleFonts.inter(fontSize: 13, height: 1.4, color: ink.withOpacity(0.85))),
              ),
            ),
          ],
        ),
      );
}
