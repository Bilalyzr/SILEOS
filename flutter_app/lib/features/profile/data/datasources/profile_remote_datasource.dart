import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/errors/exceptions.dart';

abstract class ProfileRemoteDataSource {
  Future<Map<String, dynamic>> getProfile();
  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> profileData);
  Future<String> uploadAvatar(Uint8List bytes, String filename);
}

class ProfileRemoteDataSourceImpl implements ProfileRemoteDataSource {
  final ApiClient apiClient;

  ProfileRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<Map<String, dynamic>> getProfile() async {
    try {
      final response = await apiClient.get('/api/v1/users/profile');
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw ServerException(
          'Failed to load profile',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> profileData) async {
    try {
      final response = await apiClient.put(
        '/api/v1/users/profile',
        data: profileData,
      );
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw ServerException(
          'Failed to update profile',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<String> uploadAvatar(Uint8List bytes, String filename) async {
    try {
      // Send raw bytes (works on web AND native; dart:io File does not exist on
      // web). The backend validates the MIME type, so set it from the extension
      // — MultipartFile.fromBytes defaults to octet-stream otherwise.
      final ext =
          filename.contains('.') ? filename.split('.').last.toLowerCase() : 'jpg';
      final subtype = switch (ext) {
        'png' => 'png',
        'gif' => 'gif',
        'webp' => 'webp',
        'heic' || 'heif' => 'heic',
        'bmp' => 'bmp',
        _ => 'jpeg',
      };
      final safeName = filename.isNotEmpty ? filename : 'avatar.$ext';
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          bytes,
          filename: safeName,
          contentType: MediaType('image', subtype),
        ),
      });

      // Upload through the general image endpoint with context=avatar. This
      // writes under the configured UPLOAD_DIR that nginx actually serves (the
      // same path course images use → reachable), unlike the dedicated
      // /users/avatar endpoint which historically wrote to an unserved dir and
      // 404'd. Returns {"file_url": "/uploads/avatars/<id>/<file>"}.
      final upload = await apiClient.post(
        '/api/v1/upload/image?context=avatar',
        data: formData,
      );

      if (upload.statusCode != 200 && upload.statusCode != 201) {
        throw ServerException(
          'Failed to upload avatar',
          statusCode: upload.statusCode,
        );
      }

      final url = (upload.data['file_url'] ??
              upload.data['avatar_url'] ??
              upload.data['url'] ??
              '')
          .toString();
      if (url.isEmpty) {
        throw ServerException('Upload succeeded but no URL was returned');
      }

      // Persist the served URL onto the profile so it sticks across reloads and
      // shows everywhere profile_photo is read. (PUT /profile honours
      // exclude_unset, so only the photo is changed.)
      await apiClient.put(
        '/api/v1/users/profile',
        data: {'profile_photo': url},
      );

      return url;
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }
}
