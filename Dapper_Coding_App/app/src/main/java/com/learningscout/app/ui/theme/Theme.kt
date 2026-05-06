package com.learningscout.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val LightColorScheme = lightColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    primaryContainer = PrimaryContainer,
    onPrimaryContainer = OnPrimaryContainer,
    secondary = Secondary,
    onSecondary = OnSecondary,
    secondaryContainer = SecondaryContainer,
    onSecondaryContainer = Color(0xFFFEFCFF),
    tertiary = Tertiary,
    onTertiary = OnTertiary,
    tertiaryContainer = TertiaryContainer,
    onTertiaryContainer = Color(0xFFFCFCFF),
    error = Error,
    onError = OnError,
    errorContainer = ErrorContainer,
    onErrorContainer = OnErrorContainer,
    background = Background,
    onBackground = OnBackground,
    surface = Surface,
    onSurface = OnSurface,
    surfaceVariant = SurfaceVariant,
    onSurfaceVariant = OnSurfaceVariant,
    outline = Outline,
    outlineVariant = OutlineVariant,
    surfaceTint = SurfaceTint,
    inverseSurface = InverseSurface,
    inverseOnSurface = InverseOnSurface,
    inversePrimary = InversePrimary,
    surfaceContainerLowest = SurfaceContainerLowest,
    surfaceContainerLow = SurfaceContainerLow,
    surfaceContainer = SurfaceContainer,
    surfaceContainerHigh = SurfaceContainerHigh,
    surfaceContainerHighest = SurfaceContainerHighest,
    surfaceBright = SurfaceBright,
    surfaceDim = SurfaceDim,
)

private val DarkColorScheme = darkColorScheme(
    primary = PrimaryFixedDim,
    onPrimary = Color(0xFF0A1628),
    primaryContainer = PrimaryContainer,
    onPrimaryContainer = OnPrimaryContainer,
    secondary = SecondaryFixedDim,
    onSecondary = OnSecondaryFixed,
    secondaryContainer = SecondaryContainer,
    onSecondaryContainer = Color(0xFFFEFCFF),
    tertiary = TertiaryFixedDim,
    onTertiary = OnTertiaryFixed,
    tertiaryContainer = TertiaryContainer,
    onTertiaryContainer = Color(0xFFFCFCFF),
    error = Error,
    onError = OnError,
    errorContainer = ErrorContainer,
    onErrorContainer = OnErrorContainer,
    background = InverseSurface,
    onBackground = InverseOnSurface,
    surface = InverseSurface,
    onSurface = InverseOnSurface,
    surfaceVariant = Color(0xFF2A3448),
    onSurfaceVariant = SurfaceVariant,
    outline = OutlineVariant,
    outlineVariant = Outline,
    surfaceTint = PrimaryFixedDim,
    inverseSurface = InverseOnSurface,
    inverseOnSurface = InverseSurface,
    inversePrimary = Primary,
    surfaceContainerLowest = Color(0xFF0D1624),
    surfaceContainerLow = Color(0xFF151F32),
    surfaceContainer = Color(0xFF1A2640),
    surfaceContainerHigh = Color(0xFF223050),
    surfaceContainerHighest = Color(0xFF2A3A60),
    surfaceBright = Color(0xFF2A3A60),
    surfaceDim = Color(0xFF0D1624),
)

@Composable
fun LearningScoutTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.surface.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = LearningScoutTypography,
        shapes = LearningScoutShapes,
        content = content,
    )
}
