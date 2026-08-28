package com.ffassistant.sdk.data

import android.content.Context
import com.ffassistant.sdk.FfAssistant
import com.ffassistant.sdk.network.AssistantResult
import com.ffassistant.sdk.network.ChatMessage
import com.ffassistant.sdk.network.ChatRequest
import com.ffassistant.sdk.network.Sender
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.util.UUID

internal class ChatRepository(context: Context) {
    private val gson = Gson()
    private val preferences = context.getSharedPreferences("ff_assistant_cache", Context.MODE_PRIVATE)
    val sessionId: String = preferences.getString("session_id", null) ?: UUID.randomUUID().toString().also {
        preferences.edit().putString("session_id", it).apply()
    }

    fun loadMessages(): List<ChatMessage> {
        val json = preferences.getString("messages", null) ?: return emptyList()
        return runCatching {
            gson.fromJson<List<ChatMessage>>(json, object : TypeToken<List<ChatMessage>>() {}.type)
        }.getOrDefault(emptyList())
    }

    fun saveMessage(message: ChatMessage) {
        val updated = (loadMessages() + message).takeLast(100)
        preferences.edit().putString("messages", gson.toJson(updated)).apply()
    }

    suspend fun send(text: String): AssistantResult<com.ffassistant.sdk.network.ChatResponse> {
        return FfAssistant.service.sendMessage(ChatRequest(sessionId, text, FfAssistant.productName()))
    }

    fun userMessage(text: String) = ChatMessage(UUID.randomUUID().toString(), text, Sender.USER)
    fun assistantMessage(text: String) = ChatMessage(UUID.randomUUID().toString(), text, Sender.ASSISTANT)
}