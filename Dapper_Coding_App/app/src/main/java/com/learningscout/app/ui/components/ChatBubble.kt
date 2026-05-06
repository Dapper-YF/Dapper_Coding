package com.learningscout.app.ui.components

import android.util.Log
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.learningscout.app.ui.theme.GradientEnd
import com.learningscout.app.ui.theme.GradientStart

@Composable
@OptIn(ExperimentalFoundationApi::class)
fun UserBubble(
    message: String,
    onLongPress: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = androidx.compose.foundation.layout.Arrangement.End,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.82f)
                .clip(RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp, bottomStart = 18.dp, bottomEnd = 4.dp))
                .background(MaterialTheme.colorScheme.primary)
                .combinedClickable(
                    onClick = {},
                    onLongClick = onLongPress,
                )
                .padding(horizontal = 18.dp, vertical = 14.dp),
        ) {
            Text(
                text = message,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onPrimary,
            )
        }
    }
}

@Composable
@OptIn(ExperimentalFoundationApi::class)
fun AiBubble(
    message: String,
    thinking: String = "",
    isStreaming: Boolean = false,
    isThinkingExpanded: Boolean = false,
    onToggleThinking: () -> Unit = {},
    onLongPress: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val showLoading = isStreaming && message.isBlank() && thinking.isBlank()

    val cursorTransition = if (isStreaming && !showLoading) {
        rememberInfiniteTransition(label = "cursor")
    } else null
    val cursorAlpha = if (cursorTransition != null) {
        cursorTransition.animateFloat(
            initialValue = 1f,
            targetValue = 0f,
            animationSpec = infiniteRepeatable(
                animation = tween(durationMillis = 700),
                repeatMode = RepeatMode.Reverse,
            ),
            label = "cursorAlpha",
        ).value
    } else 1f

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Start,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.92f)
                .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 18.dp, bottomStart = 18.dp, bottomEnd = 18.dp))
                .background(MaterialTheme.colorScheme.surfaceContainerLow)
                .padding(horizontal = 18.dp, vertical = 14.dp),
        ) {
            Column {
                // AI identity header
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Psychology,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Learning Scout AI",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
                Spacer(modifier = Modifier.height(10.dp))

                // Loading state: before any token arrives
                if (showLoading) {
                    ThinkingLoading()
                }

                // Thinking section (auto-expanded during streaming, collapsible after)
                if (thinking.isNotBlank()) {
                    ThinkingSection(
                        thinking = thinking,
                        isExpanded = isStreaming || isThinkingExpanded,
                        canToggle = !isStreaming,
                        onToggle = onToggleThinking,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }

                // Main response content (long-press to copy)
                if (message.isNotBlank()) {
                    Box(
                        modifier = Modifier.combinedClickable(
                            onClick = {},
                            onLongClick = onLongPress,
                        ),
                    ) {
                        val safeForMarkdown = message.length <= 8000 &&
                            message.count { it == '`' } % 2 == 0 &&
                            message.count { it == '*' } % 2 == 0
                        if (safeForMarkdown) {
                            MarkdownText(content = message)
                        } else {
                            Log.w("ChatBubble", "Skipping MarkdownText — len=${message.length}, backticks=${message.count { it == '`' }}, stars=${message.count { it == '*' }}")
                            Text(
                                text = message,
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                        }
                    }
                }

                // Cursor for streaming
                if (isStreaming && !showLoading) {
                    Text(
                        text = "▎",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.primary.copy(alpha = cursorAlpha),
                    )
                }
            }
        }
    }
}

@Composable
private fun ThinkingLoading() {
    val infiniteTransition = rememberInfiniteTransition(label = "thinkingDots")
    val dot1 by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(600, delayMillis = 0),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "dot1",
    )
    val dot2 by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(600, delayMillis = 200),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "dot2",
    )
    val dot3 by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(600, delayMillis = 400),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "dot3",
    )
    val dots = listOf(dot1, dot2, dot3)
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            text = "正在思考",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        dots.forEach { alpha ->
            Text(
                text = ".",
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = alpha),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun ThinkingSection(
    thinking: String,
    isExpanded: Boolean,
    canToggle: Boolean,
    onToggle: () -> Unit,
) {
    val bgColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
    val textColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.75f)

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(bgColor)
            .then(if (canToggle) Modifier.clickable { onToggle() } else Modifier)
            .padding(10.dp),
    ) {
        // Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "💭",
                fontSize = 13.sp,
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = if (canToggle && !isExpanded) "思考过程（点击展开）" else "思考过程",
                style = MaterialTheme.typography.labelSmall,
                color = textColor,
            )
            Spacer(modifier = Modifier.weight(1f))
            if (canToggle) {
                Icon(
                    imageVector = if (isExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                    contentDescription = if (isExpanded) "收起" else "展开",
                    tint = textColor,
                    modifier = Modifier.size(16.dp),
                )
            }
        }

        // Content
        AnimatedVisibility(visible = isExpanded) {
            Text(
                text = thinking,
                style = MaterialTheme.typography.bodySmall,
                color = textColor,
                modifier = Modifier.padding(top = 6.dp),
            )
        }
    }
}

@Composable
fun ChatBubble(
    role: String,
    content: String,
    thinking: String = "",
    isStreaming: Boolean = false,
    isThinkingExpanded: Boolean = false,
    onToggleThinking: () -> Unit = {},
    onLongPress: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    if (role == "user") {
        UserBubble(message = content, onLongPress = onLongPress, modifier = modifier)
    } else {
        AiBubble(
            message = content,
            thinking = thinking,
            isStreaming = isStreaming,
            isThinkingExpanded = isThinkingExpanded,
            onToggleThinking = onToggleThinking,
            onLongPress = onLongPress,
            modifier = modifier,
        )
    }
}
