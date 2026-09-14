import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:sashalms/config/theme.dart';
import 'package:sashalms/features/courses/presentation/providers/course_filter_providers.dart';
import 'package:sashalms/features/internships/presentation/pages/internships_page.dart';
import 'package:sashalms/features/ar_gallery/presentation/pages/ar_gallery_page.dart';
import 'package:sashalms/features/companies/presentation/pages/for_companies_page.dart';

/// Stagger Testimonials hero — the hover.dev "Stagger Testimonials" carousel
/// (www.hover.dev/components/carousels) repurposed as the home promo deck.
///
/// The deck is a row of large chamfered cards carrying the app's hero promos
/// (AR/VR learning, Learn With Sasha, Internships, …). The centre card is raised
/// and painted in the brand primary; its CTA navigates. Neighbours sit lower,
/// alternate a small ±2.5° tilt and carry a coloured corner accent. The deck
/// auto-advances every [_autoplay] (5s); tapping a side card or a nav arrow
/// re-centres it and resets the timer.
class StaggerTestimonialsHero extends ConsumerStatefulWidget {
  const StaggerTestimonialsHero({super.key});

  @override
  ConsumerState<StaggerTestimonialsHero> createState() =>
      _StaggerTestimonialsHeroState();
}

/// A single promo slide. [onTap] runs when its card is the centre one.
class _Slide {
  const _Slide({
    required this.badge,
    required this.badgeIcon,
    required this.title,
    required this.desc,
    required this.cta,
    required this.accent,
    required this.onTap,
  });

  final String badge;
  final IconData badgeIcon;
  final String title;
  final String desc;
  final String cta;
  final Color accent;
  final VoidCallback onTap;
}

const Duration _autoplay = Duration(seconds: 5);
const Duration _transition = Duration(milliseconds: 500);

