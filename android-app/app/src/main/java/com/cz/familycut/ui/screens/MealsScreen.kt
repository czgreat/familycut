package com.cz.familycut.ui.screens

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import coil.compose.AsyncImage
import com.cz.familycut.data.local.FoodPresetEntity
import com.cz.familycut.data.remote.DailyReportResponse
import com.cz.familycut.data.remote.MealEntryResponse
import com.cz.familycut.ui.components.AppPage
import com.cz.familycut.ui.components.GlassFilterChip
import com.cz.familycut.ui.components.GlassPrimaryButton
import com.cz.familycut.ui.components.GlassSecondaryButton
import com.cz.familycut.ui.components.GlassTextField
import com.cz.familycut.ui.components.HeroCard
import com.cz.familycut.ui.components.HeroPillRow
import com.cz.familycut.ui.components.InlineCameraCapture
import com.cz.familycut.ui.components.SectionCard
import com.cz.familycut.ui.theme.SkyStroke
import java.io.ByteArrayOutputStream
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun MealsScreen(
    innerPadding: PaddingValues,
    serverUrl: String,
    todayReport: DailyReportResponse?,
    mealBusy: Boolean,
    nutritionDraftBusy: Boolean,
    nutritionDraftPending: Boolean,
    lastNutritionDraftCreatedAt: Long?,
    selectedMealSlot: String,
    foodName: String,
    consumedAt: String,
    actualGrams: String,
    kcal: String,
    carb: String,
    fat: String,
    protein: String,
    sodium: String,
    presetName: String,
    dishEstimateHint: String,
    nutritionDraftRawText: String,
    nutritionDraftConfidence: Float?,
    nutritionDraftStatusText: String,
    recentMeals: List<MealEntryResponse>,
    foodPresets: List<FoodPresetEntity>,
    onSelectMealSlot: (String) -> Unit,
    onFoodNameChange: (String) -> Unit,
    onConsumedAtChange: (String) -> Unit,
    onUseCurrentTime: () -> Unit,
    onActualGramsChange: (String) -> Unit,
    onKcalChange: (String) -> Unit,
    onCarbChange: (String) -> Unit,
    onFatChange: (String) -> Unit,
    onProteinChange: (String) -> Unit,
    onSodiumChange: (String) -> Unit,
    onPresetNameChange: (String) -> Unit,
    onDishEstimateHintChange: (String) -> Unit,
    onCreateNutritionDraft: (ByteArray, String, String?, String, String?) -> Unit,
    onApplyPreset: (FoodPresetEntity) -> Unit,
    onDeletePreset: (FoodPresetEntity) -> Unit,
    onCopyMeal: (MealEntryResponse) -> Unit,
    onCopyDay: (LocalDate) -> Unit,
    onSaveCurrentAsPreset: () -> Unit,
    onSubmitMeal: () -> Unit
) {
    val context = LocalContext.current
    var selectedNutritionUri by remember { mutableStateOf<Uri?>(null) }
    var cameraOpen by remember { mutableStateOf(false) }
    var pendingBytes by remember { mutableStateOf<ByteArray?>(null) }
    var pendingName by remember { mutableStateOf("nutrition.jpg") }
    var pendingMimeType by remember { mutableStateOf<String?>(null) }
    var selectedDishUri by remember { mutableStateOf<Uri?>(null) }
    var dishCameraOpen by remember { mutableStateOf(false) }
    var pendingDishBytes by remember { mutableStateOf<ByteArray?>(null) }
    var pendingDishName by remember { mutableStateOf("dish.jpg") }
    var pendingDishMimeType by remember { mutableStateOf<String?>(null) }
    var selectedMealDetail by remember { mutableStateOf<MealEntryResponse?>(null) }
    val carbGrams = carb.toFloatOrNull()?.takeIf { actualGrams.toFloatOrNull() != null }?.let { it * ((actualGrams.toFloatOrNull() ?: 0f) / 100f) } ?: 0f
    val fatGrams = fat.toFloatOrNull()?.takeIf { actualGrams.toFloatOrNull() != null }?.let { it * ((actualGrams.toFloatOrNull() ?: 0f) / 100f) } ?: 0f
    val proteinGrams = protein.toFloatOrNull()?.takeIf { actualGrams.toFloatOrNull() != null }?.let { it * ((actualGrams.toFloatOrNull() ?: 0f) / 100f) } ?: 0f
    val macroPreview = macroPercentages(carbGrams.toDouble(), fatGrams.toDouble(), proteinGrams.toDouble())
    val macroStatus = todayReport.payloadMap("macro_status")
    val macroTarget = todayReport.payloadMap("macro_target")

    val pickerLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            selectedNutritionUri = uri
            val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            if (bytes != null) {
                val prepared = prepareUploadImage(bytes, guessFileName(uri), context.contentResolver.getType(uri))
                pendingBytes = prepared.bytes
                pendingName = prepared.fileName
                pendingMimeType = prepared.mimeType
            }
        }
    }
    val dishPickerLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            selectedDishUri = uri
            val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            if (bytes != null) {
                val prepared = prepareUploadImage(bytes, guessFileName(uri), context.contentResolver.getType(uri))
                pendingDishBytes = prepared.bytes
                pendingDishName = prepared.fileName
                pendingDishMimeType = prepared.mimeType
            }
        }
    }

    LaunchedEffect(lastNutritionDraftCreatedAt) {
        if (lastNutritionDraftCreatedAt != null) {
            selectedNutritionUri = null
            pendingBytes = null
            pendingName = "nutrition.jpg"
            pendingMimeType = null
            selectedDishUri = null
            pendingDishBytes = null
            pendingDishName = "dish.jpg"
            pendingDishMimeType = null
        }
    }

    AppPage(innerPadding = innerPadding) {
        if (selectedMealDetail != null) {
            MealDetailDialog(
                serverUrl = serverUrl,
                meal = selectedMealDetail!!,
                onDismiss = { selectedMealDetail = null }
            )
        }
        LazyColumn(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    HeroCard(
                        title = "餐食记录",
                        subtitle = "营养表拍摄默认后置相机，AI 会优先把千焦换算成千卡；除热量外，其余营养项都可后补。"
                    )
                    HeroPillRow(
                        "当前餐次 ${mealSlotLabel(selectedMealSlot)}",
                        if (nutritionDraftPending) "AI 处理中" else "可随时录入",
                        if (recentMeals.isEmpty()) "最近无餐食" else "最近 ${recentMeals.size} 条"
                    )
                }
            }
            item {
                SectionCard(title = "识别营养表", subtitle = "相机直拍默认启用后置镜头，更适合拍营养表和包装。大多数标签是千焦单位，系统会优先换算成千卡。") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (cameraOpen) {
                            InlineCameraCapture(
                                lensFacing = CameraSelector.LENS_FACING_BACK,
                                label = "后置相机",
                                onCapture = { bytes, fileName, mimeType ->
                                    cameraOpen = false
                                    selectedNutritionUri = null
                                    val prepared = prepareUploadImage(bytes, fileName, mimeType)
                                    pendingBytes = prepared.bytes
                                    pendingName = prepared.fileName
                                    pendingMimeType = prepared.mimeType
                                },
                                onClose = { cameraOpen = false }
                            )
                        } else {
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                GlassPrimaryButton(
                                    text = when {
                                        nutritionDraftBusy -> "上传中..."
                                        nutritionDraftPending -> "后台识别中..."
                                        else -> "后置直拍"
                                    },
                                    onClick = { cameraOpen = true },
                                    modifier = Modifier.weight(1f),
                                    enabled = !nutritionDraftBusy && !nutritionDraftPending
                                )
                                GlassSecondaryButton(
                                    text = "相册导入",
                                    onClick = { pickerLauncher.launch("image/*") },
                                    modifier = Modifier.weight(1f),
                                    enabled = !nutritionDraftBusy && !nutritionDraftPending
                                )
                            }
                        }
                        if (selectedNutritionUri != null) {
                            Text("已从相册选择营养表图片。", style = MaterialTheme.typography.bodyMedium)
                        }
                        if (pendingBytes != null || selectedNutritionUri != null) {
                            AsyncImage(
                                model = selectedNutritionUri ?: pendingBytes,
                                contentDescription = "营养表预览",
                                modifier = Modifier.fillMaxWidth()
                            )
                            GlassPrimaryButton(
                                text = when {
                                    nutritionDraftBusy -> "上传中..."
                                    nutritionDraftPending -> "后台识别中..."
                                    else -> "上传并识别"
                                },
                                onClick = {
                                    val bytes = pendingBytes
                                    if (bytes != null) {
                                        onCreateNutritionDraft(bytes, pendingName, pendingMimeType, "label", null)
                                    }
                                },
                                modifier = Modifier.fillMaxWidth(),
                                enabled = !nutritionDraftBusy && !nutritionDraftPending
                            )
                        }
                        Text("图片会在本地先压缩再上传，减少等待时间。", style = MaterialTheme.typography.bodySmall)
                        if (nutritionDraftStatusText.isNotBlank()) {
                            Text(nutritionDraftStatusText, style = MaterialTheme.typography.bodySmall)
                        }
                        if (nutritionDraftRawText.isNotBlank()) {
                            Text("AI 原始识别：$nutritionDraftRawText", style = MaterialTheme.typography.bodySmall)
                        }
                        if (nutritionDraftConfidence != null) {
                            Text("识别置信度：${(nutritionDraftConfidence * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
            item {
                SectionCard(title = "估算现成饭菜", subtitle = "拍现成的饭菜，让 AI 先估算每 100g 热量和营养，再由你手动输入实际重量。") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (dishCameraOpen) {
                            InlineCameraCapture(
                                lensFacing = CameraSelector.LENS_FACING_BACK,
                                label = "后置相机",
                                onCapture = { bytes, fileName, mimeType ->
                                    dishCameraOpen = false
                                    selectedDishUri = null
                                    val prepared = prepareUploadImage(bytes, fileName, mimeType)
                                    pendingDishBytes = prepared.bytes
                                    pendingDishName = prepared.fileName
                                    pendingDishMimeType = prepared.mimeType
                                },
                                onClose = { dishCameraOpen = false }
                            )
                        } else {
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                GlassPrimaryButton(
                                    text = when {
                                        nutritionDraftBusy -> "上传中..."
                                        nutritionDraftPending -> "后台估算中..."
                                        else -> "拍现成饭菜"
                                    },
                                    onClick = { dishCameraOpen = true },
                                    modifier = Modifier.weight(1f),
                                    enabled = !nutritionDraftBusy && !nutritionDraftPending
                                )
                                GlassSecondaryButton(
                                    text = "导入饭菜图",
                                    onClick = { dishPickerLauncher.launch("image/*") },
                                    modifier = Modifier.weight(1f),
                                    enabled = !nutritionDraftBusy && !nutritionDraftPending
                                )
                            }
                        }
                        GlassTextField(
                            value = dishEstimateHint,
                            onValueChange = onDishEstimateHintChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "可选提示词"
                        )
                        if (pendingDishBytes != null || selectedDishUri != null) {
                            AsyncImage(
                                model = selectedDishUri ?: pendingDishBytes,
                                contentDescription = "现成饭菜预览",
                                modifier = Modifier.fillMaxWidth()
                            )
                            GlassPrimaryButton(
                                text = when {
                                    nutritionDraftBusy -> "上传中..."
                                    nutritionDraftPending -> "后台估算中..."
                                    else -> "上传并估算"
                                },
                                onClick = {
                                    val bytes = pendingDishBytes
                                    if (bytes != null) {
                                        onCreateNutritionDraft(bytes, pendingDishName, pendingDishMimeType, "dish_estimate", dishEstimateHint)
                                    }
                                },
                                modifier = Modifier.fillMaxWidth(),
                                enabled = !nutritionDraftBusy && !nutritionDraftPending
                            )
                        }
                        Text("App 会先压缩图片再上传。饭菜估算可带上商品名/规格提示，AI 若能判断整份重量，会直接回填克重输入框。", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            item {
                SectionCard(title = "本地快捷食物库", subtitle = "保存常用餐或自定义食谱，后面一键套用。") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        GlassTextField(
                            value = presetName,
                            onValueChange = onPresetNameChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "预设名称"
                        )
                        GlassPrimaryButton(text = "保存为常用餐", onClick = onSaveCurrentAsPreset, modifier = Modifier.fillMaxWidth(), enabled = !mealBusy)
                        if (foodPresets.isEmpty()) {
                            Text("还没有本地快捷食物。")
                        } else {
                            foodPresets.take(8).forEach { preset ->
                                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                                    GlassSecondaryButton(text = "${preset.name} · ${preset.kcal.toInt()} kcal", onClick = { onApplyPreset(preset) }, modifier = Modifier.weight(1f))
                                    GlassSecondaryButton(text = "删除", onClick = { onDeletePreset(preset) })
                                }
                            }
                        }
                    }
                }
            }
            item {
                SectionCard(title = "复制历史饮食", subtitle = "可以直接复制之前某一餐，或把某一天的饮食整天复制到今天。") {
                    val recentDates = recentMeals.mapNotNull { parseMealDate(it.consumedAt) }.distinct()
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (recentDates.isEmpty()) {
                            Text("最近还没有可复制的历史餐食。")
                        } else {
                            recentDates.take(7).forEach { itemDate ->
                                GlassSecondaryButton(text = "复制 ${itemDate} 这一天到今天", onClick = { onCopyDay(itemDate) }, modifier = Modifier.fillMaxWidth())
                            }
                        }
                    }
                }
            }
            item {
                SectionCard(title = "确认并保存本餐", subtitle = "这里填写的是每 100g 数据，保存时会按实际克重自动折算。热量必填，其余营养项可选。") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("lunch", "dinner", "snack").forEach { slot ->
                                GlassFilterChip(label = mealSlotLabel(slot), selected = slot == selectedMealSlot, onClick = { onSelectMealSlot(slot) })
                            }
                        }
                        GlassTextField(value = foodName, onValueChange = onFoodNameChange, modifier = Modifier.fillMaxWidth(), label = "食物名称")
                        GlassTextField(
                            value = consumedAt,
                            onValueChange = onConsumedAtChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = "进食时间（YYYY-MM-DDTHH:mm）"
                        )
                        GlassSecondaryButton(text = "写入当前时间", onClick = onUseCurrentTime, modifier = Modifier.fillMaxWidth())
                        GlassTextField(value = actualGrams, onValueChange = onActualGramsChange, modifier = Modifier.fillMaxWidth(), label = "实际克重（g）")
                        GlassTextField(value = kcal, onValueChange = onKcalChange, modifier = Modifier.fillMaxWidth(), label = "每 100g 热量（kcal，必填）")
                        GlassTextField(value = carb, onValueChange = onCarbChange, modifier = Modifier.fillMaxWidth(), label = "每 100g 碳水（g，可选）")
                        GlassTextField(value = fat, onValueChange = onFatChange, modifier = Modifier.fillMaxWidth(), label = "每 100g 脂肪（g，可选）")
                        GlassTextField(value = protein, onValueChange = onProteinChange, modifier = Modifier.fillMaxWidth(), label = "每 100g 蛋白质（g，可选）")
                        GlassTextField(value = sodium, onValueChange = onSodiumChange, modifier = Modifier.fillMaxWidth(), label = "每 100g 钠（mg，可选）")
                        if (actualGrams.isNotBlank()) {
                            Text(
                                "本餐占比：碳水 ${macroPreview.first.toInt()}% · 脂肪 ${macroPreview.second.toInt()}% · 蛋白质 ${macroPreview.third.toInt()}%",
                                style = MaterialTheme.typography.bodyMedium
                            )
                            Text(
                                "本餐总量：碳水 ${formatWeightValue(carbGrams)} g · 脂肪 ${formatWeightValue(fatGrams)} g · 蛋白质 ${formatWeightValue(proteinGrams)} g",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                        GlassPrimaryButton(text = if (mealBusy) "正在保存..." else "保存本餐", onClick = onSubmitMeal, modifier = Modifier.fillMaxWidth(), enabled = !mealBusy)
                    }
                }
            }
            item {
                SectionCard(title = "今日宏量进度", subtitle = "按最新体重、BMR、TDEE 和目标热量差动态计算今日目标。") {
                    if (todayReport == null || macroStatus == null || macroTarget == null) {
                        Text("补一条体重并生成今日日报后，这里会显示今日碳水、蛋白质、脂肪目标与达标情况。")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("目标摄入：${todayReport.payloadNumber(\"goal_intake_kcal\")?.toInt() ?: 0} kcal")
                            MacroProgressLine("碳水", macroStatus["carb"] as? Map<*, *>, macroTarget["carb_g"])
                            MacroProgressLine("蛋白质", macroStatus["protein"] as? Map<*, *>, macroTarget["protein_g"])
                            MacroProgressLine("脂肪", macroStatus["fat"] as? Map<*, *>, macroTarget["fat_g"])
                        }
                    }
                }
            }
            item {
                SectionCard(title = "最近餐食", subtitle = "默认展示最近 10 条。") {
                    if (recentMeals.isEmpty()) {
                        Text("还没有餐食记录。")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            recentMeals.take(10).forEach { item ->
                                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text(
                                        text = "${formatMealTime(item.consumedAt)}  ${mealSlotLabel(item.mealSlot)} · ${item.foodName} · ${item.actualGrams.toInt()} g · ${item.kcal.toInt()} kcal",
                                        style = MaterialTheme.typography.bodyLarge
                                    )
                                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                        GlassSecondaryButton(text = "查看详情", onClick = { selectedMealDetail = item }, modifier = Modifier.weight(1f))
                                        GlassSecondaryButton(text = "复制这餐", onClick = { onCopyMeal(item) }, modifier = Modifier.weight(1f))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MealDetailDialog(
    serverUrl: String,
    meal: MealEntryResponse,
    onDismiss: () -> Unit
) {
    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = MaterialTheme.shapes.large,
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.96f)),
            border = BorderStroke(1.dp, SkyStroke)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(meal.foodName, style = MaterialTheme.typography.titleLarge)
                val imageUrl = resolveMediaUrl(serverUrl, meal.sourceImageUrl)
                if (imageUrl != null) {
                    AsyncImage(
                        model = imageUrl,
                        contentDescription = "餐食来源图片",
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                Text("餐次：${mealSlotLabel(meal.mealSlot)}")
                Text("实际重量：${meal.actualGrams} g")
                Text("热量：${meal.kcal.toInt()} kcal")
                Text("碳水/脂肪/蛋白：${meal.carbG} / ${meal.fatG} / ${meal.proteinG}")
                if (meal.sodiumMg != null) {
                    Text("钠：${meal.sodiumMg} mg")
                }
                if (!meal.draftType.isNullOrBlank()) {
                    Text("来源：${if (meal.draftType == "dish_estimate") "现成饭菜估算" else "成分表识别"}")
                }
                if (!meal.sourceEstimatedScope.isNullOrBlank()) {
                    Text("计重口径：${weightScopeLabel(meal.sourceEstimatedScope)}")
                }
                val weightBreakdown = buildWeightBreakdownText(
                    total = meal.sourceEstimatedGrams,
                    solid = meal.sourceEstimatedSolidGrams,
                    liquid = meal.sourceEstimatedLiquidGrams
                )
                if (weightBreakdown != null) {
                    Text("重量拆分：$weightBreakdown")
                }
                if (!meal.sourcePortionBasis.isNullOrBlank()) {
                    Text("估算依据：${meal.sourcePortionBasis}")
                }
                if (!meal.sourceRawText.isNullOrBlank()) {
                    Text("识别说明：${meal.sourceRawText}")
                }
                GlassPrimaryButton(text = "关闭", onClick = onDismiss, modifier = Modifier.fillMaxWidth())
            }
        }
    }
}

private fun formatMealTime(raw: String): String {
    return runCatching {
        Instant.parse(raw)
            .atZone(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern("M月d日 HH:mm"))
    }.getOrDefault(raw)
}

private fun mealSlotLabel(slot: String): String = when (slot) {
    "breakfast" -> "早餐"
    "lunch" -> "午餐"
    "dinner" -> "晚餐"
    "snack" -> "加餐"
    else -> slot
}

private fun weightScopeLabel(scope: String?): String = when (scope) {
    "solid_only" -> "只算固形物"
    "includes_liquid" -> "包含汤汁/液体"
    "liquid_only" -> "只算液体"
    "unclear" -> "口径不明确"
    null, "" -> "未说明"
    else -> scope
}

private fun buildWeightBreakdownText(total: Float?, solid: Float?, liquid: Float?): String? {
    val parts = mutableListOf<String>()
    if (solid != null && solid > 0f) {
        parts += "固形物 ${formatWeightValue(solid)} g"
    }
    if (liquid != null && liquid > 0f) {
        parts += "汤汁/液体 ${formatWeightValue(liquid)} g"
    }
    if (total != null && total > 0f) {
        parts += "总量 ${formatWeightValue(total)} g"
    }
    return parts.takeIf { it.isNotEmpty() }?.joinToString(" · ")
}

private fun formatWeightValue(value: Float): String {
    val rounded = kotlin.math.round(value * 10f) / 10f
    return if (rounded % 1f == 0f) rounded.toInt().toString() else rounded.toString()
}

private fun guessFileName(uri: Uri): String {
    return uri.lastPathSegment?.substringAfterLast('/')?.takeIf { it.isNotBlank() }
        ?: "nutrition-${System.currentTimeMillis()}.jpg"
}

private data class PreparedUploadImage(
    val bytes: ByteArray,
    val fileName: String,
    val mimeType: String,
)

private fun prepareUploadImage(bytes: ByteArray, fileName: String, mimeType: String?): PreparedUploadImage {
    val compressed = compressToJpeg(bytes)
    return if (compressed != null && compressed.size < bytes.size) {
        PreparedUploadImage(
            bytes = compressed,
            fileName = fileName.substringBeforeLast('.', fileName) + ".jpg",
            mimeType = "image/jpeg"
        )
    } else {
        PreparedUploadImage(bytes = bytes, fileName = fileName, mimeType = mimeType ?: "image/jpeg")
    }
}

private fun compressToJpeg(bytes: ByteArray, maxDimension: Int = 1600, quality: Int = 84): ByteArray? {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null

    var sampleSize = 1
    while (maxOf(bounds.outWidth, bounds.outHeight) / sampleSize > maxDimension * 2) {
        sampleSize *= 2
    }

    val decoded = BitmapFactory.Options().apply { inSampleSize = sampleSize }
    val source = BitmapFactory.decodeByteArray(bytes, 0, bytes.size, decoded) ?: return null
    val longest = maxOf(source.width, source.height)
    val scaled = if (longest > maxDimension) {
        val scale = maxDimension.toFloat() / longest.toFloat()
        Bitmap.createScaledBitmap(
            source,
            (source.width * scale).toInt().coerceAtLeast(1),
            (source.height * scale).toInt().coerceAtLeast(1),
            true
        )
    } else {
        source
    }
    val output = ByteArrayOutputStream()
    scaled.compress(Bitmap.CompressFormat.JPEG, quality, output)
    if (scaled !== source) {
        scaled.recycle()
    }
    source.recycle()
    return output.toByteArray()
}

private fun parseMealDate(raw: String): LocalDate? {
    return runCatching { Instant.parse(raw).atZone(ZoneId.systemDefault()).toLocalDate() }.getOrNull()
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
        "$label：${formatWeightValue(actual ?: 0f)} / ${formatWeightValue(target ?: 0f)} g · $status",
        style = MaterialTheme.typography.bodyMedium
    )
}

private fun macroPercentages(carbG: Double, fatG: Double, proteinG: Double): Triple<Double, Double, Double> {
    val carbKcal = carbG * 4
    val fatKcal = fatG * 9
    val proteinKcal = proteinG * 4
    val total = carbKcal + fatKcal + proteinKcal
    if (total <= 0.0) {
        return Triple(0.0, 0.0, 0.0)
    }
    return Triple(carbKcal / total * 100, fatKcal / total * 100, proteinKcal / total * 100)
}

private fun DailyReportResponse?.payloadMap(key: String): Map<String, Any?>? {
    return this?.payload?.get(key) as? Map<String, Any?>
}

private fun resolveMediaUrl(serverUrl: String, path: String?): String? {
    if (path.isNullOrBlank()) return null
    if (path.startsWith("http://") || path.startsWith("https://")) return path
    val origin = serverUrl.substringBefore("/api/")
    return "$origin$path"
}
