import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:sashalms/config/app_config.dart';
import 'package:sashalms/config/theme.dart';
import 'model_viewer_page.dart';

// ── Palette (cool & calm, matching the dashboard) ──────────────────────────
const Color _bg = Color(0xFFF2F5FB);
const Color _ink = Color(0xFF1E293B);
const Color _textSecondary = Color(0xFF64748B);
const Color _textTertiary = Color(0xFF94A3B8);
const Color _indigo = Color(0xFF4F46E5);
const Color _violet = Color(0xFF7C3AED);
const Color _blue = Color(0xFF2563EB);
const Color _cyan = Color(0xFF0EA5C4);
const Color _green = Color(0xFF15803D);

class ArModel {
  final String name;
  final String file;

  const ArModel({required this.name, required this.file});
}

class ArGalleryPage extends StatefulWidget {
  const ArGalleryPage({super.key});

  @override
  State<ArGalleryPage> createState() => _ArGalleryPageState();
}

class _ArGalleryPageState extends State<ArGalleryPage> {
  final List<ArModel> _allModels = const [
    ArModel(name: "Rough Work (Interactive VR Demo)", file: "Rough-Work-For-Website.glb"),
    ArModel(name: "Pythagorean Theorem", file: "Pythagorean-Theorem-Animated-For-Website-Done.glb"),
    ArModel(name: "Rhombic Dodecahedron", file: "Rhombic-Dodecahedron-Animated-For-Website-Done.glb"),
    ArModel(name: "Pascal Pyramid", file: "pascals_pyramid.glb"),
    ArModel(name: "Ordinary Helicoid", file: "ordinary_helicoid.glb"),
    ArModel(name: "Hyperboloid", file: "hyperboloid.glb"),
    ArModel(name: "Hyperbolic Paraboloid", file: "hypar_approximately.glb"),
    ArModel(name: "Extruded Sine Waves", file: "extruded_sine_waves_inside_a_cuboid.glb"),
    ArModel(name: "Catenoide", file: "catenoide.glb"),
    ArModel(name: "3D Lattice", file: "3d_lattice.glb"),
    ArModel(name: "Stereomatria", file: "stereomatria.glb"),
    ArModel(name: "Sierpinski Triangle", file: "Sierpinski-Animation-For-Website-Done.glb"),
    ArModel(name: "Saddle Wires", file: "saddle_wires.glb"),
    ArModel(name: "Catenoid", file: "catenoid.glb"),
    ArModel(name: "Menger Sponge", file: "menger_sponge.glb"),
    ArModel(name: "Boys Surface", file: "boys_surface.glb"),
    ArModel(name: "Borromean Rings", file: "borromean_rings.glb"),
    ArModel(name: "3D Hilbert Curve", file: "3d_hilbert_curve_3rd_iteration.glb"),
    ArModel(name: "Snub Cube", file: "snub_cube.glb"),
    ArModel(name: "Scherks Minimal Surface", file: "scherks_minimal_surface_scherk.glb"),
    ArModel(name: "Penrose Triangle", file: "penrose_triangle-large.glb"),
    ArModel(name: "Octahedron", file: "octahedron.glb"),
    ArModel(name: "Klein Bottle", file: "klein_bottle_2.glb"),
    ArModel(name: "Julia Quaternion", file: "julia_quaternion.glb"),
    ArModel(name: "Gyroid", file: "gyroid.glb"),
    ArModel(name: "Enneper Surface", file: "enneper_surface.glb"),
    ArModel(name: "Dodecahedron", file: "dodecahedron.glb"),
    ArModel(name: "Mobius Strip", file: "mobius-strip-model.glb"),
    ArModel(name: "Alexander Horned Sphere", file: "Alexander-Horned-Sphere.glb"),
    ArModel(name: "Cross Cap", file: "Cross-Production-Animated-For-Website-Done.glb"),
    ArModel(name: "Oloid", file: "Oloid.glb"),
    ArModel(name: "Sphericon", file: "Sphericon.glb"),
    ArModel(name: "Costas Minimal Surface", file: "Costas-Minimal-Surface-Animation-For-Website-Done.glb"),
    ArModel(name: "Dinis Surface", file: "Dinis-Surface-Animated-For-Website-Done.glb"),
    ArModel(name: "Divergence", file: "Divergence-Animated-Animated-For-Website-Done.glb"),
    ArModel(name: "Dot Product", file: "Dot-Product-Animated-For-Website-Done.glb"),
    ArModel(name: "Barth Sextic", file: "barth-sextic-Animation-For-Website-Done.glb"),
    ArModel(name: "Riemann Surfaces", file: "Riemann-Surfaces-AAnimation-For-Website-Done.glb"),
  ];

  List<ArModel> _filteredModels = [];
  String _query = '';

  @override
  void initState() {
    super.initState();
    _filteredModels = _allModels;
  }

