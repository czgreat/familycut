package com.cz.familycut.ui.screens

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.os.Environment
import android.provider.MediaStore
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.cz.familycut.data.remote.DailyReportResponse
import com.cz.familycut.data.remote.ExerciseEntryResponse
import com.cz.familycut.data.remote.PeriodicReportResponse
import com.cz.familycut.ui.components.AppPage
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassSecondaryButton
import com.cz.familycut.ui.components.GlassTextField
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.MetricCard
import com.cz.familycut.ui.components.SectionCard
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.net.URL
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun ReportsScreen(
    innerPadding: PaddingValues,
    serverUrl: String,
    todayReport: DailyReportResponse?,
    weeklyReport: PeriodicReportResponse?,
    monthlyReport: PeriodicReportResponse?,
    recentReports: List<DailyReportResponse>,
    recentExercises: List<ExerciseEntryResponse>,
    selectedExerciseType: String,
    exerciseDistanceKm: String,
    exerciseDurationMin: String,
    exerciseNote: String,
    onApplyExerciseTemplate: (String) -> Unit,
    onExerciseDistanceChange: (String) -> Unit,
    onExerciseDurationChange: (String) -> Unit,
    onExerciseNoteChange: (String) -> Unit,
    onSubmitExercise: (String) -> Unit,
    dashboardLoading: Boolean,
    onRefresh: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val intake = todayReport.payloadNumber("intake", "kcal")
    val baseTdee = todayReport.payloadNumber("base_tdee")
    val exerciseKcal = todayReport.payloadNumber("exercise_kcal")
    val deficit = todayReport.payloadNumber("deficit_kcal")
    val carbGrams = todayReport.payloadNumber("intake", "carb_g")
    val proteinGrams = todayReport.payloadNumber("intake", "protein_g")
    val fatGrams = todayReport.payloadNumber("intake", "fat_g")
    val carbRatio = todayReport.payloadNumber("macro_ratio", "carb_pct")
    val proteinRatio = todayReport.payloadNumber("macro_ratio", "protein_pct")
    val fatRatio = todayReport.payloadNumber("macro_ratio", "fat_pct")
    val goalIntake = todayReport.payloadNumber("goal_intake_kcal")
    val macroTarget = todayReport.payloadMap("macro_target")
    val macroStatus = todayReport.payloadMap("macro_status")

    AppPage(innerPadding = innerPadding) {
        LazyColumn(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    HeroCard(
                        title = "报告中心",
                        subtitle = "今日日报、本周小结和本月小结都会在这里聚合。应用内不直接展示长图，只保留导出和分享。"
                    )
                    HeroPillRow(
                        "摄入 ${intake?.toInt() ?: 0} kcal",
                        "热量差 ${deficit?.toInt() ?: 0} kcal",
                        "运动 ${exerciseKcal?.toInt() ?: 0} kcal"
                    )
                }
            }

            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    MetricCard(
                        label = "静坐 TDEE",
                        value = baseTdee?.let { "${it.toInt()} kcal" } ?: "待生成",
                        modifier = Modifier.weight(1f)
                    )
                    MetricCard(
                        label = "额外运动",
                        value = exerciseKcal?.let { "${it.toInt()} kcal" } ?: "0 kcal",
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    MetricCard(
                        label = "摄入",
                        value = intake?.let { "${it.toInt()} kcal" } ?: "待生成",
                        modifier = Modifier.weight(1f)
                    )
                    MetricCard(
                        label = "热量差",
                        value = deficit?.let { "${it.toInt()} kcal" } ?: "待生成",
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            item {
                SectionCard(title = "今日日报", subtitle = "保留手机友好的摘要和图形化比例，长图只用于导出和分享。") {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("状态：${reportStatusLabel(todayReport?.status)}")
                        Text("目标摄入：${goalIntake?.toInt() ?: 0} kcal")
                        MacroRatioBar(label = "碳水", value = carbRatio, grams = carbGrams)
                        MacroProgressLine("碳水目标", macroStatus?.get("carb") as? Map<*, *>, macroTarget?.get("carb_g"))
                        MacroRatioBar(label = "蛋白质", value = proteinRatio, grams = proteinGrams)
                        MacroProgressLine("蛋白目标", macroStatus?.get("protein") as? Map<*, *>, macroTarget?.get("protein_g"))
                        MacroRatioBar(label = "脂肪", value = fatRatio, grams = fatGrams)
                        MacroProgressLine("脂肪目标", macroStatus?.get("fat") as? Map<*, *>, macroTarget?.get("fat_g"))
                        val dailyImageUrl = todayReport?.imageUrl?.let { resolveReportUrl(serverUrl, it) }
                        if (dailyImageUrl != null) {
                            Text("日报长图已生成，可直接导出或分享。", style = MaterialTheme.typography.bodySmall)
                            ReportImageActions(
                                onExport = {
                                    scope.launch {
                                        exportReportImage(
                                            context = context,
                                            imageUrl = dailyImageUrl,
                                            fileName = "familycut-daily-${todayReport.reportDate}.png",
                                        )
                                    }
                                },
                                onShare = {
                                    scope.launch {
                                        shareReportImage(
                                            context = context,
                                            imageUrl = dailyImageUrl,
                                            fileName = "familycut-daily-${todayReport.reportDate}.png",
                                            chooserTitle = "分享今日日报"
                                        )
                                    }
                                }
                            )
                        } else {
                            Text("日报长图暂未生成。", style = MaterialTheme.typography.bodySmall)
                        }
                        if (todayReport?.imageUrl != null) {
                            Text(
                                "应用内已隐藏日报长图预览，避免占满屏幕并影响阅读。",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                        GlassPrimaryButton(
                            text = if (dashboardLoading) "正在刷新..." else "刷新报告数据",
                            onClick = onRefresh,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }

            item {
                PeriodicReportCard(
                    title = "本周小结",
                    report = weeklyReport,
                    serverUrl = serverUrl,
                    onExport = { imageUrl, fileName ->
                        scope.launch {
                            exportReportImage(context, imageUrl, fileName)
                        }
                    },
                    onShare = { imageUrl, fileName ->
                        scope.launch {
                            shareReportImage(context, imageUrl, fileName, "分享本周小结")
                        }
                    }
                )
            }

            item {
                PeriodicReportCard(
                    title = "本月小结",
                    report = monthlyReport,
                    serverUrl = serverUrl,
                    onExport = { imageUrl, fileName ->
                        scope.launch {
                            exportReportImage(context, imageUrl, fileName)
                        }
                    },
                    onShare = { imageUrl, fileName ->
                        scope.launch {
                            shareReportImage(context, imageUrl, fileName, "分享本月小结")
                        }
                    }
                )
            }

            item {
                SectionCard(title = "额外运动", subtitle = "预设常见模板，山地车、羽毛球、跑步等都可直接录。") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text("当前模板：${exerciseLabel(selectedExerciseType)}", style = MaterialTheme.typography.bodyMedium)
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            GlassSecondaryButton(text = "山地车", onClick = { onApplyExerciseTemplate("mountain_bike_commute") }, modifier = Modifier.weight(1f))
                            GlassSecondaryButton(text = "羽毛球", onClick = { onApplyExerciseTemplate("badminton") }, modifier = Modifier.weight(1f))
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            GlassSecondaryButton(text = "慢跑", onClick = { onApplyExerciseTemplate("running_easy") }, modifier = Modifier.weight(1f))
                            GlassSecondaryButton(text = "中速跑", onClick = { onApplyExerciseTemplate("running_tempo") }, modifier = Modifier.weight(1f))
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            GlassSecondaryButton(text = "快跑", onClick = { onApplyExerciseTemplate("running_fast") }, modifier = Modifier.weight(1f))
                            GlassSecondaryButton(text = "步行", onClick = { onApplyExerciseTemplate("walking") }, modifier = Modifier.weight(1f))
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            GlassSecondaryButton(text = "力量训练", onClick = { onApplyExerciseTemplate("strength_training") }, modifier = Modifier.weight(1f))
                            GlassSecondaryButton(text = "游泳", onClick = { onApplyExerciseTemplate("swimming") }, modifier = Modifier.weight(1f))
                        }
                        GlassTextField(
                            value = exerciseDistanceKm,
                            onValueChange = onExerciseDistanceChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "距离（km，可选）"
                        )
                        GlassTextField(
                            value = exerciseDurationMin,
                            onValueChange = onExerciseDurationChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "时长（分钟，可选）"
                        )
                        GlassTextField(
                            value = exerciseNote,
                            onValueChange = onExerciseNoteChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "备注（可选）"
                        )
                        GlassPrimaryButton(
                            text = "按当前模板记录运动",
                            onClick = { onSubmitExercise(selectedExerciseType) },
                            modifier = Modifier.fillMaxWidth()
                        )
                        if (recentExercises.isEmpty()) {
                            Text("今天还没有额外运动记录。")
                        } else {
                            recentExercises.take(5).forEach { item ->
                                Text(
                                    text = "${formatExerciseTime(item.occurredAt)} · ${exerciseLabel(item.exerciseType)}" +
                                        (item.distanceKm?.let { " · ${it}km" } ?: "") +
                                        (item.durationMin?.let { " · ${it.toInt()} 分钟" } ?: "") +
                                        (item.estimatedKcal?.let { " · ${it.toInt()} kcal" } ?: ""),
                                    style = MaterialTheme.typography.bodyLarge
                                )
                            }
                        }
                    }
                }
            }

            item {
                SectionCard(title = "近 7 日日报", subtitle = "快速回看最近几天是否达标。") {
                    if (recentReports.isEmpty()) {
                        Text("还没有日报记录。")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            recentReports.forEach { report ->
                                val reportDeficit = report.payloadNumber("deficit_kcal")
                                val hit = report.payloadBoolean("deficit_hit")
                                Text(
                                    text = "${formatReportDate(report.reportDate)}  热量差 ${reportDeficit?.toInt() ?: 0} kcal  ·  ${if (hit == true) "达标" else "未达标"}",
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
private fun PeriodicReportCard(
    title: String,
    report: PeriodicReportResponse?,
    serverUrl: String,
    onExport: (String, String) -> Unit,
    onShare: (String, String) -> Unit,
) {
    SectionCard(title = title, subtitle = "长图会汇总这个周期的体重、热量差和达标情况。") {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (report == null) {
                Text("还没有生成这个周期的报告。")
                return@Column
            }
            val hitDays = report.payloadNumber("hit_days") ?: 0.0
            val totalDays = report.payloadNumber("total_days") ?: 0.0
            val hitRate = if (totalDays > 0) (hitDays / totalDays).coerceIn(0.0, 1.0) else 0.0
            val avgCarb = report.payloadNumber("avg_intake", "carb_g")
            val avgProtein = report.payloadNumber("avg_intake", "protein_g")
            val avgFat = report.payloadNumber("avg_intake", "fat_g")
            Text("周期：${report.periodStart} ~ ${report.periodEnd}")
            Text("状态：${reportStatusLabel(report.status)}")
            Text("平均摄入：${report.payloadNumber("avg_intake_kcal")?.toInt() ?: 0} kcal / 天")
            Text("平均热量差：${report.payloadNumber("avg_deficit_kcal")?.toInt() ?: 0} kcal / 天")
            Text("达标天数：${report.payloadNumber("hit_days")?.toInt() ?: 0} / ${report.payloadNumber("total_days")?.toInt() ?: 0}")
            Text(
                "平均宏量：碳水 ${avgCarb?.toInt() ?: 0} g · 蛋白质 ${avgProtein?.toInt() ?: 0} g · 脂肪 ${avgFat?.toInt() ?: 0} g / 天"
            )
            LinearProgressIndicator(progress = { hitRate.toFloat() }, modifier = Modifier.fillMaxWidth().height(10.dp))
            Text("达标率：${(hitRate * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
            if (report.imageUrl != null) {
                val imageUrl = resolveReportUrl(serverUrl, report.imageUrl)
                val fileName = "familycut-${report.reportType}-${report.periodStart}-${report.periodEnd}.png"
                Text("长图已生成，可导出到相册或直接分享。", style = MaterialTheme.typography.bodySmall)
                ReportImageActions(
                    onExport = { onExport(imageUrl, fileName) },
                    onShare = { onShare(imageUrl, fileName) }
                )
                Text("应用内已隐藏长图预览，避免占满屏幕。", style = MaterialTheme.typography.bodySmall)
            } else {
                Text("长图暂未生成。", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun ReportImageActions(
    onExport: () -> Unit,
    onShare: () -> Unit
) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        GlassSecondaryButton(text = "导出", onClick = onExport, modifier = Modifier.weight(1f))
        GlassPrimaryButton(text = "分享", onClick = onShare, modifier = Modifier.weight(1f))
    }
}

@Composable
private fun MacroRatioBar(
    label: String,
    value: Double?,
    grams: Double?,
) {
    val normalized = ((value ?: 0.0) / 100.0).coerceIn(0.0, 1.0).toFloat()
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, style = MaterialTheme.typography.bodyMedium)
            val amountText = grams?.let { " · ${it.toInt()} g" } ?: ""
            Text("${(normalized * 100).toInt()}%$amountText", style = MaterialTheme.typography.bodyMedium)
        }
        LinearProgressIndicator(progress = { normalized }, modifier = Modifier.fillMaxWidth().height(10.dp))
    }
}

@Composable
private fun MacroProgressLine(
    label: String,
    progress: Map<*, *>?,
    targetValue: Any?,
) {
    val actual = (progress?.get("actual_g") as? Number)?.toFloat()
    val target = (targetValue as? Number)?.toFloat()
    val status = when (progress?.get("status") as? String) {
        "on_target" -> "达标"
        "low" -> "偏低"
        "high" -> "偏高"
        else -> "待计算"
    }
    Text(
        "$label：${formatMacroValue(actual)} / ${formatMacroValue(target)} g · $status",
        style = MaterialTheme.typography.bodySmall
    )
}

private fun formatMacroValue(value: Float?): String = value?.toInt()?.toString() ?: "0"

private suspend fun exportReportImage(context: Context, imageUrl: String, fileName: String) {
    val bytes = downloadImageBytes(imageUrl)
    withContext(Dispatchers.IO) {
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/FamilyCut")
        }
        val uri = context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
            ?: throw IllegalStateException("无法创建导出文件")
        context.contentResolver.openOutputStream(uri)?.use { output ->
            output.write(bytes)
        } ?: throw IllegalStateException("无法写入导出文件")
    }
    Toast.makeText(context, "图片已导出到系统相册 / 图片目录。", Toast.LENGTH_SHORT).show()
}

private suspend fun shareReportImage(context: Context, imageUrl: String, fileName: String, chooserTitle: String) {
    val bytes = downloadImageBytes(imageUrl)
    val cacheDir = File(context.cacheDir, "shared-reports").apply { mkdirs() }
    val file = File(cacheDir, fileName)
    withContext(Dispatchers.IO) {
        file.writeBytes(bytes)
    }
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "image/png"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, chooserTitle).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
}

private suspend fun downloadImageBytes(imageUrl: String): ByteArray {
    return withContext(Dispatchers.IO) {
        URL(imageUrl).openStream().use { it.readBytes() }
    }
}

private fun formatExerciseTime(raw: String): String {
    return runCatching {
        Instant.parse(raw)
            .atZone(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern("M月d日 HH:mm"))
    }.getOrDefault(raw)
}

private fun exerciseLabel(type: String): String = when (type) {
    "mountain_bike_commute" -> "山地车通勤"
    "badminton" -> "羽毛球"
    "running_easy" -> "慢跑"
    "running_tempo" -> "中速跑"
    "running_fast" -> "快跑"
    "walking" -> "步行"
    "swimming" -> "游泳"
    "strength_training" -> "力量训练"
    else -> "自定义运动"
}

private fun reportStatusLabel(raw: String?): String = when (raw) {
    "generated" -> "已生成"
    "processing" -> "生成中"
    "failed" -> "生成失败"
    null, "" -> "暂无"
    else -> raw
}

private fun DailyReportResponse?.payloadNumber(primaryKey: String, nestedKey: String? = null): Double? {
    val payload = this?.payload ?: return null
    val value = if (nestedKey == null) {
        payload[primaryKey]
    } else {
        (payload[primaryKey] as? Map<*, *>)?.get(nestedKey)
    }
    return value.toDoubleOrNull()
}

private fun PeriodicReportResponse.payloadNumber(primaryKey: String, nestedKey: String? = null): Double? {
    val value = if (nestedKey == null) {
        payload[primaryKey]
    } else {
        (payload[primaryKey] as? Map<*, *>)?.get(nestedKey)
    }
    return value.toDoubleOrNull()
}

private fun DailyReportResponse?.payloadMap(key: String): Map<String, Any?>? {
    return this?.payload?.get(key) as? Map<String, Any?>
}

private fun Any?.toDoubleOrNull(): Double? = when (this) {
    is Double -> this
    is Float -> this.toDouble()
    is Int -> this.toDouble()
    is Long -> this.toDouble()
    is String -> this.toDoubleOrNull()
    else -> null
}

private fun DailyReportResponse.payloadBoolean(key: String): Boolean? {
    return payload[key] as? Boolean
}

private fun formatReportDate(raw: String): String {
    return runCatching {
        LocalDate.parse(raw).format(DateTimeFormatter.ofPattern("M月d日"))
    }.getOrDefault(raw)
}

private fun resolveReportUrl(serverUrl: String, path: String): String {
    if (path.startsWith("http://") || path.startsWith("https://")) {
        return path
    }
    val origin = serverUrl.substringBefore("/api/")
    return "$origin$path"
}
