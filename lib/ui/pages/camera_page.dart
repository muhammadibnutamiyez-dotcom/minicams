import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;
import 'package:gal/gal.dart';
import '../../main.dart';
import '../widgets/mode_button.dart';

class CameraPage extends StatefulWidget {
  const CameraPage({super.key});

  @override
  State<CameraPage> createState() => _CameraPageState();
}

class _CameraPageState extends State<CameraPage> {
  CameraController? _controller;
  int _selectedCameraIndex = 0;
  FlashMode _currentFlashMode = FlashMode.off;
  
  int _selectedMode = 0; // 0: Kamera Biasa, 1: Video, 2: Foto Live
  String _selectedResolution = "720p";
  bool _isPowerSaving = false;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    if (cameras.isNotEmpty) {
      _initCamera(_selectedCameraIndex);
    }
  }

  Future<void> _initCamera(int index) async {
    if (_controller != null) {
      await _controller!.dispose();
    }

    ResolutionPreset preset = ResolutionPreset.high;
    if (_isPowerSaving) {
      preset = ResolutionPreset.low; 
    } else {
      switch (_selectedResolution) {
        case "480p": preset = ResolutionPreset.medium; break;
        case "720p": preset = ResolutionPreset.high; break;
        case "1080p": preset = ResolutionPreset.veryHigh; break;
      }
    }

    _controller = CameraController(
      cameras[index],
      preset,
      enableAudio: _selectedMode == 1 || _selectedMode == 2,
    );

    try {
      await _controller!.initialize();
      await _controller!.setFlashMode(_currentFlashMode);
      if (mounted) setState(() {});
    } catch (e) {
      debugPrint("Gagal inisialisasi kamera: $e");
    }
  }

  void _toggleCamera() {
    if (cameras.length < 2) return;
    _selectedCameraIndex = _selectedCameraIndex == 0 ? 1 : 0;
    _initCamera(_selectedCameraIndex);
  }

  void _toggleFlash() {
    setState(() {
      _currentFlashMode = _currentFlashMode == FlashMode.off ? FlashMode.torch : FlashMode.off;
    });
    _controller?.setFlashMode(_currentFlashMode);
  }

  Future<File> _processWatermark(String path) async {
    final bytes = await File(path).readAsBytes();
    img.Image? originalImage = img.decodeImage(bytes);
    
    if (originalImage != null) {
      String wmText = "Made With Mini Cam";
      int x = originalImage.width - (wmText.length * 14) - 30;
      int y = originalImage.height - 50;

      img.drawString(
        originalImage,
        wmText,
        font: img.arial24,
        x: x,
        y: y,
        color: img.ColorRgb8(255, 255, 255),
      );
      
      final wmBytes = img.encodeJpg(originalImage, quality: 90);
      final finalFile = File(path);
      await finalFile.writeAsBytes(wmBytes);
      return finalFile;
    }
    return File(path);
  }

  void _takeAction() async {
    if (_controller == null || !_controller!.value.isInitialized || _isProcessing) return;

    setState(() => _isProcessing = true);

    try {
      if (_selectedMode == 0) {
        final XFile photo = await _controller!.takePicture();
        File wmFile = await _processWatermark(photo.path);
        await Gal.putImage(wmFile.path);
        _showNotification("Foto berhasil disimpan ke Galeri!");

      } else if (_selectedMode == 1) {
        if (_controller!.value.isRecordingVideo) {
          final XFile video = await _controller!.stopVideoRecording();
          await Gal.putVideo(video.path);
          _showNotification("Video berhasil disimpan!");
        } else {
          await _controller!.startVideoRecording();
        }

      } else if (_selectedMode == 2) {
        _showNotification("Mengabadikan Foto Live... Mohon diam!");
        
        // 1. Ambil Foto
        final XFile livePhoto = await _controller!.takePicture();
        File wmLiveFile = await _processWatermark(livePhoto.path);
        await Gal.putImage(wmLiveFile.path);

        // 2. Ambil Video Pendek 2 Detik Berdampingan
        await _controller!.startVideoRecording();
        await Future.delayed(const Duration(seconds: 2));
        final XFile liveVideo = await _controller!.stopVideoRecording();
        await Gal.putVideo(liveVideo.path);

        _showNotification("Live Photo Berhasil Disimpan (Foto + Video)!");
      }
    } catch (e) {
      _showNotification("Gagal memproses media: $e");
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  void _showNotification(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_controller == null || !_controller!.value.isInitialized) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          Positioned.fill(child: CameraPreview(_controller!)),
          
          Positioned(
            bottom: 150,
            right: 16,
            child: Container(
              padding: const EdgeInsets.all(4),
              color: Colors.black45,
              child: const Text("Made With Mini Cam", style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold)),
            ),
          ),

          Positioned(
            top: 40,
            left: 16,
            right: 16,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: Icon(_currentFlashMode == FlashMode.off ? Icons.flash_off : Icons.flash_on, color: Colors.white),
                  onPressed: _toggleFlash,
                ),
                IconButton(
                  icon: const Icon(Icons.settings, color: Colors.white),
                  onPressed: () => _showSettingsDialog(context),
                ),
              ],
            ),
          ),

          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              color: Colors.black87,
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      ModeButton(text: "Kamera", isSelected: _selectedMode == 0, onTap: () => _changeMode(0)),
                      ModeButton(text: "Video", isSelected: _selectedMode == 1, onTap: () => _changeMode(1)),
                      ModeButton(text: "Foto Live", isSelected: _selectedMode == 2, onTap: () => _changeMode(2)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      const SizedBox(width: 60),
                      GestureDetector(
                        onTap: _takeAction,
                        child: Container(
                          height: 75,
                          width: 75,
                          decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.white, width: 4)),
                          child: Container(
                            margin: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: _isProcessing ? Colors.orange : (_selectedMode == 1 && _controller!.value.isRecordingVideo ? Colors.red : Colors.white),
                            ),
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.flip_camera_android, color: Colors.white, size: 30),
                        onPressed: _toggleCamera,
                      ),
                    ],
                  )
                ],
              ),
            ),
          )
        ],
      ),
    );
  }

  void _changeMode(int index) {
    setState(() => _selectedMode = index);
    _initCamera(_selectedCameraIndex);
  }

  void _showSettingsDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text("Pengaturan MINI CAM"),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Resolusi:", style: TextStyle(fontWeight: FontWeight.bold)),
                    Row(
                      children: ["480p", "720p", "1080p"].map((res) {
                        return Expanded(
                          child: RadioListTile<String>(
                            title: Text(res, style: const TextStyle(fontSize: 12)),
                            value: res,
                            groupValue: _selectedResolution,
                            contentPadding: EdgeInsets.zero,
                            onChanged: _isPowerSaving ? null : (val) {
                              setDialogState(() => _selectedResolution = val!);
                              setState(() => _selectedResolution = val!);
                              _initCamera(_selectedCameraIndex);
                            },
                          ),
                        );
                      }).toList(),
                    ),
                    if (_isPowerSaving)
                      const Text("*Resolusi terkunci <480p (Mode Hemat Daya Aktif).", style: TextStyle(color: Colors.orange, fontSize: 11)),
                    const Divider(),
                    SwitchListTile(
                      title: const Text("Mode Hemat Daya", style: TextStyle(fontSize: 14)),
                      value: _isPowerSaving,
                      onChanged: (val) {
                        setDialogState(() => _isPowerSaving = val);
                        setState(() => _isPowerSaving = val);
                        _initCamera(_selectedCameraIndex);
                      },
                    ),
                    const Divider(),
                    const Text(
                      "Aplikasi ini masih versi Beta atau percobaan, rencana akan di kembangkan agar mempermudah pengguna.",
                      style: TextStyle(fontSize: 12, italic: true, color: Colors.grey),
                    ),
                    const SizedBox(height: 16),
                    const Text("Version : 1.7 BETA", style: TextStyle(fontSize: 11, color: Colors.white54)),
                    const Text("COPYRIGHT MINI CAM by Zemi @2026", style: TextStyle(fontSize: 11, color: Colors.cyanAccent)),
                  ],
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(context), child: const Text("TUTUP")),
              ],
            );
          },
        );
      },
    );
  }
}