  void _onSearchChanged(String query) {
    setState(() {
      _query = query;
      if (query.isEmpty) {
        _filteredModels = _allModels;
      } else {
        _filteredModels = _allModels
            .where((m) => m.name.toLowerCase().contains(query.toLowerCase()))
            .toList();
      }
    });
  }

  /// Hosted URL for a model's `.glb` file.
  String _modelUrl(ArModel model) {
    var base = AppConfig.baseUrl;
    if (base.contains(':8000')) {
      base = base.replaceAll(':8000', ':3100');
    }
    final separator = base.endsWith('/') ? '' : '/';
    return '$base${separator}models/ar/${model.file}';
  }

  String _modelBaseUrl() {
    var base = AppConfig.baseUrl;
    if (base.contains(':8000')) {
      base = base.replaceAll(':8000', ':3100');
    }
    return base.endsWith('/') ? base.substring(0, base.length - 1) : base;
  }

  /// Opens the model in the in-app 3D viewer (no browser redirect).
  void _openInAppViewer(ArModel model) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ModelViewerPage(
          name: model.name,
          src: _modelUrl(model),
        ),
      ),
    );
  }

  Future<void> _launchDirectAR(ArModel model) async {
    // Intent URL structure for Android Scene Viewer
    final urlString = 'intent://arvr.google.com/scene-viewer/1.0'
        '?file=${_modelUrl(model)}'
        '&mode=ar_only'
        '#Intent;scheme=https;package=com.google.ar.core;action=android.intent.action.VIEW;end;';
    final intentUri = Uri.parse(urlString);

    try {
      if (await launchUrl(intentUri, mode: LaunchMode.externalApplication)) {
        return;
      }
    } catch (_) {
      // If package/intent fails, fall back to browser view on website
      final base = AppConfig.baseUrl;
      final separator = base.endsWith('/') ? '' : '/';
      final webUrl = Uri.parse('$base${separator}meiporul-ar');
      await launchUrl(webUrl, mode: LaunchMode.externalApplication);
    }
  }

  // A stable accent per card so the grid reads as a calm, varied palette.
  static const List<Color> _accents = [_indigo, _blue, _violet, _cyan];
  Color _accentFor(int i) => _accents[i % _accents.length];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final surface = isDark ? const Color(0xFF1E293B) : Colors.white;
    final bg = isDark ? const Color(0xFF0B1120) : _bg;

    return Scaffold(
      backgroundColor: bg,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          // Gradient hero app bar.
          SliverAppBar(
            pinned: true,
            expandedHeight: 168,
            backgroundColor: _indigo,
            foregroundColor: Colors.white,
            elevation: 0,
            title: const Text('AR Gallery'),
            flexibleSpace: FlexibleSpaceBar(
              background: _HeroHeader(count: _allModels.length),
              collapseMode: CollapseMode.parallax,
            ),
          ),

          // Search field.
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Container(
                decoration: BoxDecoration(
                  color: surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: isDark ? Colors.white10 : const Color(0x14101828)),
                  boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.04), blurRadius: 12, offset: const Offset(0, 4))],
                ),
                child: TextField(
                  onChanged: _onSearchChanged,
                  style: GoogleFonts.inter(fontSize: 14, color: isDark ? Colors.white : _ink),
                  decoration: InputDecoration(
                    hintText: 'Search 3D models…',
                    hintStyle: GoogleFonts.inter(fontSize: 14, color: _textTertiary),
                    prefixIcon: const Icon(Icons.search_rounded, color: _indigo),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  ),
                ),
              ),
            ),
          ),

          // Result count line.
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 6, 20, 10),
              child: Text(
                _query.isEmpty
                    ? '${_filteredModels.length} interactive models'
                    : '${_filteredModels.length} result${_filteredModels.length == 1 ? '' : 's'} for "$_query"',
                style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.w600, color: _textSecondary),
              ),
            ),
          ),

          if (_filteredModels.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: Padding(
                padding: const EdgeInsets.all(40),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.search_off_rounded, size: 44, color: _textTertiary),
                    const SizedBox(height: 12),
                    Text('No models match your search.',
                        style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: isDark ? Colors.white : _ink)),
                    const SizedBox(height: 4),
                    Text('Try a different keyword.',
                        style: GoogleFonts.inter(fontSize: 12.5, color: _textSecondary)),
                  ],
                ),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              sliver: SliverGrid(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 0.78,
                ),
                delegate: SliverChildBuilderDelegate(
                  (context, index) => _ModelCard(
                    key: ValueKey(_filteredModels[index].file),
                    model: _filteredModels[index],
                    src: _modelUrl(_filteredModels[index]),
                    accent: _accentFor(index),
                    surface: surface,
                    isDark: isDark,
                    onView3D: () => _openInAppViewer(_filteredModels[index]),
                    onViewAR: () => _launchDirectAR(_filteredModels[index]),
                  ),
                  childCount: _filteredModels.length,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// Gradient header shown in the collapsing app bar.
class _HeroHeader extends StatelessWidget {
  final int count;
  const _HeroHeader({required this.count});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [_indigo, _violet, _blue],
        ),
      ),
      child: Stack(
        children: [
          Positioned(right: -30, top: -20, child: _glow(120, Colors.white.withOpacity(0.14))),
          Positioned(right: 50, bottom: -40, child: _glow(96, Colors.white.withOpacity(0.10))),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 56, 20, 18),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(13),
                          border: Border.all(color: Colors.white.withOpacity(0.25)),
                        ),
                        child: const Icon(Icons.view_in_ar_rounded, color: Colors.white, size: 24),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Meiporul AR Gallery',
                                style: GoogleFonts.plusJakartaSans(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w800, letterSpacing: -0.3)),
                            const SizedBox(height: 2),
                            Text('$count interactive 3D maths models · view in 3D or AR',
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: GoogleFonts.inter(color: Colors.white.withOpacity(0.9), fontSize: 12, height: 1.4)),
                          ],
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

  static Widget _glow(double size, Color color) =>
      Container(width: size, height: size, decoration: BoxDecoration(color: color, shape: BoxShape.circle));
}

