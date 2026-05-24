import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'camera_page.dart';

class PermissionPage extends StatelessWidget {
  const PermissionPage({super.key});

  Future<void> _requestPermissions(BuildContext context) async {
    Map<Permission, PermissionStatus> statuses = await [
      Permission.camera,
      Permission.microphone,
      Permission.storage,
    ].request();

    if (statuses[Permission.camera]!.isGranted && statuses[Permission.microphone]!.isGranted) {
      if (context.mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => const CameraPage()),
        );
      }
    } else {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Aplikasi membutuhkan izin untuk melanjutkan.")),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(30.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.security, size: 90, color: Colors.orangeAccent),
            const SizedBox(height: 26),
            const Text(
              "Membutuhkan Akses",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            const Text(
              "Untuk menggunakan Mini Cam, kami memerlukan izin akses Kamera, Mikrofon, dan Penyimpanan perangkat kamu.",
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey, height: 1.5),
            ),
            const SizedBox(height: 45),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.cyanAccent,
                foregroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () => _requestPermissions(context),
              child: const Text("BERIKAN IZIN", style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }
}
