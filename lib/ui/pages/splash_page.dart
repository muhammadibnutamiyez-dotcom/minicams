import 'dart:async';
import 'package:flutter/material.dart';
import 'permission_page.dart';

class SplashPage extends StatefulWidget {
  const SplashPage({super.key});

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);

    Timer(const Duration(seconds: 4), () {
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => const PermissionPage()),
        );
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedBuilder(
              animation: _controller,
              builder: (context, child) {
                return Transform.translate(
                  offset: Offset(0, _controller.value * -25),
                  child: child,
                );
              },
              child: const Icon(
                Icons.camera_enhance_rounded, 
                size: 110,
                color: Colors.cyanAccent,
              ),
            ),
            const SizedBox(height: 28),
            const Text(
              "Mini Cam",
              style: TextStyle(fontSize: 34, fontWeight: FontWeight.bold, letterSpacing: 3),
            ),
            const SizedBox(height: 14),
            const SizedBox(
              width: 160,
              child: LinearProgressIndicator(color: Colors.cyanAccent),
            ),
          ],
        ),
      ),
    );
  }
}
