package com.cz.familycut.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.cz.familycut.data.remote.MeasurementResponse
import com.cz.familycut.ui.components.AppPage
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassTextField
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.SectionCard
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun WeightEntryScreen(
    innerPadding: PaddingValues,
    weightInput: String,
    bodyFatInput: String,
    lastWeightSubmitAt: Long?,
    recentMeasurements: List<MeasurementResponse>,
    onWeightChange: (String) -> Unit,
    onBodyFatChange: (String) -> Unit,
    onSave: () -> Unit,
    onSaved: () -> Unit,
    onSavedHandled: () -> Unit
) {
    LaunchedEffect(lastWeightSubmitAt) {
        if (lastWeightSubmitAt != null) {
            onSaved()
            onSavedHandled()
        }
    }

    AppPage(innerPadding = innerPadding) {
        LazyColumn(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    HeroCard(
                        title = "晨重记录",
                        subtitle = "提交成功后会自动返回首页，避免你卡在体重页。"
                    )
                    HeroPillRow(
                        "最近 ${recentMeasurements.size} 条",
                        if (bodyFatInput.isBlank()) "体脂可选" else "体脂已填写",
                        "晨起优先记录"
                    )
                }
            }
            item {
                SectionCard(title = "录入体征", subtitle = "建议晨起空腹称重，保持时间点稳定。") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        GlassTextField(
                            value = weightInput,
                            onValueChange = onWeightChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "体重（kg）"
                        )
                        GlassTextField(
                            value = bodyFatInput,
                            onValueChange = onBodyFatChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "体脂率（可选）"
                        )
                        GlassPrimaryButton(
                            text = "提交晨重",
                            onClick = onSave,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }
            item {
                SectionCard(title = "最近体重", subtitle = "先看趋势，不用每次手动翻历史。") {
                    if (recentMeasurements.isEmpty()) {
                        Text("还没有体重记录。")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            recentMeasurements.take(10).forEach { item ->
                                Text(
                                    text = "${formatMeasurementTime(item.measuredAt)}  ${item.weightKg} kg" +
                                        (item.bodyFatPct?.let { " / ${it}%" } ?: ""),
                                    style = MaterialTheme.typography.bodyLarge
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun formatMeasurementTime(raw: String): String {
    return runCatching {
        Instant.parse(raw)
            .atZone(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern("M月d日 HH:mm"))
    }.getOrDefault(raw)
}
