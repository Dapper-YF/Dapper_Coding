package com.learningscout.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "chat_messages")
data class ChatMessageEntity(
    @PrimaryKey val id: String,
    val sessionId: String = "default",
    val role: String,
    val content: String,
    val thinking: String = "",
    val conversationId: String = "default",
    val timestamp: Long = System.currentTimeMillis(),
)
