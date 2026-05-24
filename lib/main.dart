import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'ui/pages/splash_page.dart';

List<CameraDescription> cameras = [];

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    cameras = await availableCameras();
  } catch (e) {
    debugPrint("Inisialisasi kamera gagal: $e");
  }
  runApp(const MiniCamApp());
}

class MiniCamApp extends StatelessWidget {
  const MiniCamApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MINI CAM',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A),
      ),
      debugShowCheckedModeBanner: false,
      home: const SplashPage(),
    );
  }
}
