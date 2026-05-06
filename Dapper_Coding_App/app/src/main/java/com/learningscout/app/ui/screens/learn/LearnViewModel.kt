package com.learningscout.app.ui.screens.learn

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.learningscout.app.data.remote.ApiService
import com.learningscout.app.data.remote.dto.DailyLessonResponse
import com.learningscout.app.data.remote.dto.DigestResponse
import com.learningscout.app.data.remote.dto.UserStatsDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LearnUiState(
    val lesson: DailyLessonResponse? = null,
    val digest: DigestResponse? = null,
    val stats: UserStatsDto? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class LearnViewModel @Inject constructor(
    private val apiService: ApiService,
) : ViewModel() {

    private val _uiState = MutableStateFlow(LearnUiState())
    val uiState: StateFlow<LearnUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun refresh() {
        loadAll()
    }

    private fun loadAll() {
        if (_uiState.value.isLoading) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val lessonDeferred = async { runCatching { apiService.getDailyLesson() } }
                val digestDeferred = async { runCatching { apiService.getLatestDigest() } }
                val statsDeferred = async { runCatching { apiService.getUserStats() } }

                val lesson = lessonDeferred.await().getOrNull()
                val digest = digestDeferred.await().getOrNull()
                val stats = statsDeferred.await().getOrNull()

                _uiState.value = _uiState.value.copy(
                    lesson = lesson,
                    digest = digest,
                    stats = stats,
                    isLoading = false,
                    error = null,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "加载失败，请检查网络后重试",
                )
            }
        }
    }
}
