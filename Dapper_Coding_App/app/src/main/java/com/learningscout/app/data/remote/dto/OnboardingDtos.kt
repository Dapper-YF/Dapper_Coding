package com.learningscout.app.data.remote.dto

data class RegisterRequest(
    val device_id: String,
)

data class LoginRequest(
    val device_id: String,
)

data class RegisterEmailRequest(
    val name: String,
    val email: String,
    val password: String,
)

data class LoginEmailRequest(
    val email: String,
    val password: String,
)

data class AuthResponse(
    val user_id: String,
    val token: String,
    val new_user: Boolean = false,
    val onboarding_complete: Boolean = false,
)

data class OnboardingTreeResponse(
    val version: String,
    val tree: List<QuestionNode>,
)

data class QuestionNode(
    val id: String,
    val order: Int,
    val text: String,
    val type: String,
    val options: List<OptionNode>,
    val children: List<QuestionNode>? = null,
    val max_select: Int? = null,
)

data class OptionNode(
    val id: String,
    val text: String,
    val next_id: String? = null,
    val children: List<QuestionNode>? = null,
)

data class AnswerEntry(
    val question_id: String,
    val answer: List<String>,
)

data class CompleteOnboardingRequest(
    val answers: List<AnswerEntry>,
)

data class CompleteOnboardingResponse(
    val user_id: String,
    val profile: UserProfile,
    val status: String,
)

data class UserProfile(
    val name: String? = null,
    val email: String? = null,
    val avatar_url: String? = null,
    val created_at: String? = null,
    val identity: String = "",
    val identity_detail: String? = null,
    val interests: List<String> = emptyList(),
    val interests_detail: Map<String, List<String>>? = null,
    val skill_levels: Map<String, String> = emptyMap(),
    val unsure_topics: List<String> = emptyList(),
    val learning_goals: List<String> = emptyList(),
)

data class ProfileResponse(
    val profile: UserProfile,
)

data class UpdateProfileRequest(
    val name: String? = null,
    val phone: String? = null,
)

data class UpdateProfileResponse(
    val status: String,
)

data class OnboardingStatusResponse(
    val onboarding_complete: Boolean,
)
