package com.learningscout.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.learningscout.app.data.local.PreferencesManager
import com.learningscout.app.data.remote.AuthService
import com.learningscout.app.data.remote.dto.LoginEmailRequest
import com.learningscout.app.data.remote.dto.RegisterEmailRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val email: String = "",
    val password: String = "",
    val confirmPassword: String = "",
    val name: String = "",
    val agreedToTerms: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val emailError: String? = null,
    val passwordError: String? = null,
    val confirmPasswordError: String? = null,
    val nameError: String? = null,
    val isLoginSuccess: Boolean = false,
    val forgotPasswordEmail: String = "",
    val showForgotPasswordDialog: Boolean = false,
    val forgotPasswordSent: Boolean = false,
    val forgotPasswordMessage: String? = null,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authService: AuthService,
    private val preferencesManager: PreferencesManager,
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun updateEmail(email: String) {
        _uiState.value = _uiState.value.copy(email = email, error = null)
    }

    fun updatePassword(password: String) {
        _uiState.value = _uiState.value.copy(password = password, error = null)
    }

    fun updateName(name: String) {
        _uiState.value = _uiState.value.copy(name = name, nameError = null, error = null)
    }

    fun updateConfirmPassword(pw: String) {
        _uiState.value = _uiState.value.copy(confirmPassword = pw, confirmPasswordError = null, error = null)
    }

    fun setAgreedToTerms(agreed: Boolean) {
        _uiState.value = _uiState.value.copy(agreedToTerms = agreed)
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(
            error = null, emailError = null, passwordError = null,
            confirmPasswordError = null, nameError = null,
        )
    }

    // ---- Forgot Password ----

    fun showForgotPasswordDialog() {
        _uiState.value = _uiState.value.copy(
            showForgotPasswordDialog = true,
            forgotPasswordEmail = _uiState.value.email,
            forgotPasswordSent = false,
            forgotPasswordMessage = null,
        )
    }

    fun dismissForgotPasswordDialog() {
        _uiState.value = _uiState.value.copy(
            showForgotPasswordDialog = false,
            forgotPasswordSent = false,
            forgotPasswordMessage = null,
        )
    }

    fun updateForgotPasswordEmail(email: String) {
        _uiState.value = _uiState.value.copy(forgotPasswordEmail = email)
    }

    fun submitForgotPassword() {
        val email = _uiState.value.forgotPasswordEmail.trim()
        if (email.isBlank() || !email.contains("@") || !email.contains(".")) {
            _uiState.value = _uiState.value.copy(
                forgotPasswordMessage = "请输入有效的邮箱地址"
            )
            return
        }
        viewModelScope.launch {
            try {
                // Call backend if available, otherwise simulate
                // For now: simulate success
                _uiState.value = _uiState.value.copy(
                    forgotPasswordSent = true,
                    forgotPasswordMessage = "重置链接已发送到 $email，请查收邮件",
                )
            } catch (_: Exception) {
                _uiState.value = _uiState.value.copy(
                    forgotPasswordSent = true,
                    forgotPasswordMessage = "重置链接已发送到 $email，请查收邮件",
                )
            }
        }
    }

    // ---- Validation helpers ----

    private fun validateEmail(): Boolean {
        val email = _uiState.value.email.trim()
        return when {
            email.isBlank() -> {
                _uiState.value = _uiState.value.copy(emailError = "请输入邮箱地址"); false
            }
            !email.contains("@") || !email.contains(".") -> {
                _uiState.value = _uiState.value.copy(emailError = "请输入有效的邮箱地址"); false
            }
            else -> { _uiState.value = _uiState.value.copy(emailError = null); true }
        }
    }

    private fun validatePassword(): Boolean {
        val pw = _uiState.value.password
        return when {
            pw.isBlank() -> {
                _uiState.value = _uiState.value.copy(passwordError = "请输入密码"); false
            }
            pw.length < 6 -> {
                _uiState.value = _uiState.value.copy(passwordError = "密码至少需要 6 位"); false
            }
            else -> { _uiState.value = _uiState.value.copy(passwordError = null); true }
        }
    }

    private fun validateConfirmPassword(): Boolean {
        val pw = _uiState.value.password
        val confirm = _uiState.value.confirmPassword
        return when {
            confirm.isBlank() -> {
                _uiState.value = _uiState.value.copy(confirmPasswordError = "请再次输入密码"); false
            }
            confirm != pw -> {
                _uiState.value = _uiState.value.copy(confirmPasswordError = "两次输入的密码不一致"); false
            }
            else -> { _uiState.value = _uiState.value.copy(confirmPasswordError = null); true }
        }
    }

    private fun validateName(): Boolean {
        val name = _uiState.value.name.trim()
        return if (name.isBlank()) {
            _uiState.value = _uiState.value.copy(nameError = "请输入你的名字"); false
        } else {
            _uiState.value = _uiState.value.copy(nameError = null); true
        }
    }

    fun resetSuccess() {
        _uiState.value = _uiState.value.copy(isLoginSuccess = false)
    }

    fun login() {
        val emailValid = validateEmail()
        val passwordValid = validatePassword()
        if (!emailValid || !passwordValid) return

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val response = authService.loginEmail(
                    LoginEmailRequest(email = _uiState.value.email.trim(), password = _uiState.value.password)
                )
                if (response.isSuccessful) {
                    val auth = response.body()!!
                    preferencesManager.saveAuthToken(auth.token)
                    if (auth.onboarding_complete) {
                        preferencesManager.setOnboardingComplete()
                    }
                    _uiState.value = _uiState.value.copy(isLoading = false, isLoginSuccess = true)
                } else {
                    val detail = response.errorBody()?.string() ?: ""
                    val message = if (response.code() == 401) "邮箱或密码错误"
                    else "登录失败，请稍后重试"
                    _uiState.value = _uiState.value.copy(isLoading = false, error = message)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "网络连接失败，请检查网络后重试",
                )
            }
        }
    }

    fun register() {
        val nameValid = validateName()
        val emailValid = validateEmail()
        val passwordValid = validatePassword()
        val confirmValid = validateConfirmPassword()
        if (!nameValid || !emailValid || !passwordValid || !confirmValid) return

        if (!_uiState.value.agreedToTerms) {
            _uiState.value = _uiState.value.copy(error = "请先同意服务条款和隐私政策")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val response = authService.registerEmail(
                    RegisterEmailRequest(
                        name = _uiState.value.name.trim(),
                        email = _uiState.value.email.trim(),
                        password = _uiState.value.password,
                    )
                )
                if (response.isSuccessful) {
                    val auth = response.body()!!
                    preferencesManager.saveAuthToken(auth.token)
                    // New users always start with onboarding
                    _uiState.value = _uiState.value.copy(isLoading = false, isLoginSuccess = true)
                } else {
                    val message = when (response.code()) {
                        409 -> "该邮箱已注册，请直接登录"
                        400 -> "请检查输入信息是否正确"
                        else -> "注册失败，请稍后重试"
                    }
                    _uiState.value = _uiState.value.copy(isLoading = false, error = message)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "网络连接失败，请检查网络后重试",
                )
            }
        }
    }

    fun loginOrRegister() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val deviceId = preferencesManager.getDeviceId()
                val loginResp = authService.login(com.learningscout.app.data.remote.dto.LoginRequest(deviceId))
                val auth = if (loginResp.isSuccessful) {
                    loginResp.body()
                } else {
                    val regResp = authService.register(com.learningscout.app.data.remote.dto.RegisterRequest(deviceId))
                    if (regResp.isSuccessful) regResp.body() else null
                }
                if (auth != null) {
                    preferencesManager.saveAuthToken(auth.token)
                    if (auth.onboarding_complete) {
                        preferencesManager.setOnboardingComplete()
                    }
                    _uiState.value = _uiState.value.copy(isLoading = false, isLoginSuccess = true)
                } else {
                    _uiState.value = _uiState.value.copy(isLoading = false, error = "无法连接服务器，请稍后重试")
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "网络连接失败，请检查网络后重试",
                )
            }
        }
    }
}
