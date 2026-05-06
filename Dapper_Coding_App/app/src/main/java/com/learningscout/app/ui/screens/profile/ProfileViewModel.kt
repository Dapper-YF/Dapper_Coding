package com.learningscout.app.ui.screens.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.learningscout.app.data.local.PreferencesManager
import com.learningscout.app.data.remote.ApiService
import com.learningscout.app.data.remote.AuthService
import com.learningscout.app.data.remote.dto.UpdateProfileRequest
import com.learningscout.app.domain.model.ProfileData
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val profile: ProfileData = ProfileData(),
    val isLoading: Boolean = true,
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val apiService: ApiService,
    private val authService: AuthService,
    private val preferencesManager: PreferencesManager,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    init {
        loadProfile()
    }

    fun refresh() {
        loadProfile()
    }

    fun updateProfile(name: String, phone: String, onResult: (Boolean, String) -> Unit) {
        viewModelScope.launch {
            try {
                val token = preferencesManager.getAuthToken() ?: return@launch
                val resp = authService.updateProfile(
                    "Bearer $token",
                    UpdateProfileRequest(
                        name = name.ifBlank { null },
                        phone = phone.ifBlank { null },
                    ),
                )
                if (resp.isSuccessful) {
                    _uiState.value = _uiState.value.copy(
                        profile = _uiState.value.profile.copy(displayName = name.ifBlank { "学习者" }),
                    )
                    onResult(true, "保存成功")
                } else {
                    onResult(false, "保存失败，请重试")
                }
            } catch (_: Exception) {
                onResult(false, "保存失败，请重试")
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            preferencesManager.clearAuthToken()
            _uiState.value = ProfileUiState()
        }
    }

    private fun loadProfile() {
        viewModelScope.launch {
            try {
                val token = preferencesManager.getAuthToken() ?: return@launch
                val profileResp = authService.getProfile("Bearer $token")
                val stats = apiService.getUserStats()

                val profile = if (profileResp.isSuccessful) {
                    profileResp.body()?.profile
                } else null

                // Username: prefer stats.username, then profile.name, else "学习者"
                val displayName = stats.username?.takeIf { it.isNotBlank() }
                    ?: profile?.name?.takeIf { it.isNotBlank() }
                    ?: readableName(profile)

                _uiState.value = _uiState.value.copy(
                    profile = _uiState.value.profile.copy(
                        displayName = displayName,
                        email = profile?.email ?: "",
                        avatarUrl = profile?.avatar_url ?: "",
                        identity = readableIdentity(profile),
                        interests = profile?.interests?.mapNotNull { identityNames[it] } ?: emptyList(),
                        totalDays = stats.total_days,
                        streakDays = stats.streak_days,
                        conceptsMastered = stats.concepts_mastered,
                        activeDays = stats.active_days,
                    ),
                    isLoading = false,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false)
            }
        }
    }

    private companion object {
        private val identityNames = mapOf(
            "student" to "在校学生",
            "worker" to "在职人员",
            "hobbyist" to "编程爱好者",
        )
        private val detailNames = mapOf(
            "cs" to "计算机专业",
            "other" to "其他专业",
            "it_dev" to "IT 开发",
            "it_other" to "IT 相关",
            "non_it" to "转行学习者",
            "junior" to "初级",
            "mid" to "中级",
            "senior" to "高级",
        )
        private val interestLabels = mapOf(
            "cs" to "计算机科学",
            "math" to "数学",
            "physics" to "物理学",
            "other" to "其他领域",
        )

        fun readableName(profile: com.learningscout.app.data.remote.dto.UserProfile?): String {
            if (profile == null) return "学习者"
            val detail = profile.identity_detail?.takeIf { it.isNotEmpty() }
            val identity = profile.identity.takeIf { it.isNotEmpty() }

            val parts = mutableListOf<String>()
            detail?.let { detailNames[it]?.let { n -> parts.add(n) } }
            identity?.let { identityNames[it]?.let { n -> parts.add(n) } }
            return if (parts.isNotEmpty()) parts.joinToString(" · ") else "学习者"
        }

        fun readableIdentity(profile: com.learningscout.app.data.remote.dto.UserProfile?): String {
            if (profile == null) return ""
            val identity = profile.identity.takeIf { it.isNotEmpty() }
            val detail = profile.identity_detail?.takeIf { it.isNotEmpty() }
            val parts = mutableListOf<String>()
            identity?.let { identityNames[it]?.let { n -> parts.add(n) } }
            detail?.let { detailNames[it]?.let { n -> parts.add(n) } }
            return parts.joinToString(" · ")
        }
    }
}
