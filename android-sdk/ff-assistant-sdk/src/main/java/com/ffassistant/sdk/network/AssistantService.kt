package com.ffassistant.sdk.network

import kotlinx.coroutines.CancellationException
import retrofit2.Response
import java.io.IOException

internal class AssistantService(private val api: AssistantApi) {
    suspend fun sendMessage(request: ChatRequest): AssistantResult<ChatResponse> =
        execute { api.chat(request) }

    private suspend fun <T> execute(call: suspend () -> Response<T>): AssistantResult<T> = try {
        val response = call()
        if (response.isSuccessful) {
            response.body()?.let { AssistantResult.Success(it) }
                ?: AssistantResult.Failure(AssistantError.InvalidResponse())
        } else {
            AssistantResult.Failure(AssistantError.Http(response.code(), response.errorBody()?.string()))
        }
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (io: IOException) {
        AssistantResult.Failure(AssistantError.Network(io))
    } catch (unexpected: Exception) {
        AssistantResult.Failure(AssistantError.InvalidResponse(unexpected))
    }
}