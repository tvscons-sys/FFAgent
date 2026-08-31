package com.ffassistant.sample

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.ffassistant.sdk.FfAssistant
import com.ffassistant.sdk.FfAssistantConfig
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import com.google.android.material.textview.MaterialTextView

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        FfAssistant.initialize(
            this,
            FfAssistantConfig(
                baseUrl = BuildConfig.FF_BACKEND_URL,
                productName = "FF Vehicle Support",
                enableNetworkLogging = true
            )
        )

        val openAssistantButton = findViewById<MaterialButton>(R.id.openAssistantButton)
        openAssistantButton.setOnClickListener {
            FfAssistant.startChatSession(this)
        }
    }
}