class _ModelCard extends StatelessWidget {
  final ArModel model;
  final String src;
  final Color accent;
  final Color surface;
  final bool isDark;
  final VoidCallback onView3D;
  final VoidCallback onViewAR;

  const _ModelCard({
    super.key,
    required this.model,
    required this.src,
    required this.accent,
    required this.surface,
    required this.isDark,
    required this.onView3D,
    required this.onViewAR,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onView3D,
      child: Container(
        decoration: BoxDecoration(
          color: surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: isDark ? Colors.white10 : const Color(0x14101828)),
          boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.05), blurRadius: 14, offset: const Offset(0, 6))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Preview area: a live, auto-rotating 3D model on a tinted wash,
            // with the "AR Ready" chip. Interaction is suppressed so a tap on
            // the card opens the full viewer instead of orbiting the model.
            Expanded(
              child: Container(
                clipBehavior: Clip.antiAlias,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [accent.withOpacity(isDark ? 0.30 : 0.14), accent.withOpacity(isDark ? 0.12 : 0.05)],
                  ),
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(18)),
                ),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    _thumbnailWidget(model, accent),
                    Positioned(
                      top: 10,
                      right: 10,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: _green.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.bolt_rounded, size: 11, color: _green),
                            const SizedBox(width: 2),
                            Text('AR Ready', style: GoogleFonts.inter(fontSize: 9, fontWeight: FontWeight.w700, color: _green)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(11),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    model.name,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 12.5, height: 1.25, color: isDark ? Colors.white : _ink),
                  ),
                  const SizedBox(height: 9),
                  Row(
                    children: [
                      Expanded(
                        child: _SmallButton(
                          label: 'View 3D',
                          icon: Icons.threed_rotation_rounded,
                          filled: true,
                          accent: accent,
                          onTap: onView3D,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: _SmallButton(
                          label: 'AR',
                          icon: Icons.view_in_ar_rounded,
                          filled: false,
                          accent: accent,
                          onTap: onViewAR,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _thumbnailWidget(ArModel model, Color accent) {
    final fileName = model.file.replaceAll('.glb', '');
    final localThumbnails = {
      '3d_hilbert_curve_3rd_iteration',
      '3d_lattice',
      'Alexander-Horned-Sphere',
      'barth-sextic-Animation-For-Website-Done',
      'borromean_rings'
    };

    if (localThumbnails.contains(fileName)) {
      return Image.asset(
        'assets/models/ar_thumbnails/$fileName.webp',
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => _defaultThumbnail(accent),
      );
    }

    var base = AppConfig.baseUrl;
    if (base.contains(':8000')) {
      base = base.replaceAll(':8000', ':3100');
    }
    final cleanBase = base.endsWith('/') ? base.substring(0, base.length - 1) : base;
    final networkUrl = '$cleanBase/models/ar_thumbnails/$fileName.jpg';

    return CachedNetworkImage(
      imageUrl: networkUrl,
      fit: BoxFit.cover,
      placeholder: (context, url) => _defaultThumbnail(accent),
      errorWidget: (context, url, error) => _defaultThumbnail(accent),
    );
  }

  Widget _defaultThumbnail(Color accent) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.all(16),
      child: Center(
        child: Image.asset(
          'assets/images/sasha-logo.png',
          fit: BoxFit.contain,
        ),
      ),
    );
  }
}

class _SmallButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool filled;
  final Color accent;
  final VoidCallback onTap;

  const _SmallButton({required this.label, required this.icon, required this.filled, required this.accent, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(9),
      child: Container(
        height: 32,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: filled ? accent : accent.withOpacity(0.10),
          borderRadius: BorderRadius.circular(9),
          border: filled ? null : Border.all(color: accent.withOpacity(0.35)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 13, color: filled ? Colors.white : accent),
            const SizedBox(width: 4),
            Text(label, style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w700, color: filled ? Colors.white : accent)),
          ],
        ),
      ),
    );
  }
}
