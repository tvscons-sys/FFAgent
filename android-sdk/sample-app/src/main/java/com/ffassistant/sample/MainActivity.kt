package com.ffassistant.sample

import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity
import com.ffassistant.sdk.FfAssistant
import com.ffassistant.sdk.FfAssistantConfig

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val button = Button(this).apply { text = "Open FF Support Assistant" }
        setContentView(button)
        FfAssistant.initialize(this, FfAssistantConfig(baseUrl = BuildConfig.FF_BACKEND_URL))
        button.setOnClickListener { FfAssistant.startChatSession(this) }
    }
}