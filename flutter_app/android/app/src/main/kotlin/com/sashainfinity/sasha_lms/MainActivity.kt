package com.sashainfinity.sasha_lms

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        flutterEngine
            .platformViewsController
            .registry
            .registerViewFactory(
                "sasha_bunny_player_view",
                SashaBunnyPlayerViewFactory(flutterEngine.dartExecutor.binaryMessenger)
            )
    }
}
