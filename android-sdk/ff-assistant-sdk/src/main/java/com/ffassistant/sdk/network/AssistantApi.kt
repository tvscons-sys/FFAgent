package com.ffassistant.sdk.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

/** REST contract implemented by the FastAPI RAG service. */
interface AssistantApi {
    @POST("chat")
    suspend fun chat(@Body request: ChatRequest): Response<ChatResponse>
}

data class ChatRequest(
    val query: String
)

data class ChatSource(
    val document: String? = null,
    val type: String? = null,
    val location: Any? = null,
    val relevance: Double? = null
)

data class ChatResponse(
    val answer: String,
    val sources: List<ChatSource> = emptyList(),
    val retrieved_count: Int = 0
)

data class ChatMessage(
    val id: String,
    val text: String,
    val sender: Sender,
    val timestamp: Long = System.currentTimeMillis(),
    // UI-only fields (not sent to the backend): drive the "no answer found ->
    // raise a ticket" prompt and the persisted thumbs-up/down feedback state.
    val retrievedCount: Int = -1,
    val feedback: Feedback? = Feedback.NONE
)

enum class Feedback { NONE, UP, DOWN }

enum class Sender { USER, ASSISTANT }

sealed class AssistantResult<out T> {
    data class Success<T>(val value: T) : AssistantResult<T>()
    data class Failure(val error: AssistantError) : AssistantResult<Nothing>()
}

sealed class AssistantError(val userMessage: String, cause: Throwable? = null) : Exception(userMessage, cause) {
    data class Http(val code: Int, val serverMessage: String? = null) : AssistantError(
        "The assistant service returned an error ($code)."
    )
    data class Network(val exception: Throwable) : AssistantError("Unable to reach the assistant service.", exception)
    data class InvalidResponse(val exception: Throwable? = null) : AssistantError("The assistant returned an invalid response.", exception)
}