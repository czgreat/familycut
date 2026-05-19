package com.cz.familycut.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.cz.familycut.data.model.UserSession
import com.cz.familycut.data.remote.DailyReportResponse
import com.cz.familycut.data.remote.MealEntryResponse
import com.cz.familycut.data.remote.MeasurementResponse
import com.cz.familycut.data.remote.MediaAssetResponse
import com.cz.familycut.ui.components.AppPage
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassSecondaryButton
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.MetricCard
import com.cz.familycut.ui.components.SectionCard
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun HomeScreen(
    innerPadding: PaddingValues,
    session: UserSession?,
    dashboardLoading: Boolean,
    recentMeasurements: List<MeasurementResponse>,
    recentMeals: List<MealEntryResponse>,
    recentSelfies: List<MediaAssetResponse>,
    todayReport: DailyReportResponse?,
    onOpenWeightEntry: () -> Unit,
    onOpenMeals: () -> Unit,
    onOpenSelfies: () -> Unit,
    onOpenReports: () -> Unit,
    onOpenSettings: () -> Unit,
    onRefresh: () -> Unit
) {
    val latestMeasurement = recentMeasurements.firstOrNull()
    val todayKcal = todayReport.payloadNumber("intake", "kcal")
    val tdee = todayReport.payloadNumber("tdee")

    AppPage(innerPadding = innerPadding) {
        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    HeroCard(
                        title = "你好，${session?.displayName ?: "成员"}",
                        subtitle = if (dashboardLoading) {
                            "正在同步体重、餐食、自拍和日报数据。"
                        } else {
                            "现在首页已经直接串起晨重、餐食、自拍和日报四条主线。"
                        }
                    )
                    HeroPillRow(
                        "摄入 ${todayKcal?.toInt() ?: 0} kcal",
                        "TDEE ${tdee?.toInt() ?: 0} kcal",
                        "自拍 ${recentSelfies.size}"
                    )
                }
            }

            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    MetricCard(
                        label = "最近体重",
                        value = latestMeasurement?.let { "${it.weightKg} kg" } ?: "暂无",
                        modifier = Modifier.weight(1f)
                    )
                    MetricCard(
                        label = "今日摄入",
                        value = todayKcal?.let { "${it.toInt()} kcal" } ?: "待生成",
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    MetricCard(
                        label = "TDEE",
                        value = tdee?.let { "${it.toInt()} kcal" } ?: "待计算",
                        modifier = Modifier.weight(1f)
                    )
                    MetricCard(
                        label = "自拍数",
                        value = recentSelfies.size.toString(),
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            item {
                SectionCard(title = "快捷入口", subtitle = "高频动作集中在一处，保持像 App 一样的固定节奏。") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            QuickActionButton(title = "晨重记录", onClick = onOpenWeightEntry, modifier = Modifier.weight(1f))
                            QuickActionButton(title = "餐食记录", onClick = onOpenMeals, modifier = Modifier.weight(1f))
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            QuickActionButton(title = "自拍记录", onClick = onOpenSelfies, modifier = Modifier.weight(1f))
                            QuickActionButton(title = "今日报告", onClick = onOpenReports, modifier = Modifier.weight(1f))
                        }
                        QuickActionButton(title = "连接设置", onClick = onOpenSettings, modifier = Modifier.fillMaxWidth())
                        GlassPrimaryButton(
                            text = if (dashboardLoading) "正在刷新..." else "刷新全部数据",
                            onClick = onRefresh,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }

            item {
                SectionCard(title = "最近体重", subtitle = "优先看最近几条体重记录，确认趋势有没有偏离。") {
                    if (recentMeasurements.isEmpty()) {
                        Text("还没有体重记录，先去补一条晨重。")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            recentMeasurements.take(5).forEach { item ->
                                Text(
                                    text = "${formatInstant(item.measuredAt)}  ${item.weightKg} kg" +
                                        (item.bodyFatPct?.let { " / ${it}%" } ?: ""),
                                    style = MaterialTheme.typography.bodyLarge
                                )
                            }
                        }
                    }
                }
            }

            item {
                SectionCard(title = "最近餐食", subtitle = "餐食记录保持高密可读，方便快速回看今天和最近几餐。") {
                    if (recentMeals.isEmpty()) {
                        Text("还没有餐食记录，可以先从午餐或晚餐开始。")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            recentMeals.take(5).forEach { item ->
                                Text(
                                    text = "${mealSlotLabel(item.mealSlot)} · ${item.foodName} · ${item.actualGrams.toInt()} g · ${item.kcal.toInt()} kcal",
                                    style = MaterialTheme.typography.bodyLarge
                                )
                            }
                        }
                    }
                }
            }

            item {
                SectionCard(title = "最近自拍", subtitle = "自拍流先保证上传与浏览稳定，后续再做同日对比。") {
                    if (recentSelfies.isEmpty()) {
                        Text("还没有自拍记录。")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            recentSelfies.take(3).forEach { item ->
                                Text(
                                    text = "${formatInstant(item.capturedAt)}  ${item.note ?: "已上传自拍"}",
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

@Composable
private fun QuickActionButton(
    title: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    GlassSecondaryButton(text = title, onClick = onClick, modifier = modifier)
}

private fun formatInstant(raw: String): String {
    return runCatching {
        Instant.parse(raw)
            .atZone(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern("M月d日 HH:mm"))
    }.getOrDefault(raw)
}

private fun DailyReportResponse?.payloadNumber(primaryKey: String, nestedKey: String? = null): Double? {
    val payload = this?.payload ?: return null
    val value = if (nestedKey == null) {
        payload[primaryKey]
    } else {
        (payload[primaryKey] as? Map<*, *>)?.get(nestedKey)
    }
    return when (value) {
        is Double -> value
        is Int -> value.toDouble()
        is Long -> value.toDouble()
        is Float -> value.toDouble()
        else -> null
    }
}

private fun mealSlotLabel(slot: String): String = when (slot) {
    "breakfast" -> "早餐"
    "lunch" -> "午餐"
    "dinner" -> "晚餐"
    "snack" -> "加餐"
    else -> slot
}
