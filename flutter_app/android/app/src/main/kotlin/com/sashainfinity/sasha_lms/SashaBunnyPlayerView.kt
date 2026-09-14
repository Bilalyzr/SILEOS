package com.sashainfinity.sasha_lms

import android.content.Context
import android.view.View
import android.view.ViewGroup
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.StandardMessageCodec
import io.flutter.plugin.platform.PlatformView
import io.flutter.plugin.platform.PlatformViewFactory
import com.example.flutter_bunny_video_player.BunnyVideoPlatformView
import androidx.media3.common.Player

class SashaBunnyPlayerView(
    context: Context,
    creationParams: Map<String, Any>?,
    messenger: BinaryMessenger
) : PlatformView {

    private val delegateView: BunnyVideoPlatformView = BunnyVideoPlatformView(context, creationParams)
    private val videoId: String? = creationParams?.get("videoId") as? String
    private var hasRegisteredListener = false
    private var methodChannel: MethodChannel? = null

    init {
        methodChannel = MethodChannel(messenger, "com.sashainfinity.sasha_lms/bunny_player")
        startCheckingPlayer()
    }

    private fun startCheckingPlayer() {
        val view = delegateView.getView()
        val checkRunnable = object : Runnable {
            override fun run() {
                val player = findMedia3Player(view)
                if (player != null) {
                    registerPlayerListener(player)
                } else {
                    view.postDelayed(this, 200)
                }
            }
        }
        view.post(checkRunnable)
    }

    private fun findMedia3Player(view: View): Player? {
        if (view is androidx.media3.ui.PlayerView) {
            return view.player
        }
        if (view is ViewGroup) {
            for (i in 0 until view.childCount) {
                val player = findMedia3Player(view.getChildAt(i))
                if (player != null) return player
            }
        }
        return null
    }

    private fun registerPlayerListener(player: Player) {
        if (hasRegisteredListener) return
        hasRegisteredListener = true
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) {
                    videoId?.let { id ->
                        methodChannel?.invokeMethod("onEnded", mapOf("videoId" to id))
                    }
                }
            }
        })
    }

    override fun getView(): View {
        return delegateView.getView()
    }

    override fun dispose() {
        delegateView.dispose()
        methodChannel = null
    }
}

class SashaBunnyPlayerViewFactory(private val messenger: BinaryMessenger) : PlatformViewFactory(StandardMessageCodec.INSTANCE) {
    override fun create(context: Context, id: Int, args: Any?): PlatformView {
        val creationParams = args as? Map<String, Any>
        return SashaBunnyPlayerView(context, creationParams, messenger)
    }
}
