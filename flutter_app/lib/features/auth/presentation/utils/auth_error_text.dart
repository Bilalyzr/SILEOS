/// Turns a raw backend/exception message (e.g. "Could not validate
/// credentials", "No account found with this email address") into a clean,
/// user-friendly sentence. Keeps the auth UI consistent and non-technical.
String humanizeAuthError(String raw) {
  final m = raw.toLowerCase();

  if (m.contains('could not validate credentials') || m.contains('session')) {
    return 'Your session has expired. Please sign in again.';
  }
  if (m.contains('no account found') ||
      (m.contains('not found') && m.contains('email'))) {
    return 'No account found with this email. Please check it or register.';
  }
  if (m.contains('incorrect') ||
      m.contains('invalid credentials') ||
      m.contains('wrong password') ||
      m.contains('unauthorized')) {
    return 'Incorrect email or password. Please try again.';
  }
  if (m.contains('verif')) {
    return 'Please verify your email before signing in.';
  }
  if (m.contains('already')) {
    return 'This email is already registered. Please sign in instead.';
  }
  if (m.contains('no internet') || m.contains('connection error')) {
    return 'No internet connection. Check your network and try again.';
  }
  if (m.contains('timeout')) {
    return 'The server took too long to respond. Please try again.';
  }
  if (m.contains('server error') ||
      m.contains('unexpected') ||
      m.contains('500')) {
    return 'Something went wrong on our end. Please try again shortly.';
  }

  final s = raw.trim();
  if (s.isEmpty) return 'Something went wrong. Please try again.';
  // Fallback: surface the backend text, but capitalized.
  return s[0].toUpperCase() + s.substring(1);
}
