// lib/config/design_tokens.dart
//
// Central design tokens for the "Professional / Production" visual language —
// the Stripe · Notion · HubSpot feeling: orange + white + slate-gray, generous
// whitespace, hairline borders and whisper-soft shadows (never glow). Gradients,
// shadows, neutrals, spacing and corner radii live here so every screen and
// shared widget pulls from one source of truth. Brand colours stay in
// [AppTheme] (theme.dart); this file composes them into reusable effects.
import 'package:flutter/material.dart';
import 'theme.dart';

/// Slate-gray neutral ramp — the professional backbone of the UI. Orange is the
/// accent; slate carries surfaces, borders, dividers and muted text.
class AppNeutrals {
  AppNeutrals._();

  // Light surfaces & lines
  static const Color slate50 = Color(0xFFF8FAFC); // app section backgrounds
  static const Color slate100 = Color(0xFFF1F5F9); // subtle fills / chips
  static const Color slate200 = Color(0xFFE9EDF2); // hairline card borders
  static const Color slate300 = Color(0xFFCBD5E1); // dividers / disabled
  static const Color slate400 = Color(0xFF94A3B8); // placeholder / faint text
  static const Color slate500 = Color(0xFF64748B); // muted body text
  static const Color slate600 = Color(0xFF475569); // secondary text
  static const Color slate700 = Color(0xFF334155); // strong body text
  static const Color slate800 = Color(0xFF1E293B); // dark surfaces
  static const Color slate900 = Color(0xFF0F172A); // headings / ink

  // Dark-mode lines
  static const Color borderDark = Color(0xFF24303F);
  static const Color surfaceDarkRaised = Color(0xFF202A38);
}

/// Reusable gradients. Used sparingly — professional layouts lead with solid
/// fills and reserve gradients for the occasional hero / banner surface.
class AppGradients {
  AppGradients._();

  /// Primary brand sweep — restrained, for hero banners and feature surfaces.
  static const LinearGradient primary = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFB923C), AppTheme.primary, AppTheme.primaryDark],
    stops: [0.0, 0.55, 1.0],
  );

  /// Deep slate/blue sweep for premium or AR-style hero panels.
  static const LinearGradient deep = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [AppTheme.secondary, Color(0xFF075985)],
  );

  /// Whisper-soft warm tint used behind hero sections on light backgrounds.
  static const LinearGradient subtle = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFFFFF8F1), Color(0xFFFFFFFF)],
  );

  /// Neutral slate wash for section/banner backgrounds that should stay calm.
  static const LinearGradient surface = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [AppNeutrals.slate50, Color(0xFFFFFFFF)],
  );

  /// Legacy alias (was a hot orange→red sweep). Now a calm single-hue orange
  /// so existing call-sites read as professional accents, not "energetic".
  static const LinearGradient fire = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [Color(0xFFFB923C), AppTheme.primary],
  );
}

/// Elevation as soft, near-neutral shadows. Spec: blur ~20, opacity ~0.05.
/// No coloured glow — depth comes from a hairline border + a faint drop.
class AppShadows {
  AppShadows._();

  /// Resting card elevation — the default for [AppCard].
  static List<BoxShadow> get card => [
        BoxShadow(
          color: const Color(0xFF0F172A).withOpacity(0.05),
          blurRadius: 20,
          offset: const Offset(0, 8),
        ),
      ];

  /// Lighter elevation for compact / inline surfaces (chips, list rows).
  static List<BoxShadow> get soft => [
        BoxShadow(
          color: const Color(0xFF0F172A).withOpacity(0.04),
          blurRadius: 12,
          offset: const Offset(0, 4),
        ),
      ];

  /// Raised / pressed-hover card — still subtle, just a touch deeper.
  static List<BoxShadow> get cardRaised => [
        BoxShadow(
          color: const Color(0xFF0F172A).withOpacity(0.08),
          blurRadius: 28,
          offset: const Offset(0, 14),
        ),
      ];

  /// A restrained tint beneath primary buttons — a hint of lift, not a glow.
  static List<BoxShadow> get primarySoft => [
        BoxShadow(
          color: AppTheme.primary.withOpacity(0.22),
          blurRadius: 16,
          offset: const Offset(0, 8),
        ),
      ];

  /// Legacy alias for the old orange "glow" — now the restrained [primarySoft].
  static List<BoxShadow> get primaryGlow => primarySoft;
}

/// 4-pt spacing scale. Use these instead of magic numbers for consistency.
/// Spec: section spacing 24, card padding 20.
class AppSpacing {
  AppSpacing._();
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double card = 20; // standard card inner padding
  static const double section = 24; // gap between sections
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;

  /// Standard horizontal page padding.
  static const EdgeInsets page = EdgeInsets.symmetric(horizontal: 20);
}

/// Corner radii. Professional but generous. Spec: cards 28, banner bottom 32.
class AppRadius {
  AppRadius._();
  static const double sm = 10;
  static const double md = 14; // buttons / inputs
  static const double lg = 20; // compact cards / sheets
  static const double card = 28; // standard card radius (design spec)
  static const double banner = 32; // cover/banner bottom corners
  static const double pill = 999;

  /// Legacy alias — `xl` previously meant the largest card radius (now [card]).
  static const double xl = card;

  static BorderRadius get smAll => BorderRadius.circular(sm);
  static BorderRadius get mdAll => BorderRadius.circular(md);
  static BorderRadius get lgAll => BorderRadius.circular(lg);
  static BorderRadius get cardAll => BorderRadius.circular(card);
  static BorderRadius get xlAll => BorderRadius.circular(xl);
}
