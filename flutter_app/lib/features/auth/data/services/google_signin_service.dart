// lib/features/auth/data/services/google_signin_service.dart
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

/// Wraps the Google → Firebase sign-in dance. The backend only accepts
/// Firebase ID tokens (audience = the Firebase project), so a raw
/// google_sign_in idToken is not enough: we must exchange the Google
/// credential for a Firebase session and send Firebase's ID token.
class GoogleSignInService {
  final GoogleSignIn _googleSignIn = GoogleSignIn(scopes: ['email']);

  /// Returns a Firebase ID token, or null if the user cancelled the picker.
  Future<String?> getFirebaseIdToken() async {
    final googleUser = await _googleSignIn.signIn();
    if (googleUser == null) return null;

    final googleAuth = await googleUser.authentication;
    final credential = GoogleAuthProvider.credential(
      idToken: googleAuth.idToken,
      accessToken: googleAuth.accessToken,
    );
    final userCredential =
        await FirebaseAuth.instance.signInWithCredential(credential);
    return userCredential.user?.getIdToken();
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
    await FirebaseAuth.instance.signOut();
  }
}
