package com.learningscout.app.data.remote.dto

data class ChatRequest(
    val message: String,
    @com.google.gson.annotations.SerializedName("conversation_id")
    val conversationId: String = "default",
)

data class ChatDeltaEvent(
    val delta: String? = null,
    val partial: String? = null,
    val done: Boolean = false,
)

// ---- Digest ----

data class DigestResponse(
    val digest: DigestItemDto?,
)

data class DigestItemDto(
    val id: Int,
    val date: String,
    val title: String,
    val content: String,
    val source_articles: String = "",
    val created_at: String = "",
)

// ---- Conversations ----

data class HistoryMessageDto(
    val role: String,
    val content: String,
    @com.google.gson.annotations.SerializedName("created_at")
    val createdAt: String,
)

data class ConversationDto(
    val id: Int,
    val user_id: String,
    val channel: String,
    val title: String? = null,
    val created_at: String,
    val last_active: String,
    val message_count: Int,
)

data class UserStatsDto(
    val username: String? = null,
    @com.google.gson.annotations.SerializedName("days_learning")
    val total_days: Int = 0,
    @com.google.gson.annotations.SerializedName("current_streak")
    val streak_days: Int = 0,
    @com.google.gson.annotations.SerializedName("concepts_mastered")
    val concepts_mastered: Int = 0,
    @com.google.gson.annotations.SerializedName("active_days")
    val active_days: Int = 0,
    val total_conversations: Int = 0,
    val total_messages: Int = 0,
)

data class DailyLessonResponse(
    val lesson: LessonDto?,
    val review_lesson: LessonDto?,
)

data class LessonDto(
    val id: String,
    val title: String,
    val summary: String?,
    val key_insight: String?,
    val image_url: String?,
)

data class AppVersionResponse(
    val version: Int,
    @com.google.gson.annotations.SerializedName("version_name")
    val versionName: String,
    @com.google.gson.annotations.SerializedName("download_url")
    val downloadUrl: String,
    val changelog: String,
    @com.google.gson.annotations.SerializedName("force_update")
    val forceUpdate: Boolean,
)

// ---- Summarize ----

data class SummarizeRequest(
    @com.google.gson.annotations.SerializedName("conversation_id")
    val conversationId: String,
)

data class SummarizeResponse(
    val summary: String = "",
    val key_points: List<String> = emptyList(),
    val next_topics: List<String> = emptyList(),
)
