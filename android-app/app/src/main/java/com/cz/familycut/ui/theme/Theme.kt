package com.cz.familycut.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.unit.dp
import com.cz.familycut.data.model.ThemeMode

private val LightColors = lightColorScheme(
    primary = GlacierBlue,
    onPrimary = MoonText,
    primaryContainer = Color(0xFFDBE8F8),
    onPrimaryContainer = GlacierBlueDark,
    secondary = GlacierBlueDark,
    onSecondary = MoonText,
    background = SilverMist,
    surface = CloudGlass,
    surfaceVariant = AuroraSurface,
    onSurface = SlateText,
    onSurfaceVariant = SlateMuted,
    outline = SkyStroke,
    error = DangerRose
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF8EB8F0),
    onPrimary = GraphiteNight,
    primaryContainer = Color(0xFF203C5F),
    onPrimaryContainer = MoonText,
    secondary = Color(0xFFBBD1EC),
    onSecondary = GraphiteNight,
    background = GraphiteNight,
    surface = GraphiteSurface,
    surfaceVariant = Color(0xFF1E3047),
    onSurface = MoonText,
    onSurfaceVariant = Color(0xFFD1DCE9),
    outline = Color(0x40FFFFFF),
    error = Color(0xFFFFB4AB)
)

private val FamilyCutShapes = Shapes(
    extraSmall = RoundedCornerShape(16.dp),
    small = RoundedCornerShape(20.dp),
    medium = RoundedCornerShape(24.dp),
    large = RoundedCornerShape(30.dp),
    extraLarge = RoundedCornerShape(36.dp)
)

@Composable
fun FamilyCutTheme(
    themeMode: ThemeMode,
    content: @Composable () -> Unit
) {
    val darkTheme = when (themeMode) {
        ThemeMode.FOLLOW_SYSTEM -> isSystemInDarkTheme()
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
    }

    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        shapes = FamilyCutShapes,
        typography = FamilyCutTypography,
        content = content
    )
}
