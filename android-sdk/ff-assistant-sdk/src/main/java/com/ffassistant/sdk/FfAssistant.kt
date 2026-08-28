package com.ffassistant.sdk

import android.content.Context
import android.content.Intent
import com.ffassistant.sdk.network.AssistantApi
import com.ffassistant.sdk.network.AssistantService
import com.ffassistant.sdk.ui.ChatActivity
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

data class FfAssistantConfig(
    val baseUrl: String,
    val productName: String? = null,
    val enableNetworkLogging: Boolean = false,
    val connectTimeoutSeconds: Long = 15,
    val readTimeoutSeconds: Long = 30
)

object FfAssistant {
    private lateinit var appContext: Context
    private lateinit var config: FfAssistantConfig
    internal lateinit var service: AssistantService
        private set

    @JvmStatic
    fun initialize(context: Context, config: FfAssistantConfig) {
        require(config.baseUrl.endsWith('/')) { "baseUrl must end with '/'." }
        appContext = context.applicationContext
        this.config = config
        val logging = HttpLoggingInterceptor().apply {
            level = if (config.enableNetworkLogging) HttpLoggingInterceptor.Level.BASIC else HttpLoggingInterceptor.Level.NONE
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(config.connectTimeoutSeconds, TimeUnit.SECONDS)
            .readTimeout(config.readTimeoutSeconds, TimeUnit.SECONDS)
            .build()
        val api = Retrofit.Builder()
            .baseUrl(config.baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AssistantApi::class.java)
        service = AssistantService(api)
    }

    @JvmStatic
    fun startChatSession(context: Context) {
        check(::service.isInitialized) { "Call FfAssistant.initialize() before starting a chat." }
        context.startActivity(Intent(context, ChatActivity::class.java))
    }

    internal fun context(): Context = appContext
    internal fun productName(): String? = config.productName
}