package com.cz.familycut.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.SnackbarData
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cz.familycut.ui.theme.CloudGlassStrong
import com.cz.familycut.ui.theme.GraphiteNight
import com.cz.familycut.ui.theme.GlacierBlue
import com.cz.familycut.ui.theme.GlacierBlueDark
import com.cz.familycut.ui.theme.SilverMist
import com.cz.familycut.ui.theme.SkyStroke

@Composable
fun AppPage(
    innerPadding: PaddingValues = PaddingValues(),
    content: @Composable () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.85f),
                        SilverMist.copy(alpha = 0.96f),
                        MaterialTheme.colorScheme.background
                    ),
                    radius = 1600f
                )
            )
            .padding(innerPadding)
    ) {
        content()
    }
}

@Composable
fun AppPageColumn(
    innerPadding: PaddingValues = PaddingValues(),
    content: @Composable () -> Unit
) {
    AppPage(innerPadding = innerPadding) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            content()
        }
    }
}

@Composable
fun AppPageList(
    innerPadding: PaddingValues = PaddingValues(),
    content: LazyColumnScopeBuilder
) {
    AppPage(innerPadding = innerPadding) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 20.dp),
            contentPadding = PaddingValues(vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            content.build(this)
        }
    }
}

fun interface LazyColumnScopeBuilder {
    fun build(scope: androidx.compose.foundation.lazy.LazyListScope)
}

@Composable
fun HeroCard(
    title: String,
    subtitle: String,
    modifier: Modifier = Modifier
) {
    ElevatedCard(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(32.dp),
        colors = CardDefaults.elevatedCardColors(
            containerColor = GlacierBlueDark,
            contentColor = Color.White
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 12.dp)
    ) {
        Column(
            modifier = Modifier.padding(22.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.86f)
            )
        }
    }
}

@Composable
fun MetricCard(
    label: String,
    value: String,
    modifier: Modifier = Modifier
) {
    ElevatedCard(
        modifier = modifier.border(BorderStroke(1.dp, SkyStroke), RoundedCornerShape(24.dp)),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 6.dp)
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelLarge,
                color = GlacierBlueDark
            )
            Text(
                text = value,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Composable
fun SectionCard(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    content: @Composable () -> Unit
) {
    ElevatedCard(
        modifier = modifier
            .fillMaxWidth()
            .border(BorderStroke(1.dp, SkyStroke), RoundedCornerShape(28.dp)),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 8.dp)
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(text = title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                if (subtitle != null) {
                    Text(
                        text = subtitle,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.72f)
                    )
                }
            }
            content()
        }
    }
}

@Composable
fun HeroPillRow(vararg items: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items.filter { it.isNotBlank() }.take(3).forEach { item ->
            Card(
                shape = CircleShape,
                colors = CardDefaults.cardColors(containerColor = CloudGlassStrong),
                border = BorderStroke(1.dp, SkyStroke)
            ) {
                Text(
                    text = item,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                    style = MaterialTheme.typography.labelMedium,
                    color = GlacierBlue
                )
            }
        }
    }
}

@Composable
fun GlassPrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true
) {
    Button(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        shape = RoundedCornerShape(22.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = GlacierBlueDark,
            contentColor = Color.White,
            disabledContainerColor = GlacierBlueDark.copy(alpha = 0.36f),
            disabledContentColor = Color.White.copy(alpha = 0.72f)
        ),
        elevation = ButtonDefaults.buttonElevation(defaultElevation = 10.dp)
    ) {
        Text(text)
    }
}

@Composable
fun GlassSecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        shape = RoundedCornerShape(22.dp),
        border = BorderStroke(1.dp, SkyStroke),
        colors = ButtonDefaults.outlinedButtonColors(
            containerColor = CloudGlassStrong.copy(alpha = 0.72f),
            contentColor = GlacierBlueDark,
            disabledContainerColor = CloudGlassStrong.copy(alpha = 0.36f),
            disabledContentColor = GlacierBlueDark.copy(alpha = 0.4f)
        )
    ) {
        Text(text)
    }
}

@Composable
fun GlassTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier,
        enabled = enabled,
        label = { Text(label) },
        shape = RoundedCornerShape(22.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = GlacierBlue,
            unfocusedBorderColor = SkyStroke,
            focusedContainerColor = CloudGlassStrong.copy(alpha = 0.8f),
            unfocusedContainerColor = CloudGlassStrong.copy(alpha = 0.58f),
            focusedLabelColor = GlacierBlueDark,
            unfocusedLabelColor = MaterialTheme.colorScheme.onSurfaceVariant,
            cursorColor = GlacierBlueDark,
            focusedTextColor = MaterialTheme.colorScheme.onSurface,
            unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
            disabledContainerColor = CloudGlassStrong.copy(alpha = 0.3f),
            disabledBorderColor = SkyStroke.copy(alpha = 0.45f),
            disabledTextColor = GraphiteNight.copy(alpha = 0.54f)
        )
    )
}

@Composable
fun GlassFilterChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(label) },
        shape = RoundedCornerShape(22.dp),
        border = BorderStroke(1.dp, SkyStroke),
        colors = FilterChipDefaults.filterChipColors(
            selectedContainerColor = GlacierBlue.copy(alpha = 0.18f),
            selectedLabelColor = GlacierBlueDark,
            selectedLeadingIconColor = GlacierBlueDark,
            containerColor = CloudGlassStrong.copy(alpha = 0.6f),
            labelColor = MaterialTheme.colorScheme.onSurfaceVariant
        )
    )
}

@Composable
fun GlassSnackbarHost(hostState: SnackbarHostState) {
    SnackbarHost(hostState = hostState) { data: SnackbarData ->
        Card(
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.96f)),
            border = BorderStroke(1.dp, SkyStroke),
            elevation = CardDefaults.cardElevation(defaultElevation = 10.dp)
        ) {
            Text(
                text = data.visuals.message,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}
