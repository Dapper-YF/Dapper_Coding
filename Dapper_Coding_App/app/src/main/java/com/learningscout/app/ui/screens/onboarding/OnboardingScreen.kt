package com.learningscout.app.ui.screens.onboarding

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.learningscout.app.data.remote.dto.OptionNode
import com.learningscout.app.data.remote.dto.QuestionNode
import com.learningscout.app.data.remote.dto.UserProfile

@Composable
fun OnboardingScreen(
    onComplete: () -> Unit,
    viewModel: OnboardingViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 48.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        LinearProgressIndicator(
            progress = { uiState.progress },
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 32.dp),
        )

        when {
            uiState.isLoading -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator()
                }
            }

            uiState.error != null -> {
                Text(
                    text = uiState.error ?: "",
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyLarge,
                    textAlign = TextAlign.Center,
                )
            }

            uiState.isComplete -> {
                CompleteContent(
                    profile = uiState.profile,
                    onComplete = onComplete,
                )
            }

            uiState.currentQuestion != null -> {
                QuestionCard(
                    question = uiState.currentQuestion!!,
                    selectedOptionIds = uiState.selectedOptionIds,
                    onSelectOption = { viewModel.selectOption(it) },
                    onConfirmMultiChoice = { viewModel.confirmMultiChoice() },
                    onSkip = { viewModel.skipQuestion() },
                )
            }

            else -> {
                SubmitContent(
                    onSubmit = { viewModel.completeOnboarding() },
                    isSubmitting = uiState.isSubmitting,
                )
            }
        }
    }
}

