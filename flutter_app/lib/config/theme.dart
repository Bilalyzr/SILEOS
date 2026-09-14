import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Brand Colors from Tailwind Config
  static const Color primary = Color(0xFFF97316); // Orange-500
  static const Color primaryDark = Color(0xFFEA580C); // Orange-600
  static const Color secondary = Color(0xFF0C4A6E); // Dark Blue (secondary-900)
  
  // Semantic Colors
  static const Color success = Color(0xFF22C55E);
  static const Color warning = Color(0xFFEAB308);
  static const Color danger = Color(0xFFEF4444);
  static const Color info = Color(0xFF0EA5E9);

  // Neutral Colors — slate-gray backbone (see AppNeutrals in design_tokens.dart)
  static const Color backgroundLight = Color(0xFFFFFFFF);
  static const Color backgroundDark = Color(0xFF0B1118); // near-slate-950
  static const Color surfaceLight = Color(0xFFF8FAFC); // Slate-50
  static const Color surfaceDark = Color(0xFF161E2A); // slate-900-ish card
  static const Color textLight = Color(0xFF0F172A); // Slate-900
  static const Color textDark = Color(0xFFF8FAFC); // Slate-50
  static const Color mutedLight = Color(0xFF64748B); // Slate-500 muted text
  static const Color mutedDark = Color(0xFF94A3B8); // Slate-400 muted text
  static const Color borderLight = Color(0xFFE9EDF2); // hairline card border
  static const Color borderDark = Color(0xFF24303F); // hairline (dark)

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: const ColorScheme(
        brightness: Brightness.light,
        primary: primary,
        onPrimary: Colors.white,
        secondary: secondary,
        onSecondary: Colors.white,
        error: danger,
        onError: Colors.white,
        surface: backgroundLight,
        onSurface: textLight,
      ),
      scaffoldBackgroundColor: backgroundLight,
      textTheme: _buildTextTheme(Brightness.light),
      appBarTheme: AppBarTheme(
        backgroundColor: backgroundLight,
        foregroundColor: textLight,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          color: textLight,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      navigationBarTheme: _navBarTheme(Brightness.light),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          elevation: 0,
          textStyle: GoogleFonts.inter(
            fontSize: 15.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          textStyle: GoogleFonts.inter(
            fontSize: 15.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          side: const BorderSide(color: primary, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          textStyle: GoogleFonts.inter(
            fontSize: 15.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: backgroundLight,
        elevation: 0,
        shadowColor: const Color(0xFF0F172A).withOpacity(0.05),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(28),
          side: const BorderSide(color: borderLight, width: 1),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: const Color(0xFFF1F5F9), // slate-100, neutral default
        labelStyle: GoogleFonts.inter(
          fontWeight: FontWeight.w600,
          fontSize: 13,
          color: const Color(0xFF334155), // slate-700
        ),
        side: const BorderSide(color: borderLight, width: 1),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceLight,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: danger),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
    );
  }

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme(
        brightness: Brightness.dark,
        primary: primary,
        onPrimary: Colors.white,
        secondary: secondary,
        onSecondary: Colors.white,
        error: danger,
        onError: Colors.white,
        surface: backgroundDark,
        onSurface: textDark,
      ),
      scaffoldBackgroundColor: backgroundDark,
      textTheme: _buildTextTheme(Brightness.dark),
      appBarTheme: AppBarTheme(
        backgroundColor: backgroundDark,
        foregroundColor: textDark,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          color: textDark,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      navigationBarTheme: _navBarTheme(Brightness.dark),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          elevation: 0,
          textStyle: GoogleFonts.inter(
            fontSize: 15.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          textStyle: GoogleFonts.inter(
            fontSize: 15.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          side: const BorderSide(color: primary, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          textStyle: GoogleFonts.inter(
            fontSize: 15.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.1,
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: surfaceDark,
        elevation: 0,
        shadowColor: Colors.black.withOpacity(0.3),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(28),
          side: const BorderSide(color: borderDark, width: 1),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: const Color(0xFF1E293B), // slate-800, neutral default
        labelStyle: GoogleFonts.inter(
          fontWeight: FontWeight.w600,
          fontSize: 13,
          color: const Color(0xFFCBD5E1), // slate-300
        ),
        side: const BorderSide(color: borderDark, width: 1),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceDark,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFF475569)), // slate-600
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFF475569)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: danger),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
    );
  }

  /// Professional bottom navigation: a soft orange tint behind the selected
  /// destination, hairline top divider, calm 24px icons.
  static NavigationBarThemeData _navBarTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    return NavigationBarThemeData(
      height: 70,
      elevation: 0,
      backgroundColor: isDark ? backgroundDark : backgroundLight,
      indicatorColor: primary.withOpacity(0.10),
      indicatorShape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
      iconTheme: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return IconThemeData(
          size: 24,
          color: selected
              ? primary
              : (isDark ? mutedDark : mutedLight),
        );
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return GoogleFonts.inter(
          fontSize: 12,
          fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
          letterSpacing: 0.1,
          color: selected ? primary : (isDark ? mutedDark : mutedLight),
        );
      }),
    );
  }

  static TextTheme _buildTextTheme(Brightness brightness) {
    final baseColor = brightness == Brightness.dark ? textDark : textLight;
    
    // Base Inter theme
    final interTheme = GoogleFonts.interTextTheme().apply(
      bodyColor: baseColor,
      displayColor: baseColor,
    );

    // Override headings with Space Grotesk
    return interTheme.copyWith(
      displayLarge: GoogleFonts.plusJakartaSans(
        fontSize: 54,
        fontWeight: FontWeight.w700,
        letterSpacing: -1.2,
        height: 1.06,
        color: baseColor,
      ),
      displayMedium: GoogleFonts.plusJakartaSans(
        fontSize: 44,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.8,
        height: 1.08,
        color: baseColor,
      ),
      displaySmall: GoogleFonts.plusJakartaSans(
        fontSize: 34,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.4,
        color: baseColor,
      ),
      headlineLarge: GoogleFonts.plusJakartaSans(
        fontSize: 32,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.5,
        color: baseColor,
      ),
      headlineMedium: GoogleFonts.plusJakartaSans(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.3,
        color: baseColor,
      ),
      headlineSmall: GoogleFonts.plusJakartaSans(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        color: baseColor,
      ),
      titleLarge: GoogleFonts.plusJakartaSans(
        fontSize: 22, 
        fontWeight: FontWeight.w600,
        color: baseColor,
      ),
      titleMedium: GoogleFonts.inter(
        fontSize: 16, 
        fontWeight: FontWeight.w600,
        color: baseColor,
      ),
      titleSmall: GoogleFonts.inter(
        fontSize: 14, 
        fontWeight: FontWeight.w600,
        color: baseColor,
      ),
    );
  }
}
