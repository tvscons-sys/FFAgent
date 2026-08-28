package com.ffassistant.sdk.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

/** REST contract implemented by the FastAPI RAG service. */
interface AssistantApi {
    @POST("chat")
    suspend fun chat(@Body request: ChatRequest): Response<ChatResponse>

    @POST("ticket")
    suspend fun createTicket(@Body request: TicketRequest): Response<TicketResponse>
}

data class ChatRequest(
    val sessionId: String,
    val message: String,
    val product: String? = null,
    val metadata: Map<String, String> = emptyMap()
)

data class ChatResponse(
    val sessionId: String,
    val answer: String,
    val confidence: Double? = null,
    val likelyCause: String? = null,
    val evidence: List<String> = emptyList(),
    val relatedIssues: List<String> = emptyList(),
    val resolved: Boolean = false
)

data class TicketRequest(
    val sessionId: String,
    val title: String,
    val description: String,
    val product: String? = null,
    val conversation: List<ChatMessage> = emptyList()
)

data class TicketResponse(
    val ticketId: String,
    val status: String,
    val message: String? = null
)

data class ChatMessage(
    val id: String,
    val text: String,
    val sender: Sender,
    val timestamp: Long = System.currentTimeMillis()
)

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