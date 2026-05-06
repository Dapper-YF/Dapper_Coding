package com.learningscout.app.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LearningScoutTopAppBar(
    modifier: Modifier = Modifier,
    onDarkModeToggle: (() -> Unit)? = null,
    onRefreshClick: (() -> Unit)? = null,
) {
    var syncPressed by remember { mutableStateOf(false) }

    val syncScale by animateFloatAsState(
        targetValue = if (syncPressed) 0.92f else 1f,
        animationSpec = tween(durationMillis = 200),
        label = "syncScale",
    )

    TopAppBar(
        modifier = modifier,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
            ) {
                Text(
                    text = "Learning Scout",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        },
        actions = {
            IconButton(onClick = { onDarkModeToggle?.invoke() }) {
                Icon(
                    imageVector = Icons.Default.DarkMode,
                    contentDescription = "深色模式",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.65f),
                    modifier = Modifier.size(20.dp),
                )
            }
            IconButton(
                onClick = {
                    syncPressed = !syncPressed
                    onRefreshClick?.invoke()
                },
                modifier = Modifier.scale(syncScale),
            ) {
                Icon(
                    imageVector = Icons.Default.Sync,
                    contentDescription = "刷新",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.65f),
                    modifier = Modifier.size(20.dp),
                )
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f),
        ),
    )
}
