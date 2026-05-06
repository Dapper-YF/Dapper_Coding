package com.learningscout.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.learningscout.app.data.local.PreferencesManager
import com.learningscout.app.data.remote.AuthService
import com.learningscout.app.data.remote.dto.AuthResponse
import com.learningscout.app.data.remote.dto.LoginRequest
import com.learningscout.app.data.remote.dto.RegisterRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val isSuccess: Boolean = false,
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authService: AuthService,
    private val preferencesManager: PreferencesManager,
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun loginOrRegister() {
        viewModelScope.launch {
            _uiState.value = LoginUiState(isLoading = true)
            try {
                val deviceId = preferencesManager.getDeviceId()
                val auth = tryLogin(deviceId) ?: tryRegister(deviceId)
                if (auth != null) {
                    preferencesManager.saveAuthToken(auth.token)
                    if (auth.onboarding_complete) {
                        preferencesManager.setOnboardingComplete()
                    }
                    _uiState.value = LoginUiState(isSuccess = true)
                } else {
                    _uiState.value = LoginUiState(error = "无法连接服务器，请稍后重试")
                }
            } catch (e: Exception) {
                _uiState.value = LoginUiState(error = e.message ?: "未知错误")
            }
        }
    }

    private suspend fun tryLogin(deviceId: String): AuthResponse? {
        val response = authService.login(LoginRequest(deviceId))
        return if (response.isSuccessful) response.body() else null
    }

    private suspend fun tryRegister(deviceId: String): AuthResponse? {
        val response = authService.register(RegisterRequest(deviceId))
        return if (response.isSuccessful) response.body() else null
    }
}