@Composable
private fun QuestionCard(
    question: QuestionNode,
    selectedOptionIds: Set<String>,
    onSelectOption: (OptionNode) -> Unit,
    onConfirmMultiChoice: () -> Unit,
    onSkip: () -> Unit,
) {
    val isMulti = question.type == "multi_choice"
    val maxSelect = question.max_select ?: Int.MAX_VALUE

    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .widthIn(max = 480.dp)
            .animateContentSize(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
        ),
        shape = MaterialTheme.shapes.large,
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = question.text,
                style = MaterialTheme.typography.titleLarge,
                textAlign = TextAlign.Center,
            )

            if (isMulti && maxSelect < Int.MAX_VALUE) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "已选 ${selectedOptionIds.size}/$maxSelect 项",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Spacer(modifier = Modifier.height(20.dp))

            question.options.forEach { option ->
                val isSelected = option.id in selectedOptionIds
                val atLimit = isMulti && selectedOptionIds.size >= maxSelect && !isSelected

                if (isMulti) {
                    OutlinedButton(
                        onClick = { onSelectOption(option) },
                        modifier = Modifier.fillMaxWidth(),
                        shape = MaterialTheme.shapes.medium,
                        enabled = !atLimit,
                        border = if (isSelected) {
                            BorderStroke(2.dp, MaterialTheme.colorScheme.primary)
                        } else {
                            ButtonDefaults.outlinedButtonBorder
                        },
                    ) {
                        Text(
                            text = option.text,
                            modifier = Modifier.padding(vertical = 4.dp),
                            color = if (isSelected) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurface
                            },
                        )
                    }
                } else {
                    Button(
                        onClick = { onSelectOption(option) },
                        modifier = Modifier.fillMaxWidth(),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Text(
                            text = option.text,
                            modifier = Modifier.padding(vertical = 4.dp),
                        )
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            if (isMulti) {
                Button(
                    onClick = onConfirmMultiChoice,
                    modifier = Modifier.fillMaxWidth(),
                    shape = MaterialTheme.shapes.medium,
                    enabled = selectedOptionIds.isNotEmpty(),
                ) {
                    Text(
                        text = "下一步",
                        modifier = Modifier.padding(vertical = 4.dp),
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            TextButton(onClick = onSkip) {
                Text(
                    text = "不确定",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun SubmitContent(onSubmit: () -> Unit, isSubmitting: Boolean = false) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .widthIn(max = 480.dp),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
        ),
        shape = MaterialTheme.shapes.large,
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = "准备就绪",
                style = MaterialTheme.typography.headlineMedium,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "你已经回答了所有问题，点击完成来生成你的专属学习路径。",
                style = MaterialTheme.typography.bodyLarge,
                textAlign = TextAlign.Center,
            )
            Spacer(modifier = Modifier.height(24.dp))
            Button(
                onClick = onSubmit,
                modifier = Modifier.fillMaxWidth(),
                shape = MaterialTheme.shapes.medium,
                enabled = !isSubmitting,
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(
                        modifier = Modifier.height(20.dp),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text(
                        text = "完成",
                        modifier = Modifier.padding(vertical = 4.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun CompleteContent(
    profile: UserProfile?,
    onComplete: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        // Welcome header
        Text(
            text = "欢迎加入\nLearning Scout",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "你的专属学习路径已经就绪",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )

        if (profile != null) {
            Spacer(modifier = Modifier.height(20.dp))
            ProfileSummary(profile)
        }

        Spacer(modifier = Modifier.height(28.dp))
        Button(
            onClick = onComplete,
            modifier = Modifier.fillMaxWidth(),
            shape = MaterialTheme.shapes.medium,
        ) {
            Text(
                text = "开始学习",
                modifier = Modifier.padding(vertical = 4.dp),
            )
        }
    }
}

@Composable
private fun ProfileSummary(profile: UserProfile) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.Start,
    ) {
        // Selected interests as gradient badges
        if (profile.interests.isNotEmpty()) {
            val readableInterests = profile.interests.mapNotNull { INTEREST_LABEL_MAP[it] ?: it }
            SectionTitle("兴趣领域")
            Spacer(modifier = Modifier.height(8.dp))
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                for (interest in readableInterests) {
                    val desc = TOPIC_DESCRIPTIONS[interest]
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f))
                            .padding(horizontal = 14.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = "▸",
                            color = MaterialTheme.colorScheme.primary,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column {
                            Text(
                                text = interest,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                            )
                            if (desc != null) {
                                Text(
                                    text = desc,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                }
            }
            Spacer(modifier = Modifier.height(16.dp))
        }

        // Sub-topics (interests_detail)
        val detailItems = mutableListOf<String>()
        profile.interests_detail?.forEach { (_, subs) ->
            subs.forEach { sub ->
                DETAIL_LABEL_MAP[sub]?.let { detailItems.add(it) }
            }
        }
        if (detailItems.isNotEmpty()) {
            SectionTitle("细分方向")
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                detailItems.take(6).forEach { item ->
                    ChipBadge(item)
                }
            }
            Spacer(modifier = Modifier.height(16.dp))
        }

        // Learning goals
        if (profile.learning_goals.isNotEmpty()) {
            SectionTitle("学习目标")
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                profile.learning_goals.take(4).forEach { goal ->
                    val label = LEARNING_GOAL_LABEL_MAP[goal] ?: goal
                    ChipBadge(label)
                }
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        fontWeight = FontWeight.Medium,
    )
}

@Composable
private fun ChipBadge(text: String) {
    Text(
        text = text,
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.5f))
            .padding(horizontal = 10.dp, vertical = 4.dp),
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSecondaryContainer,
    )
}

private val INTEREST_LABEL_MAP = mapOf(
    "cs" to "计算机科学", "physics" to "物理学", "math" to "数学", "other" to "其他领域",
)

private val DETAIL_LABEL_MAP = mapOf(
    "artificial_intelligence" to "人工智能", "machine_learning" to "机器学习",
    "deep_learning" to "深度学习", "nlp" to "自然语言处理",
    "computer_vision" to "计算机视觉", "reinforcement_learning" to "强化学习",
    "web_development" to "Web 开发", "web_frontend" to "前端开发",
    "web_backend" to "后端开发", "full_stack" to "全栈开发",
    "mobile_development" to "移动开发", "android" to "Android",
    "ios" to "iOS", "cross_platform" to "跨平台",
    "game_development" to "游戏开发", "algorithms_data_structures" to "算法与数据结构",
    "cybersecurity" to "网络安全", "data_science" to "数据科学",
)

private val TOPIC_DESCRIPTIONS = mapOf(
    "机器学习" to "掌握监督学习、无监督学习与模型评估的核心方法",
    "深度学习" to "理解神经网络、CNN、RNN 与 Transformer 架构",
    "自然语言处理" to "探索大语言模型、文本生成与语义理解的前沿技术",
    "计算机视觉" to "学习图像识别、目标检测与图像生成技术",
    "前端开发" to "React、Vue 等现代框架与响应式设计",
    "后端开发" to "API 设计、数据库优化与服务端架构",
    "移动开发" to "Android、iOS 原生与跨平台应用开发",
    "游戏开发" to "Unity、Unreal 引擎与游戏设计模式",
    "算法与数据结构" to "LeetCode 刷题指南与算法思维训练",
    "网络安全" to "渗透测试、安全防御与密码学基础",
    "数据科学" to "数据分析、可视化与大数据处理技术",
    "物理学" to "从经典力学到现代物理的系统学习",
    "数学" to "微积分、线性代数与概率统计的核心概念",
)

private val LEARNING_GOAL_LABEL_MAP = mapOf(
    "career_switch" to "职业转型",
    "skill_upgrade" to "技能提升",
    "hobby_explore" to "兴趣探索",
    "academic" to "学术研究",
    "project_build" to "项目实战",
)
