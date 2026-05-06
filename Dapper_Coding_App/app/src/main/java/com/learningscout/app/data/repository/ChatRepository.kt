package com.learningscout.app.data.repository

import android.util.Log
import com.google.gson.Gson
import com.learningscout.app.data.local.dao.ChatDao
import com.learningscout.app.data.local.entity.ChatMessageEntity
import com.learningscout.app.data.local.entity.ChatSessionEntity
import com.learningscout.app.data.remote.RetrofitClient
import com.learningscout.app.data.remote.dto.ChatRequest
import kotlinx.coroutines.flow.Flow
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.net.SocketTimeoutException
import java.util.UUID
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val chatDao: ChatDao,
    @Named("apiClient") private val okHttpClient: OkHttpClient,
) {
    private val gson = Gson()

    // ---- Sessions ----

    fun getSessions(): Flow<List<ChatSessionEntity>> = chatDao.getSessions()

    suspend fun createSession(): String {
        val session = ChatSessionEntity(
            id = UUID.randomUUID().toString(),
            title = "新对话",
            createdAt = System.currentTimeMillis(),
            updatedAt = System.currentTimeMillis(),
        )
        chatDao.insertSession(session)
        return session.id
    }

    suspend fun ensureSession(sessionId: String, title: String = "历史对话") {
        chatDao.insertSession(
            ChatSessionEntity(
                id = sessionId,
                title = title,
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis(),
            )
        )
    }

    suspend fun updateSessionTitle(sessionId: String, title: String) {
        chatDao.updateSession(sessionId, title)
    }

    suspend fun deleteSession(sessionId: String) {
        chatDao.clearMessages(sessionId)
        chatDao.deleteSession(sessionId)
    }

    // ---- Messages ----

    fun getMessages(sessionId: String): Flow<List<ChatMessageEntity>> =
        chatDao.getMessages(sessionId)

    fun getMessagesLegacy(conversationId: String = "default"): Flow<List<ChatMessageEntity>> =
        chatDao.getMessagesLegacy(conversationId)

    suspend fun sendMessage(message: ChatMessageEntity) {
        chatDao.insertMessage(message)
    }

    suspend fun clearConversation(conversationId: String = "default") {
        chatDao.clearConversation(conversationId)
    }

    // ---- Thinking tag filter ----

    suspend fun reportLessonFeedback(lessonId: String, feedback: String): Boolean {
        return try {
            val body = """{"lesson_id":"$lessonId","feedback":"$feedback"}"""
            val request = Request.Builder()
                .url("${RetrofitClient.BASE_URL}api/lesson/feedback")
                .post(body.toRequestBody("application/json".toMediaType()))
                .build()
            okHttpClient.newCall(request).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    fun stripThinkingTags(text: String): String {
        return text
            .replace(Regex("<think>[\\s\\S]*?</think>", setOf(RegexOption.DOT_MATCHES_ALL)), "")
            .replace(Regex("<thinking>[\\s\\S]*?</thinking>", setOf(RegexOption.DOT_MATCHES_ALL)), "")
            .replace(Regex("\\[THINKING\\][\\s\\S]*?\\[/THINKING\\]"), "")
            .replace(Regex("```think[\\s\\S]*?```"), "")
            .trim()
    }

    // ---- SSE streaming chat ----

    fun streamChat(
        message: String,
        sessionId: String,
        onDelta: (thinking: String, response: String) -> Unit,
        onComplete: (response: String, thinking: String, List<String>, List<String>) -> Unit,
        onError: (String) -> Unit,
    ) {
        val jsonBody = gson.toJson(ChatRequest(message, sessionId))
        val request = Request.Builder()
            .url("${RetrofitClient.BASE_URL}api/chat")
            .post(jsonBody.toRequestBody("application/json".toMediaType()))
            .build()

        okHttpClient.newCall(request).enqueue(object : okhttp3.Callback {
            override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                Log.e("ChatRepository", "SSE request failed", e)
                val msg = if (e is SocketTimeoutException) {
                    "响应超时，请重试"
                } else {
                    "网络开小差了，请重试"
                }
                onError(msg)
            }

            override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
                try {
                    if (!response.isSuccessful) {
                        response.close()
                        Log.e("ChatRepository", "HTTP ${response.code}: ${response.message}")
                        onError("服务器响应异常 (${response.code})")
                        return
                    }

                    val source = response.body?.source()
                    if (source == null) {
                        response.close()
                        onError("Empty response")
                        return
                    }

                    val fullRaw = StringBuilder()
                    val fullClean = StringBuilder()
                    val thinkingFull = StringBuilder()
                    var inThinking = false
                    var insightChips = emptyList<String>()
                    var detectedTopics = emptyList<String>()

                    try {
                        while (!source.exhausted()) {
                            val line = source.readUtf8Line() ?: break
                            if (!line.startsWith("data: ")) continue
                            val data = line.removePrefix("data: ").trim()
                            if (data == "[DONE]") break

                            // Try parsing as done event first
                            try {
                                val doneEvent = gson.fromJson(data, SseDoneEvent::class.java)
                                if (doneEvent.done == true) {
                                    insightChips = doneEvent.insight_chips ?: emptyList()
                                    detectedTopics = doneEvent.detected_topics ?: emptyList()
                                    if (fullRaw.isEmpty() && !doneEvent.full.isNullOrBlank()) {
                                        fullRaw.append(doneEvent.full)
                                        fullClean.append(doneEvent.full)
                                        onDelta(thinkingFull.toString(), fullClean.toString())
                                    }
                                    continue
                                }
                            } catch (_: Exception) { }

                            // Parse as delta event
                            try {
                                val event = gson.fromJson(data, SseEvent::class.java)
                                val chunk = event.delta ?: event.partial ?: ""
                                if (chunk.isEmpty()) continue
                                fullRaw.append(chunk)

                                val (newInThinking, thinkingChunk, responseChunk) = applyThinkingFilter(chunk, inThinking)
                                inThinking = newInThinking
                                if (thinkingChunk.isNotEmpty()) {
                                    thinkingFull.append(thinkingChunk)
                                }
                                if (responseChunk.isNotEmpty()) {
                                    fullClean.append(responseChunk)
                                }
                                onDelta(thinkingFull.toString(), fullClean.toString())
                            } catch (_: Exception) {
                                Log.w("ChatRepository", "Failed to parse SSE: $data")
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("ChatRepository", "SSE read error", e)
                    } finally {
                        response.close()
                        // If still inside a think block, fullRaw has the complete text;
                        // use stripThinkingTags on it instead of the truncated fullClean.
                        val finalText = if (!inThinking && fullClean.isNotEmpty()) {
                            fullClean.toString()
                        } else {
                            stripThinkingTags(fullRaw.toString())
                        }
                        val finalThinking = thinkingFull.toString()
                        Log.d("ChatRepository", "SSE complete — finalLen=${finalText.length}, thinkingLen=${finalThinking.length}, inThinking=$inThinking, chips=$insightChips, topics=$detectedTopics")
                        onComplete(finalText, finalThinking, insightChips, detectedTopics)
                    }
                } catch (e: Exception) {
                    Log.e("ChatRepository", "SSE outer crash", e)
                    try { response.close() } catch (_: Exception) {}
                    onError("消息接收异常，请重试")
                }
            }
        })
    }

    // ---- Data classes for SSE parsing ----

    private data class SseEvent(
        val delta: String?,
        val partial: String?,
    )

    private data class SseDoneEvent(
        val done: Boolean?,
        val full: String?,
        val insight_chips: List<String>?,
        val detected_topics: List<String>?,
    )

    // ---- Thinking filter ----

    private fun applyThinkingFilter(chunk: String, inThinking: Boolean): Triple<Boolean, String, String> {
        val lower = chunk.lowercase()
        val openIdx = lower.indexOf("<think>")
        if (!inThinking && openIdx >= 0) {
            val closeIdx = lower.indexOf("</think>", openIdx + 7)
            return if (closeIdx >= 0) {
                // Both tags in this chunk: extract thinking between them
                val thinking = chunk.substring(openIdx + 7, closeIdx)
                val response = chunk.substring(0, openIdx) + chunk.substring(closeIdx + 8)
                Triple(false, thinking, response)
            } else {
                // Open tag found, no close: everything after <think> is thinking
                val thinking = chunk.substring(openIdx + 7)
                Triple(true, thinking, chunk.substring(0, openIdx))
            }
        }
        if (inThinking) {
            val closeIdx = lower.indexOf("</think>")
            return if (closeIdx >= 0) {
                // Close tag found: before it is thinking, after it is response
                val thinking = chunk.substring(0, closeIdx)
                Triple(false, thinking, chunk.substring(closeIdx + 8))
            } else {
                // Still inside think block: entire chunk is thinking
                Triple(true, chunk, "")
            }
        }
        return Triple(false, "", chunk)
    }
}
