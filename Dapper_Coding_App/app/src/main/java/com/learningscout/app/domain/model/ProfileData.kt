package com.learningscout.app.domain.model

data class ProfileData(
    val displayName: String = "学习者",
    val email: String = "",
    val avatarUrl: String = "",
    val identity: String = "",
    val interests: List<String> = emptyList(),
    val streakDays: Int = 0,
    val totalDays: Int = 0,
    val conceptsMastered: Int = 0,
    val activeDays: Int = 0,
)