class _StaggerTestimonialsHeroState
    extends ConsumerState<StaggerTestimonialsHero> {
  int _center = 0;
  Timer? _timer;
  int _count = 0;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(_autoplay, (_) => _advance(1));
  }

  void _advance(int steps) {
    if (steps == 0 || _count == 0) return;
    setState(() => _center = (_center + steps) % _count);
    _startTimer(); // reset the 5s window after any move
  }

  /// Signed ring distance of card [i] from the current centre.
  int _position(int i) {
    final half = _count ~/ 2;
    return ((i - _center + _count + half) % _count) - half;
  }

  /// The promo slides — content carried over from the previous hero slides,
  /// plus the Internships card. Built per-frame so the tap callbacks can close
  /// over [context]/[ref].
  List<_Slide> _slides() => [
        _Slide(
          badge: 'AR/VR TECH LEARNING',
          badgeIcon: Icons.threed_rotation,
          title: 'Transform Education with AR/VR Innovation',
          desc:
              'Experience mathematics in cutting-edge Augmented & Virtual Reality. Visualize complex concepts in immersive 3D.',
          cta: 'Explore Programs',
          accent: AppTheme.primary,
          onTap: () => ref.read(scaffoldTabProvider.notifier).state = 1,
        ),
        _Slide(
          badge: 'CAREER LAUNCH',
          badgeIcon: Icons.work_outline,
          title: 'Internships & Opportunities',
          desc:
              'Apply for hands-on internships and real project experience that make your résumé genuinely stand out.',
          cta: 'View Internships',
          accent: AppTheme.info,
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const InternshipsPage()),
          ),
        ),
        _Slide(
          badge: 'IMMERSIVE 3D',
          badgeIcon: Icons.view_in_ar_outlined,
          title: 'Explore the AR Gallery',
          desc:
              'Browse 100+ interactive 3D AR models you can rotate, scale and explore right from your phone.',
          cta: 'Open Gallery',
          accent: const Color(0xFFF97316),
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const ArGalleryPage()),
          ),
        ),
        _Slide(
          badge: 'FOR COMPANIES',
          badgeIcon: Icons.business_center_outlined,
          title: 'Hire Skilled Graduates',
          desc:
              'Partner with SashaInfinity to recruit job-ready graduates trained on modern, practical skills.',
          cta: 'Learn More',
          accent: Colors.indigo,
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const ForCompaniesPage()),
          ),
        ),
      ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final slides = _slides();
    _count = slides.length;

    return LayoutBuilder(
      builder: (context, constraints) {
        final maxW = constraints.maxWidth;
        // Slightly more compact promo card.
        final cardW = math.min(maxW * 0.76, 320.0);
        final cardH = cardW * 1.12;
        final centerLeft = (maxW - cardW) / 2;
        final stepX = cardW * 0.9; // sideways step per neighbour
        const neutralTop = 70.0; // baseline the side cards rest on

        // Build cards back-to-front so the centre card paints on top.
        final indices = List<int>.generate(_count, (i) => i)
          ..sort((a, b) => _position(b).abs().compareTo(_position(a).abs()));

        final cards = <Widget>[];
        for (final i in indices) {
          final pos = _position(i);
          final absPos = pos.abs();
          if (absPos > 2) continue; // off the ring — skip

          final isCenter = pos == 0;
          final dy = isCenter
              ? -72.0
              : pos.isOdd
                  ? 16.0
                  : -16.0;
          final angle = isCenter
              ? 0.0
              : (pos.isOdd ? 2.5 : -2.5) * math.pi / 180;
          // |pos|==2 stays mounted off-screen (opacity 0) as the staging slot
          // so the wrap-around advance animates smoothly.
          final opacity = absPos <= 1 ? 1.0 : 0.0;
          final left = centerLeft + stepX * pos;
          final top = neutralTop + dy;

          cards.add(
            AnimatedPositioned(
              key: ValueKey(i),
              duration: _transition,
              curve: Curves.easeInOut,
              left: left,
              top: top,
              width: cardW,
              height: cardH,
              child: AnimatedOpacity(
                duration: _transition,
                opacity: opacity,
                child: AnimatedRotation(
                  duration: _transition,
                  curve: Curves.easeInOut,
                  turns: angle / (2 * math.pi),
                  child: _card(slides[i], isCenter, isDark, pos),
                ),
              ),
            ),
          );
        }

        return Column(
          children: [
            SizedBox(
              height: cardH + 110,
              width: maxW,
              child: Stack(
                clipBehavior: Clip.none,
                children: cards,
              ),
            ),
            const SizedBox(height: 6),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _navButton(Icons.chevron_left, 'Previous slide',
                    () => _advance(-1), isDark, filled: false),
                const SizedBox(width: 12),
                _navButton(Icons.chevron_right, 'Next slide',
                    () => _advance(1), isDark, filled: true),
              ],
            ),
          ],
        );
      },
    );
  }

  Widget _card(_Slide s, bool isCenter, bool isDark, int pos) {
    final cardBg = isCenter
        ? AppTheme.primary
        : (isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight);
    final borderColor = isCenter
        ? AppTheme.primary
        : (isDark ? AppTheme.borderDark : AppTheme.borderLight);
    final titleColor =
        isCenter ? Colors.white : (isDark ? AppTheme.textDark : AppTheme.textLight);
    final descColor = isCenter
        ? Colors.white.withOpacity(0.92)
        : (isDark ? AppTheme.mutedDark : AppTheme.mutedLight);
    final accent = isCenter ? Colors.white : s.accent;

    final shape = _ChamferBorder(
      cut: 30,
      side: BorderSide(color: borderColor, width: 1.5),
    );

    return GestureDetector(
      // Centre card runs its action; side cards re-centre themselves.
      onTap: () => isCenter ? s.onTap() : _advance(pos),
      child: Container(
        decoration: ShapeDecoration(
          color: cardBg,
          shape: shape,
          shadows: [
            BoxShadow(
              color: isCenter
                  ? AppTheme.primary.withOpacity(0.35)
                  : Colors.black.withOpacity(isDark ? 0.4 : 0.08),
              blurRadius: isCenter ? 28 : 14,
              offset: Offset(0, isCenter ? 16 : 8),
            ),
          ],
        ),
        child: ClipPath(
          clipper: ShapeBorderClipper(shape: shape),
          child: Stack(
            children: [
              // Coloured corner accent peeking through the chamfered top-left
              // corner (hover.dev's signature diagonal tab) — side cards only.
              if (!isCenter)
                Positioned(
                  top: -34,
                  left: -34,
                  child: Transform.rotate(
                    angle: math.pi / 4,
                    child: Container(
                      width: 78,
                      height: 78,
                      color: s.accent.withOpacity(isDark ? 0.55 : 0.85),
                    ),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 26, 24, 22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Badge pill
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 7),
                      decoration: BoxDecoration(
                        color: isCenter
                            ? Colors.white.withOpacity(0.2)
                            : s.accent.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(s.badgeIcon, size: 15, color: accent),
                          const SizedBox(width: 7),
                          Text(
                            s.badge,
                            style: GoogleFonts.plusJakartaSans(
                              color: accent,
                              fontSize: 11.5,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.0,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      s.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        height: 1.15,
                        color: titleColor,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: Text(
                        s.desc,
                        maxLines: 4,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.justify,
                        style: GoogleFonts.inter(
                          fontSize: 14.5,
                          height: 1.45,
                          fontWeight: FontWeight.w500,
                          color: descColor,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    // CTA row
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          s.cta,
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            color: accent,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Icon(Icons.arrow_forward_rounded, size: 17, color: accent),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _navButton(IconData icon, String semantic, VoidCallback onTap,
      bool isDark,
      {required bool filled}) {
    final bg = filled
        ? AppTheme.primary
        : (isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight);
    final fg = filled
        ? Colors.white
        : (isDark ? AppTheme.textDark : AppTheme.textLight);
    return Semantics(
      button: true,
      label: semantic,
      child: Material(
        color: bg,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: filled
              ? BorderSide.none
              : BorderSide(
                  color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
                  width: 1.5),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: onTap,
          child: SizedBox(
            width: 50,
            height: 50,
            child: Icon(icon, size: 26, color: fg),
          ),
        ),
      ),
    );
  }
}

/// A rectangle border with the two top corners chamfered (45° cut) — the
/// octagon-ish silhouette used by the hover.dev stagger cards. Used as a
/// [ShapeDecoration] shape so it fills, borders and clips in one go.
class _ChamferBorder extends ShapeBorder {
  const _ChamferBorder({required this.cut, this.side = BorderSide.none});

  final double cut;
  final BorderSide side;

  @override
  EdgeInsetsGeometry get dimensions => EdgeInsets.all(side.width);

  Path _build(Rect r) {
    return Path()
      ..moveTo(r.left + cut, r.top)
      ..lineTo(r.right - cut, r.top)
      ..lineTo(r.right, r.top + cut)
      ..lineTo(r.right, r.bottom)
      ..lineTo(r.left, r.bottom)
      ..lineTo(r.left, r.top + cut)
      ..close();
  }

  @override
  Path getOuterPath(Rect rect, {TextDirection? textDirection}) => _build(rect);

  @override
  Path getInnerPath(Rect rect, {TextDirection? textDirection}) =>
      _build(rect.deflate(side.width));

  @override
  void paint(Canvas canvas, Rect rect, {TextDirection? textDirection}) {
    if (side.style == BorderStyle.none) return;
    canvas.drawPath(_build(rect.deflate(side.width / 2)), side.toPaint());
  }

  @override
  ShapeBorder scale(double t) =>
      _ChamferBorder(cut: cut * t, side: side.scale(t));

  @override
  bool operator ==(Object other) =>
      other is _ChamferBorder && other.cut == cut && other.side == side;

  @override
  int get hashCode => Object.hash(cut, side);
}
