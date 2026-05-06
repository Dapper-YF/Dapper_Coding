package com.learningscout.app.ui.screens.chat

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.learningscout.app.data.local.entity.ChatMessageEntity
import com.learningscout.app.data.local.entity.ChatSessionEntity
import com.learningscout.app.data.remote.ApiService
import com.learningscout.app.data.remote.dto.SummarizeRequest
import com.learningscout.app.data.remote.dto.SummarizeResponse
import com.learningscout.app.data.repository.ChatRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.UUID
import javax.inject.Inject

data class ChatUiState(
    val sessions: List<ChatSessionEntity> = emptyList(),
    val currentSessionId: String? = null,
    val messages: List<ChatMessageEntity> = emptyList(),
    val isStreaming: Boolean = false,
    val streamingMessageId: String? = null,
    val streamingThinking: String = "",
    val error: String? = null,
    val isLoading: Boolean = false,
    val insightChips: List<String> = emptyList(),
    val summaryData: SummarizeResponse? = null,
    val isSummarizing: Boolean = false,
    val expandedThinkingIds: Set<String> = emptySet(),
    val lastUserMessage: String? = null,
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val chatRepository: ChatRepository,
    private val apiService: ApiService,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private var sessionsJob: Job? = null
    private var messagesJob: Job? = null

    init {
        loadSessions()
    }

    private fun loadSessions() {
        sessionsJob?.cancel()
        sessionsJob = viewModelScope.launch {
            chatRepository.getSessions().collect { sessions ->
                _uiState.value = _uiState.value.copy(sessions = sessions)
                // Auto-select first session if none selected
                if (_uiState.value.currentSessionId == null && sessions.isNotEmpty()) {
                    selectSession(sessions.first().id)
                }
            }
        }
    }

    fun createNewSession() {
        viewModelScope.launch {
            val sessionId = chatRepository.createSession()
            selectSession(sessionId)
        }
    }

    fun selectSession(sessionId: String) {
        if (_uiState.value.currentSessionId == sessionId) return
        _uiState.value = _uiState.value.copy(
            currentSessionId = sessionId,
            messages = emptyList(),
            error = null,
            isLoading = true,
        )
        messagesJob?.cancel()
        messagesJob = viewModelScope.launch {
            chatRepository.getMessages(sessionId).collect { messages ->
                // Don't overwrite messages while streaming — the stream manages
                // message content in real-time via onDelta callbacks.
                if (!_uiState.value.isStreaming) {
                    _uiState.value = _uiState.value.copy(
                        messages = messages,
                        isLoading = false,
                    )
                }
            }
        }
    }

    fun deleteSession(sessionId: String) {
        viewModelScope.launch {
            chatRepository.deleteSession(sessionId)
            val sessions = _uiState.value.sessions
            if (_uiState.value.currentSessionId == sessionId) {
                val remaining = sessions.filter { it.id != sessionId }
                if (remaining.isNotEmpty()) {
                    selectSession(remaining.first().id)
                } else {
                    _uiState.value = _uiState.value.copy(
                        currentSessionId = null,
                        messages = emptyList(),
                    )
                }
            }
        }
    }

    fun ensureSessionAndSend(text: String) {
        if (text.isBlank()) return
        if (_uiState.value.currentSessionId == null) {
            viewModelScope.launch {
                val sessionId = chatRepository.createSession()
                selectSession(sessionId)
                // wait for session selection to propagate
                while (_uiState.value.currentSessionId != sessionId) {
                    kotlinx.coroutines.delay(50)
                }
                sendMessage(text)
            }
        } else {
            sendMessage(text)
        }
    }

    fun sendMessage(text: String) {
        if (text.isBlank()) return
        if (_uiState.value.isStreaming) return

        val sessionId = _uiState.value.currentSessionId ?: return

        val now = System.currentTimeMillis()
        val userMessage = ChatMessageEntity(
            id = UUID.randomUUID().toString(),
            sessionId = sessionId,
            role = "user",
            content = text.trim(),
            timestamp = now,
        )

        val aiMessage = ChatMessageEntity(
            id = UUID.randomUUID().toString(),
            sessionId = sessionId,
            role = "ai",
            content = "",
            timestamp = now + 1,
        )

        val currentMessages = _uiState.value.messages.toMutableList()
        currentMessages.add(userMessage)
        currentMessages.add(aiMessage)
        _uiState.value = _uiState.value.copy(
            messages = currentMessages,
            isStreaming = true,
            streamingMessageId = aiMessage.id,
            streamingThinking = "",
            error = null,
            insightChips = emptyList(),
            lastUserMessage = text.trim(),
        )

        // Save user message locally
        viewModelScope.launch {
            chatRepository.sendMessage(userMessage)
            // Update session title from first user message
            if (currentMessages.size <= 2) {
                val title = if (text.length > 10) text.take(10) + "…" else text
                chatRepository.updateSessionTitle(sessionId, title)
            }
        }

        // Stream AI response
        chatRepository.streamChat(
            message = text.trim(),
            sessionId = sessionId,
            onDelta = { thinking, response ->
                try {
                    val updated = _uiState.value.messages.toMutableList()
                    val idx = updated.indexOfLast { it.id == aiMessage.id }
                    if (idx >= 0) {
                        updated[idx] = updated[idx].copy(content = response)
                    }
                    _uiState.value = _uiState.value.copy(
                        messages = updated,
                        streamingThinking = thinking,
                    )
                } catch (e: Exception) {
                    Log.e("ChatViewModel", "onDelta crash", e)
                }
            },
            onComplete = { finalContent, finalThinking, insightChips, _ ->
                Log.d("ChatViewModel", "onComplete called — contentLen=${finalContent.length}, thinkingLen=${finalThinking.length}, chips=$insightChips")
                try {
                    val validContent = validateContent(finalContent)
                    val updated = _uiState.value.messages.toMutableList()
                    val idx = updated.indexOfLast { it.id == aiMessage.id }
                    if (idx >= 0) {
                        if (validContent != null) {
                            updated[idx] = updated[idx].copy(content = validContent, thinking = finalThinking)
                        } else {
                            // Content is garbled/empty — remove the placeholder AI bubble
                            updated.removeAt(idx)
                        }
                    }
                    _uiState.value = _uiState.value.copy(
                        messages = updated,
                        isStreaming = false,
                        streamingMessageId = null,
                        streamingThinking = "",
                        insightChips = if (validContent != null) insightChips else emptyList(),
                        error = if (validContent == null) "AI 回复异常，请重试" else null,
                    )
                    // Save AI message locally (only if valid)
                    if (validContent != null) {
                        val aiMsg = updated.lastOrNull { it.role == "ai" }
                        if (aiMsg != null) {
                            viewModelScope.launch {
                                chatRepository.sendMessage(aiMsg)
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.e("ChatViewModel", "onComplete crash", e)
                    _uiState.value = _uiState.value.copy(
                        isStreaming = false,
                        streamingMessageId = null,
                        streamingThinking = "",
                        error = "消息处理异常，请重试",
                    )
                }
            },
            onError = { error ->
                _uiState.value = _uiState.value.copy(
                    isStreaming = false,
                    streamingMessageId = null,
                    error = error,
                )
            },
        )
    }

    fun retryLastMessage() {
        val text = _uiState.value.lastUserMessage ?: return
        if (_uiState.value.isStreaming) return
        // Remove the last AI message (failed one) from the list
        val msgs = _uiState.value.messages.toMutableList()
        val lastAiIdx = msgs.indexOfLast { it.role == "ai" }
        if (lastAiIdx >= 0 && msgs[lastAiIdx].content.isBlank()) {
            msgs.removeAt(lastAiIdx)
        }
        _uiState.value = _uiState.value.copy(
            messages = msgs,
            error = null,
        )
        sendMessage(text)
    }

    fun toggleThinking(messageId: String) {
        _uiState.value = _uiState.value.copy(
            expandedThinkingIds = _uiState.value.expandedThinkingIds.let {
                if (messageId in it) it - messageId else it + messageId
            }
        )
    }

    fun generateSummary() {
        val sessionId = _uiState.value.currentSessionId ?: return
        val messages = _uiState.value.messages
        if (messages.isEmpty()) return

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSummarizing = true)
            try {
                val response = apiService.summarize(SummarizeRequest(sessionId))
                _uiState.value = _uiState.value.copy(
                    summaryData = response,
                    isSummarizing = false,
                )
            } catch (e: Exception) {
                Log.w("ChatViewModel", "Summarize API failed, using local fallback", e)
                // Local fallback summary
                val userMsgs = messages.filter { it.role == "user" }.map { it.content }
                val keyWords = extractKeywords(userMsgs)
                _uiState.value = _uiState.value.copy(
                    summaryData = SummarizeResponse(
                        summary = "本次对话共 ${messages.size} 条消息，讨论了 ${keyWords.joinToString("、")}",
                        key_points = keyWords.take(5),
                        next_topics = keyWords.take(3).map { "深入了解 $it" },
                    ),
                    isSummarizing = false,
                )
            }
        }
    }

    fun clearSummary() {
        _uiState.value = _uiState.value.copy(summaryData = null)
    }

    private fun extractKeywords(messages: List<String>): List<String> {
        val techPatterns = listOf(
            Regex("\\b(Python|JavaScript|TypeScript|Java|Kotlin|Swift|Go|Rust|C\\+\\+)\\b"),
            Regex("\\b(API|REST|HTTP|SSE|WebSocket|GraphQL)\\b"),
            Regex("\\b(SQL|NoSQL|MongoDB|Redis|PostgreSQL|MySQL)\\b"),
            Regex("\\b(Docker|Kubernetes|CI/CD|DevOps|微服务)\\b"),
            Regex("\\b(React|Vue|Angular|Compose|Flutter|SwiftUI)\\b"),
            Regex("\\b(机器学习|深度学习|神经网络|AI|LLM|NLP|CV)\\b"),
            Regex("\\b(算法|数据结构|排序|搜索|动态规划|递归)\\b"),
            Regex("\\b(函数|类|对象|继承|多态|接口|抽象)\\b"),
            Regex("\\b(异步|并发|多线程|协程|线程池|锁)\\b"),
            Regex("\\b(测试|单元测试|集成测试|TDD|Mock)\\b"),
        )
        val found = mutableSetOf<String>()
        for (msg in messages) {
            for (pattern in techPatterns) {
                pattern.findAll(msg).forEach { found.add(it.value) }
            }
        }
        return found.take(8).toList()
    }

    /**
     * Validate LLM response content. Returns null if the content is irrecoverably
     * garbled; otherwise returns cleaned content (with U+FFFD chars stripped).
     */
    private fun validateContent(content: String): String? {
        var cleaned = content.trim()
        if (cleaned.isEmpty()) {
            Log.w("ChatViewModel", "validateContent: empty after trim")
            return null
        }

        // Strip Unicode replacement characters (corrupted UTF-8 decoding);
        // reject only if the damage ratio is too high.
        val replacementCount = cleaned.count { it == '�' }
        if (replacementCount > 0) {
            val ratio = replacementCount.toFloat() / cleaned.length
            Log.w("ChatViewModel", "validateContent: found $replacementCount replacement chars (${(ratio * 100).toInt()}% of ${cleaned.length})")
            if (ratio > 0.5f) {
                // More than half the content is corrupted — unrecoverable
                Log.w("ChatViewModel", "validateContent: corruption ratio too high, rejecting")
                return null
            }
            // Strip the bad chars and continue
            cleaned = cleaned.replace("�", "")
        }

        // Check for sufficient meaningful characters (CJK + ASCII letters/digits)
        val meaningfulChars = cleaned.count { it.isLetterOrDigit() || it in '一'..'鿿' }
        Log.d("ChatViewModel", "validateContent: meaningfulChars=$meaningfulChars, totalLen=${cleaned.length}")
        if (meaningfulChars < 3) {
            Log.w("ChatViewModel", "validateContent: too few meaningful chars ($meaningfulChars), len=${cleaned.length}")
            return null
        }
        return cleaned
    }

    fun refresh() {
        // Reselect current session to reload
        _uiState.value.currentSessionId?.let { selectSession(it) }
    }

    // Legacy support — loads server conversation history, syncs to local DB, then selects
    fun setConversationId(id: String) {
        viewModelScope.launch {
            // Check if we already have local messages for this session
            val localSessions = _uiState.value.sessions
            val hasLocalSession = localSessions.any { it.id == id }
            try {
                if (!hasLocalSession) {
                    // Sync session and messages from server
                    val history = apiService.getConversationHistory(id)
                    if (history.isNotEmpty()) {
                        val title = history.firstOrNull { it.role == "user" }?.content?.take(10)
                            ?: "历史对话"
                        chatRepository.ensureSession(id, if (title.length >= 10) "$title…" else title)
                        for (msg in history) {
                            val role = if (msg.role == "assistant") "ai" else msg.role
                            val timestamp = try {
                                SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).parse(msg.createdAt)?.time
                                    ?: System.currentTimeMillis()
                            } catch (_: Exception) {
                                System.currentTimeMillis()
                            }
                            chatRepository.sendMessage(
                                ChatMessageEntity(
                                    id = UUID.randomUUID().toString(),
                                    sessionId = id,
                                    role = role,
                                    content = msg.content,
                                    timestamp = timestamp,
                                )
                            )
                        }
                    }
                }
            } catch (e: Exception) {
                Log.w("ChatViewModel", "Failed to sync server history for $id", e)
            }
            selectSession(id)
        }
    }
}
