package com.learningscout.app.ui.screens.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.learningscout.app.data.local.PreferencesManager
import com.learningscout.app.data.remote.AuthService
import com.learningscout.app.data.remote.dto.AnswerEntry
import com.learningscout.app.data.remote.dto.CompleteOnboardingRequest
import com.learningscout.app.data.remote.dto.OptionNode
import com.learningscout.app.data.remote.dto.QuestionNode
import com.learningscout.app.data.remote.dto.UserProfile
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OnboardingUiState(
    val currentQuestion: QuestionNode? = null,
    val progress: Float = 0f,
    val isLoading: Boolean = true,
    val isSubmitting: Boolean = false,
    val error: String? = null,
    val isComplete: Boolean = false,
    val profile: UserProfile? = null,
    val selectedOptionIds: Set<String> = emptySet(),
)

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val authService: AuthService,
    private val preferencesManager: PreferencesManager,
) : ViewModel() {

    private val _uiState = MutableStateFlow(OnboardingUiState())
    val uiState: StateFlow<OnboardingUiState> = _uiState.asStateFlow()

    private val questionQueue = ArrayDeque<QuestionNode>()
    private val answers = mutableMapOf<String, MutableList<String>>()
    private var totalQuestionEstimate = 0
    private var answeredCount = 0

    init {
        loadTree()
    }

    fun selectOption(option: OptionNode) {
        val current = _uiState.value.currentQuestion ?: return
        val isMulti = current.type == "multi_choice"

        if (isMulti) {
            val selected = _uiState.value.selectedOptionIds.toMutableSet()
            val answerList = answers.getOrPut(current.id) { mutableListOf() }

            if (option.id in selected) {
                selected.remove(option.id)
                answerList.remove(option.id)
            } else {
                selected.add(option.id)
                if (option.id !in answerList) {
                    answerList.add(option.id)
                }
            }
            _uiState.value = _uiState.value.copy(selectedOptionIds = selected)
        } else {
            answers.getOrPut(current.id) { mutableListOf() }.apply {
                clear()
                add(option.id)
            }
            answeredCount++
            questionQueue.removeFirst()

            option.children?.let { children ->
                children.reversed().forEach { questionQueue.addFirst(it) }
            }

            advanceQuestion()
        }
    }

    fun confirmMultiChoice() {
        val current = _uiState.value.currentQuestion ?: return
        val selected = _uiState.value.selectedOptionIds

        if (selected.isEmpty()) return

        answeredCount++
        questionQueue.removeFirst()

        // Push children of all selected options in reverse order
        current.options
            .filter { it.id in selected }
            .reversed()
            .forEach { option ->
                option.children?.let { children ->
                    children.reversed().forEach { questionQueue.addFirst(it) }
                }
            }

        advanceQuestion()
    }

    fun skipQuestion() {
        val current = _uiState.value.currentQuestion ?: return
        answers.getOrPut(current.id) { mutableListOf() }.apply {
            clear()
            add("unsure")
        }
        answeredCount++
        questionQueue.removeFirst()
        advanceQuestion()
    }

    fun completeOnboarding() {
        if (_uiState.value.isSubmitting) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSubmitting = true, error = null)
            try {
                val token = preferencesManager.getAuthToken() ?: return@launch
                val answerList = answers.map { (qid, ans) ->
                    AnswerEntry(question_id = qid, answer = ans.toList())
                }
                val response = authService.completeOnboarding(
                    authorization = "Bearer $token",
                    request = CompleteOnboardingRequest(answers = answerList),
                )
                if (response.isSuccessful) {
                    preferencesManager.setOnboardingComplete()
                    _uiState.value = _uiState.value.copy(
                        isComplete = true,
                        isSubmitting = false,
                        profile = response.body()?.profile,
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isSubmitting = false,
                        error = "提交失败，请重试",
                    )
                }
            } catch (_: Exception) {
                _uiState.value = _uiState.value.copy(
                    isSubmitting = false,
                    error = "提交失败，请检查网络连接后重试",
                )
            }
        }
    }

    private fun loadTree() {
        viewModelScope.launch {
            try {
                val token = preferencesManager.getAuthToken() ?: return@launch
                val response = authService.getOnboardingTree("Bearer $token")
                if (response.isSuccessful) {
                    val tree = response.body()?.tree ?: emptyList()
                    questionQueue.clear()
                    questionQueue.addAll(tree)
                    totalQuestionEstimate = countAllQuestions(tree)
                    advanceQuestion()
                } else {
                    _uiState.value = OnboardingUiState(
                        isLoading = false,
                        error = "加载问卷失败",
                    )
                }
            } catch (_: Exception) {
                _uiState.value = OnboardingUiState(
                    isLoading = false,
                    error = "加载问卷失败，请检查网络连接",
                )
            }
        }
    }

    private fun advanceQuestion() {
        if (questionQueue.isEmpty()) {
            val progress = if (totalQuestionEstimate > 0) 1f else 0f
            _uiState.value = _uiState.value.copy(
                currentQuestion = null,
                progress = progress,
                isLoading = false,
                selectedOptionIds = emptySet(),
            )
        } else {
            val progress = if (totalQuestionEstimate > 0) {
                answeredCount.toFloat() / totalQuestionEstimate
            } else 0f
            _uiState.value = _uiState.value.copy(
                currentQuestion = questionQueue.first(),
                progress = progress.coerceIn(0f, 1f),
                isLoading = false,
                selectedOptionIds = emptySet(),
            )
        }
    }

    private fun countAllQuestions(nodes: List<QuestionNode>): Int {
        var count = 0
        for (node in nodes) {
            count++
            node.children?.let { count += countAllQuestions(it) }
            for (opt in node.options) {
                opt.children?.let { count += countAllQuestions(it) }
            }
        }
        return count
    }
}
