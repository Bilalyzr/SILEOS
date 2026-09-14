import 'dart:typed_data';
import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';

abstract class ProfileRepository {
  Future<Either<Failure, Map<String, dynamic>>> getProfile();
  Future<Either<Failure, Map<String, dynamic>>> updateProfile(Map<String, dynamic> profileData);
  Future<Either<Failure, String>> uploadAvatar(Uint8List bytes, String filename);
}
