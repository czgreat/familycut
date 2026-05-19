package com.cz.familycut.ui.viewmodel

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.cz.familycut.BuildConfig
import com.cz.familycut.data.local.FoodPresetEntity
import com.cz.familycut.data.local.ThemePreferencesRepository
import com.cz.familycut.data.model.ThemeMode
import com.cz.familycut.data.model.UserSession
import com.cz.familycut.data.remote.DailyReportResponse
import com.cz.familycut.data.remote.ExerciseEntryCreateRequest
import com.cz.familycut.data.remote.ExerciseEntryResponse
import com.cz.familycut.data.remote.MealEntryCreateRequest
import com.cz.familycut.data.remote.MealEntryResponse
import com.cz.familycut.data.remote.MeasurementResponse
import com.cz.familycut.data.remote.MediaAssetResponse
import com.cz.familycut.data.remote.NutritionDraftResponse
import com.cz.familycut.data.remote.PeriodicReportResponse
import com.cz.familycut.data.repository.AppStateRepository
import com.cz.familycut.data.repository.FoodPresetRepository
import com.cz.familycut.data.repository.SyncRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import retrofit2.HttpException
import org.json.JSONObject
import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.YearMonth
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.temporal.TemporalAdjusters

class MainViewModel(
    private val preferencesRepository: ThemePreferencesRepository,
    private val appStateRepository: AppStateRepository,
    private val syncRepository: SyncRepository,
    foodPresetRepository: FoodPresetRepository
) : ViewModel() {
    companion object {
        private val MealTimeFormatter: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm")
    }

    val session: StateFlow<UserSession?> = appStateRepository.session

    val themeMode: StateFlow<ThemeMode> = preferencesRepository.themeMode.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = ThemeMode.FOLLOW_SYSTEM
    )

    val serverUrl: StateFlow<String> = preferencesRepository.serverUrl.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = BuildConfig.API_BASE_URL
    )

    val foodPresets: StateFlow<List<FoodPresetEntity>> = foodPresetRepository.foodPresets.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = emptyList()
    )

    val themeModeValue: ThemeMode
        get() = themeMode.value

    private val _notice = MutableStateFlow<String?>(null)
    val notice: StateFlow<String?> = _notice.asStateFlow()

    var weightInput by mutableStateOf("")
        private set
    var bodyFatInput by mutableStateOf("")
        private set
    var loginBusy by mutableStateOf(false)
        private set
    var invitePreviewText by mutableStateOf("")
        private set
    var dashboardLoading by mutableStateOf(false)
        private set
    var mealBusy by mutableStateOf(false)
        private set
    var nutritionDraftBusy by mutableStateOf(false)
        private set
    var nutritionDraftPending by mutableStateOf(false)
        private set
    var selfieBusy by mutableStateOf(false)
        private set

    var recentMeasurements by mutableStateOf<List<MeasurementResponse>>(emptyList())
        private set
    var recentMeals by mutableStateOf<List<MealEntryResponse>>(emptyList())
        private set
    var recentSelfies by mutableStateOf<List<MediaAssetResponse>>(emptyList())
        private set
    var recentExercises by mutableStateOf<List<ExerciseEntryResponse>>(emptyList())
        private set
    var todayReport by mutableStateOf<DailyReportResponse?>(null)
        private set
    var weeklyReport by mutableStateOf<PeriodicReportResponse?>(null)
        private set
    var monthlyReport by mutableStateOf<PeriodicReportResponse?>(null)
        private set
    var recentReports by mutableStateOf<List<DailyReportResponse>>(emptyList())
        private set

    var selectedMealSlot by mutableStateOf("lunch")
        private set
    var mealFoodName by mutableStateOf("")
        private set
    var mealConsumedAt by mutableStateOf(currentMealDateTimeValue())
        private set
    var mealActualGrams by mutableStateOf("")
        private set
    var mealKcal by mutableStateOf("")
        private set
    var mealCarb by mutableStateOf("")
        private set
    var mealFat by mutableStateOf("")
        private set
    var mealProtein by mutableStateOf("")
        private set
    var mealSodium by mutableStateOf("")
        private set
    var mealPresetName by mutableStateOf("")
        private set
    var dishEstimateHint by mutableStateOf("")
        private set
    var currentMealDraftId by mutableStateOf<String?>(null)
        private set
    var currentMealDraftType by mutableStateOf<String?>(null)
        private set
    var nutritionDraftRawText by mutableStateOf("")
        private set
    var nutritionDraftConfidence by mutableStateOf<Float?>(null)
        private set
    var nutritionDraftStatusText by mutableStateOf("")
        private set
    var selfieNote by mutableStateOf("")
        private set
    var comparisonGifUrl by mutableStateOf<String?>(null)
        private set
    var lastWeightSubmitAt by mutableStateOf<Long?>(null)
        private set
    var lastNutritionDraftCreatedAt by mutableStateOf<Long?>(null)
        private set
    var lastSelfieUploadAt by mutableStateOf<Long?>(null)
        private set
    var exerciseDistanceKm by mutableStateOf("7")
        private set
    var exerciseDurationMin by mutableStateOf("")
        private set
    var exerciseNote by mutableStateOf("")
        private set
    var selectedExerciseType by mutableStateOf("mountain_bike_commute")
        private set

    private val presetRepository = foodPresetRepository
    private var nutritionDraftPollingJob: Job? = null

    init {
        if (session.value != null) {
            refreshDashboardData()
        }
    }

    val profileNeedsCompletion: Boolean
        get() {
            val current = session.value ?: return false
            return current.heightCm == null || current.sex.isNullOrBlank() || current.birthYear == null
        }

    fun login(serverUrl: String, username: String, password: String) {
        viewModelScope.launch {
            loginBusy = true
            try {
                val currentSession = appStateRepository.login(serverUrl, username, password)
                val syncedCount = syncRepository.flushQueuedActions()
                refreshDashboardData()
                _notice.value = queuedSyncNotice("已登录：${currentSession.displayName}", syncedCount)
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "登录失败，请检查服务器地址、网络和密码。")
            } finally {
                loginBusy = false
            }
        }
    }

    fun saveServerUrl(serverUrl: String) {
        viewModelScope.launch {
            try {
                preferencesRepository.setServerUrl(serverUrl)
                _notice.value = "服务器地址已保存。"
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "服务器地址保存失败。")
            }
        }
    }

    fun previewInvite(serverUrl: String, code: String) {
        if (code.isBlank()) {
            invitePreviewText = ""
            return
        }
        viewModelScope.launch {
            try {
                val preview = appStateRepository.previewInvite(serverUrl, code)
                invitePreviewText = "邀请码有效，可加入为：${preview.role}"
            } catch (error: Exception) {
                invitePreviewText = friendlyMessage(error, "邀请码无效。")
            }
        }
    }

    fun registerByInvite(
        serverUrl: String,
        code: String,
        username: String,
        password: String,
        displayName: String,
        sex: String,
        birthYear: String
    ) {
        val parsedBirthYear = birthYear.toIntOrNull()
        if (sex.isBlank() || parsedBirthYear == null) {
            _notice.value = "请先填写性别和出生年份。"
            return
        }
        viewModelScope.launch {
            loginBusy = true
            try {
                val currentSession = appStateRepository.registerByInvite(
                    serverUrl = serverUrl,
                    code = code,
                    username = username,
                    password = password,
                    displayName = displayName,
                    sex = sex,
                    birthYear = parsedBirthYear
                )
                val syncedCount = syncRepository.flushQueuedActions()
                refreshDashboardData()
                _notice.value = queuedSyncNotice("已加入家庭：${currentSession.displayName}", syncedCount)
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "邀请码注册失败。")
            } finally {
                loginBusy = false
            }
        }
    }

    fun completeProfile(displayName: String, sex: String, birthYear: String, heightCm: String) {
        val parsedHeight = heightCm.toFloatOrNull()
        val current = session.value
        val parsedBirthYear = birthYear.toIntOrNull()
        val resolvedSex = current?.sex ?: sex.takeIf { it.isNotBlank() }
        val resolvedBirthYear = current?.birthYear ?: parsedBirthYear
        if (displayName.isBlank() || resolvedSex.isNullOrBlank() || resolvedBirthYear == null || parsedHeight == null || parsedHeight <= 0f) {
            _notice.value = "请完整填写显示名、性别、出生年份和身高。"
            return
        }
        viewModelScope.launch {
            loginBusy = true
            try {
                val currentSession = appStateRepository.completeProfile(
                    displayName = displayName,
                    sex = if (current?.sex == null) resolvedSex else null,
                    birthYear = if (current?.birthYear == null) resolvedBirthYear else null,
                    heightCm = parsedHeight
                )
                val syncedCount = syncRepository.flushQueuedActions()
                refreshDashboardData()
                _notice.value = queuedSyncNotice("资料已完善：${currentSession.displayName}", syncedCount)
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "资料保存失败。")
            } finally {
                loginBusy = false
            }
        }
    }

    fun logout() {
        appStateRepository.logout()
        recentMeasurements = emptyList()
        recentMeals = emptyList()
        recentSelfies = emptyList()
        recentExercises = emptyList()
        todayReport = null
        weeklyReport = null
        monthlyReport = null
        recentReports = emptyList()
        comparisonGifUrl = null
        _notice.value = "已退出登录。"
    }

    fun setThemeMode(mode: ThemeMode) {
        viewModelScope.launch {
            preferencesRepository.setThemeMode(mode)
        }
    }

    fun refreshDashboardData() {
        refreshData(includePeriodicReports = false)
    }

    fun refreshReportsData() {
        refreshData(includePeriodicReports = true)
    }

    private fun refreshData(includePeriodicReports: Boolean) {
        if (session.value == null) return
        viewModelScope.launch {
            dashboardLoading = true
            try {
                val syncedCount = syncRepository.flushQueuedActions()
                coroutineScope {
                    val measurementsTask = async { appStateRepository.listMeasurements() }
                    val mealsTask = async { appStateRepository.listMeals(limit = 60) }
                    val selfiesTask = async { appStateRepository.listSelfies() }
                    val exercisesTask = async { appStateRepository.listExercises() }
                    val today = LocalDate.now()
                    val todayReportTask = async { appStateRepository.getDailyReport(today) }
                    val recentReportsTask = async { appStateRepository.getRecentReports(limit = 7) }
                    val weeklyReportTask = if (includePeriodicReports) {
                        val weekStart = today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
                        async { appStateRepository.getWeeklyReport(weekStart) }
                    } else {
                        null
                    }
                    val monthlyReportTask = if (includePeriodicReports) {
                        async { appStateRepository.getMonthlyReport(YearMonth.from(today).toString()) }
                    } else {
                        null
                    }

                    recentMeasurements = measurementsTask.await()
                    recentMeals = mealsTask.await()
                    recentSelfies = selfiesTask.await()
                    recentExercises = exercisesTask.await()
                    todayReport = todayReportTask.await()
                    if (weeklyReportTask != null) {
                        weeklyReport = weeklyReportTask.await()
                    }
                    if (monthlyReportTask != null) {
                        monthlyReport = monthlyReportTask.await()
                    }
                    recentReports = recentReportsTask.await()
                }
                if (syncedCount > 0 && _notice.value == null) {
                    _notice.value = "已补传 $syncedCount 条离线晨重。"
                }
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "读取首页数据失败。")
            } finally {
                dashboardLoading = false
            }
        }
    }

    fun updateWeightInput(value: String) {
        weightInput = value
    }

    fun updateBodyFatInput(value: String) {
        bodyFatInput = value
    }

    fun submitWeight() {
        val weight = weightInput.toFloatOrNull()
        val bodyFat = bodyFatInput.toFloatOrNull()
        if (weight == null || weight <= 0f) {
            _notice.value = "请输入有效体重。"
            return
        }
        viewModelScope.launch {
            val uploaded = syncRepository.submitOrQueueWeightDraft(weightKg = weight, bodyFatPct = bodyFat)
            weightInput = ""
            bodyFatInput = ""
            lastWeightSubmitAt = System.currentTimeMillis()
            if (uploaded) {
                refreshDashboardData()
                _notice.value = "晨重已提交到服务器。"
            } else {
                _notice.value = "网络失败，已回落保存到本地队列。"
            }
        }
    }

    fun selectMealSlot(slot: String) {
        selectedMealSlot = slot
    }

    fun updateMealFoodName(value: String) {
        mealFoodName = value
    }

    fun updateMealConsumedAt(value: String) {
        mealConsumedAt = value
    }

    fun useCurrentMealTime() {
        mealConsumedAt = currentMealDateTimeValue()
    }

    fun updateMealActualGrams(value: String) {
        mealActualGrams = value
    }

    fun updateMealKcal(value: String) {
        mealKcal = value
    }

    fun updateMealCarb(value: String) {
        mealCarb = value
    }

    fun updateMealFat(value: String) {
        mealFat = value
    }

    fun updateMealProtein(value: String) {
        mealProtein = value
    }

    fun updateMealSodium(value: String) {
        mealSodium = value
    }

    fun updateMealPresetName(value: String) {
        mealPresetName = value
    }

    fun updateDishEstimateHint(value: String) {
        dishEstimateHint = value
    }

    fun createNutritionDraft(imageBytes: ByteArray, fileName: String, mimeType: String?, draftType: String, hintText: String? = null) {
        viewModelScope.launch {
            nutritionDraftBusy = true
            nutritionDraftPending = false
            nutritionDraftStatusText = "正在上传图片..."
            try {
                val draft = appStateRepository.createNutritionDraft(imageBytes, fileName, mimeType, draftType, hintText)
                currentMealDraftId = draft.id
                currentMealDraftType = draft.draftType
                lastNutritionDraftCreatedAt = System.currentTimeMillis()
                when (draft.status) {
                    "ready" -> {
                        applyNutritionDraft(draft)
                        dishEstimateHint = ""
                        _notice.value = "AI 识别完成，请检查名称和估算结果，并手动输入实际重量。"
                    }
                    "failed" -> {
                        dishEstimateHint = ""
                        nutritionDraftStatusText = draft.errorMessage ?: "后台识别失败，请稍后重试。"
                        _notice.value = nutritionDraftStatusText
                    }
                    else -> {
                        nutritionDraftPending = true
                        nutritionDraftStatusText = "图片已上传，后台识别中..."
                        _notice.value = "图片已上传，后台识别中。可以先继续填写重量和餐次。"
                        startNutritionDraftPolling(draft.id)
                    }
                }
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "营养表识别失败。")
                nutritionDraftStatusText = ""
            } finally {
                nutritionDraftBusy = false
            }
        }
    }

    fun submitMeal() {
        val actualGrams = mealActualGrams.toFloatOrNull()
        val per100Kcal = mealKcal.toFloatOrNull()
        val per100Carb = mealCarb.toFloatOrNull()
        val per100Fat = mealFat.toFloatOrNull()
        val per100Protein = mealProtein.toFloatOrNull()
        val per100Sodium = mealSodium.toFloatOrNull()

        if (mealFoodName.isBlank()) {
            _notice.value = "请填写食物名称。"
            return
        }
        if (actualGrams == null || actualGrams <= 0f || per100Kcal == null || per100Kcal < 0f) {
            _notice.value = "请至少填写每 100g 热量和实际克重。"
            return
        }
        if ((per100Carb != null && per100Carb < 0f) || (per100Fat != null && per100Fat < 0f) || (per100Protein != null && per100Protein < 0f)) {
            _notice.value = "碳水、脂肪、蛋白质不能为负数。"
            return
        }
        val consumedAt = runCatching { mealConsumedAtToInstantString() }.getOrElse {
            _notice.value = it.message ?: "进食时间格式不正确。"
            return
        }

        val ratio = actualGrams / 100f
        viewModelScope.launch {
            mealBusy = true
            try {
                appStateRepository.createMeal(
                    MealEntryCreateRequest(
                        draftId = currentMealDraftId,
                        mealSlot = selectedMealSlot,
                        consumedAt = consumedAt,
                        foodName = mealFoodName,
                        actualGrams = actualGrams,
                        kcal = per100Kcal * ratio,
                        carbG = (per100Carb ?: 0f) * ratio,
                        fatG = (per100Fat ?: 0f) * ratio,
                        proteinG = (per100Protein ?: 0f) * ratio,
                        sodiumMg = per100Sodium?.let { it * ratio },
                        corrections = buildMap {
                            if (nutritionDraftRawText.isNotBlank()) {
                                put("raw_text", nutritionDraftRawText)
                            }
                            if (!currentMealDraftType.isNullOrBlank()) {
                                put("draft_type", currentMealDraftType!!)
                            }
                        }.ifEmpty { null }
                    )
                )
                mealConsumedAt = currentMealDateTimeValue()
                mealFoodName = ""
                mealActualGrams = ""
                mealKcal = ""
                mealCarb = ""
                mealFat = ""
                mealProtein = ""
                mealSodium = ""
                currentMealDraftId = null
                currentMealDraftType = null
                nutritionDraftRawText = ""
                nutritionDraftConfidence = null
                nutritionDraftStatusText = ""
                clearMealDraft()
                refreshDashboardData()
                _notice.value = "餐食已保存。"
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "餐食保存失败。")
            } finally {
                mealBusy = false
            }
        }
    }

    fun saveCurrentMealAsPreset() {
        val actualGrams = mealActualGrams.toFloatOrNull()
        val kcal = mealKcal.toFloatOrNull()
        val carb = mealCarb.toFloatOrNull()
        val fat = mealFat.toFloatOrNull()
        val protein = mealProtein.toFloatOrNull()
        val sodium = mealSodium.toFloatOrNull()
        val name = mealPresetName.ifBlank { mealFoodName }
        if (name.isBlank() || actualGrams == null || actualGrams <= 0f || kcal == null || kcal < 0f) {
            _notice.value = "先把食物名称、每 100g 热量和实际克重填好，再保存为常用餐。"
            return
        }
        viewModelScope.launch {
            presetRepository.savePreset(
                name = name,
                mealSlot = selectedMealSlot,
                actualGrams = actualGrams,
                kcal = kcal,
                carbG = carb ?: 0f,
                fatG = fat ?: 0f,
                proteinG = protein ?: 0f,
                sodiumMg = sodium,
                note = if (nutritionDraftRawText.isBlank()) null else nutritionDraftRawText
            )
            mealPresetName = ""
            _notice.value = "已保存到本地快捷食物库。"
        }
    }

    fun applyPreset(preset: FoodPresetEntity) {
        selectedMealSlot = preset.mealSlot
        mealConsumedAt = currentMealDateTimeValue()
        mealFoodName = preset.name
        mealActualGrams = preset.actualGrams.toString()
        mealKcal = preset.kcal.toString()
        mealCarb = preset.carbG.toString()
        mealFat = preset.fatG.toString()
        mealProtein = preset.proteinG.toString()
        mealSodium = preset.sodiumMg?.toString().orEmpty()
        nutritionDraftRawText = preset.note.orEmpty()
        nutritionDraftConfidence = null
        _notice.value = "已套用常用餐：${preset.name}"
    }

    fun deletePreset(preset: FoodPresetEntity) {
        viewModelScope.launch {
            presetRepository.deletePreset(preset.id)
            _notice.value = "已删除常用餐：${preset.name}"
        }
    }

    fun copyMealToForm(meal: MealEntryResponse) {
        selectedMealSlot = meal.mealSlot
        mealConsumedAt = currentMealDateTimeValue()
        mealFoodName = meal.foodName
        mealActualGrams = meal.actualGrams.toString()
        mealKcal = per100Value(meal.kcal, meal.actualGrams)
        mealCarb = per100Value(meal.carbG, meal.actualGrams)
        mealFat = per100Value(meal.fatG, meal.actualGrams)
        mealProtein = per100Value(meal.proteinG, meal.actualGrams)
        mealSodium = meal.sodiumMg?.let { per100Value(it, meal.actualGrams) }.orEmpty()
        currentMealDraftId = meal.draftId
        currentMealDraftType = meal.draftType
        nutritionDraftRawText = meal.sourceRawText.orEmpty()
        nutritionDraftConfidence = null
        _notice.value = "已复制这餐到编辑区。"
    }

    fun copyMealsFromDate(sourceDate: LocalDate) {
        val sourceMeals = recentMeals
            .filter { runCatching { Instant.parse(it.consumedAt).atZone(ZoneId.systemDefault()).toLocalDate() }.getOrNull() == sourceDate }
            .sortedBy { it.consumedAt }
        if (sourceMeals.isEmpty()) {
            _notice.value = "这个日期没有可复制的餐食。"
            return
        }
        viewModelScope.launch {
            mealBusy = true
            try {
                val targetDate = LocalDate.now()
                for (meal in sourceMeals) {
                    val localTime = Instant.parse(meal.consumedAt).atZone(ZoneId.systemDefault()).toLocalTime()
                    val targetAt = targetDate.atTime(localTime).atZone(ZoneId.systemDefault()).toInstant().toString()
                    appStateRepository.createMeal(
                        MealEntryCreateRequest(
                            draftId = meal.draftId,
                            mealSlot = meal.mealSlot,
                            consumedAt = targetAt,
                            foodName = meal.foodName,
                            actualGrams = meal.actualGrams,
                            kcal = meal.kcal,
                            carbG = meal.carbG,
                            fatG = meal.fatG,
                            proteinG = meal.proteinG,
                            sodiumMg = meal.sodiumMg,
                            corrections = meal.corrections
                        )
                    )
                }
                refreshDashboardData()
                _notice.value = "已把 ${sourceDate} 的 ${sourceMeals.size} 餐复制到今天。"
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "复制整天餐食失败。")
            } finally {
                mealBusy = false
            }
        }
    }

    fun updateSelfieNote(value: String) {
        selfieNote = value
    }

    fun updateExerciseDistanceKm(value: String) {
        exerciseDistanceKm = value
    }

    fun updateExerciseDurationMin(value: String) {
        exerciseDurationMin = value
    }

    fun updateExerciseNote(value: String) {
        exerciseNote = value
    }

    fun applyExerciseTemplate(exerciseType: String) {
        selectedExerciseType = exerciseType
        when (exerciseType) {
            "mountain_bike_commute" -> {
                exerciseDistanceKm = "7"
                exerciseDurationMin = ""
                exerciseNote = "山地车通勤"
            }
            "badminton" -> {
                exerciseDistanceKm = ""
                exerciseDurationMin = "60"
                exerciseNote = "羽毛球"
            }
            "running_easy" -> {
                exerciseDistanceKm = "5"
                exerciseDurationMin = ""
                exerciseNote = "慢跑"
            }
            "running_tempo" -> {
                exerciseDistanceKm = "5"
                exerciseDurationMin = ""
                exerciseNote = "中速跑"
            }
            "running_fast" -> {
                exerciseDistanceKm = "5"
                exerciseDurationMin = ""
                exerciseNote = "快跑"
            }
            "walking" -> {
                exerciseDistanceKm = "5"
                exerciseDurationMin = ""
                exerciseNote = "步行"
            }
            "strength_training" -> {
                exerciseDistanceKm = ""
                exerciseDurationMin = "45"
                exerciseNote = "力量训练"
            }
            "swimming" -> {
                exerciseDistanceKm = ""
                exerciseDurationMin = "45"
                exerciseNote = "游泳"
            }
            else -> {
                exerciseDistanceKm = ""
                exerciseDurationMin = ""
                exerciseNote = ""
            }
        }
    }

    fun submitExercise(exerciseType: String = selectedExerciseType) {
        val distance = exerciseDistanceKm.toFloatOrNull()
        val duration = exerciseDurationMin.toFloatOrNull()
        if ((distance == null || distance <= 0f) && (duration == null || duration <= 0f)) {
            _notice.value = "请至少填写有效的运动距离或时长。"
            return
        }
        viewModelScope.launch {
            try {
                appStateRepository.createExercise(
                    ExerciseEntryCreateRequest(
                        exerciseType = exerciseType,
                        occurredAt = Instant.now().toString(),
                        distanceKm = distance?.takeIf { it > 0f },
                        durationMin = duration?.takeIf { it > 0f },
                        note = exerciseNote.ifBlank { null }
                    )
                )
                selectedExerciseType = "mountain_bike_commute"
                exerciseDistanceKm = "7"
                exerciseDurationMin = ""
                exerciseNote = ""
                refreshReportsData()
                _notice.value = "已记录额外运动。"
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "记录运动失败。")
            }
        }
    }

    fun uploadSelfie(imageBytes: ByteArray, fileName: String, mimeType: String?) {
        viewModelScope.launch {
            selfieBusy = true
            try {
                appStateRepository.uploadSelfie(
                    imageBytes = imageBytes,
                    fileName = fileName,
                    mimeType = mimeType,
                    note = selfieNote,
                    isShared = false
                )
                selfieNote = ""
                lastSelfieUploadAt = System.currentTimeMillis()
                refreshDashboardData()
                _notice.value = "自拍已上传。"
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "自拍上传失败。")
            } finally {
                selfieBusy = false
            }
        }
    }

    fun compareSelfies(firstAssetId: String, secondAssetId: String) {
        if (firstAssetId.isBlank() || secondAssetId.isBlank() || firstAssetId == secondAssetId) {
            _notice.value = "请选择两张不同的自拍再生成对比动图。"
            return
        }
        viewModelScope.launch {
            selfieBusy = true
            try {
                val result = appStateRepository.compareSelfies(firstAssetId, secondAssetId)
                comparisonGifUrl = resolveMediaUrl(result.gifUrl)
                _notice.value = "对比动图已生成。"
            } catch (error: Exception) {
                _notice.value = friendlyMessage(error, "对比动图生成失败。")
            } finally {
                selfieBusy = false
            }
        }
    }

    fun consumeNotice() {
        _notice.value = null
    }

    fun consumeWeightSubmitNavigation() {
        lastWeightSubmitAt = null
    }

    private fun resolveMediaUrl(path: String): String {
        return if (path.startsWith("http://") || path.startsWith("https://")) {
            path
        } else {
            "${serverUrl.value.substringBefore("/api/")}$path"
        }
    }

    private fun clearMealDraft() {
        mealConsumedAt = currentMealDateTimeValue()
        mealFoodName = ""
        mealActualGrams = ""
        mealKcal = ""
        mealCarb = ""
        mealFat = ""
        mealProtein = ""
        mealSodium = ""
        mealPresetName = ""
        dishEstimateHint = ""
        currentMealDraftId = null
        currentMealDraftType = null
        nutritionDraftRawText = ""
        nutritionDraftConfidence = null
        nutritionDraftStatusText = ""
        nutritionDraftPending = false
    }

    private fun mealConsumedAtToInstantString(): String {
        val parsed = LocalDateTime.parse(mealConsumedAt, MealTimeFormatter)
        return parsed.atZone(ZoneId.systemDefault()).toInstant().toString()
    }

    private fun currentMealDateTimeValue(): String {
        return LocalDateTime.now().withSecond(0).withNano(0).format(MealTimeFormatter)
    }

    private fun applyNutritionDraft(draft: NutritionDraftResponse) {
        mealFoodName = draft.foodName?.takeIf { it.isNotBlank() } ?: mealFoodName
        if (mealActualGrams.isBlank()) {
            val estimated = draft.estimatedGrams?.takeIf { it > 0f }
            if (estimated != null) {
                mealActualGrams = formatDraftNumber(estimated)
            }
        }
        mealKcal = draft.per100gKcal?.toString().orEmpty()
        mealCarb = draft.per100gCarbG?.toString().orEmpty()
        mealFat = draft.per100gFatG?.toString().orEmpty()
        mealProtein = draft.per100gProteinG?.toString().orEmpty()
        mealSodium = draft.per100gSodiumMg?.toString().orEmpty()
        currentMealDraftId = draft.id
        currentMealDraftType = draft.draftType
        nutritionDraftRawText = draft.rawText.orEmpty()
        nutritionDraftConfidence = draft.confidence
        val scopeLabel = draft.estimatedScope?.let { weightScopeLabel(it) }
        val breakdown = buildWeightBreakdownText(
            total = draft.estimatedGrams,
            solid = draft.estimatedSolidGrams,
            liquid = draft.estimatedLiquidGrams
        )
        nutritionDraftStatusText = when {
            draft.estimatedGrams != null && draft.estimatedGrams > 0f && !scopeLabel.isNullOrBlank() && !breakdown.isNullOrBlank() ->
                "识别完成，已回填估算重量 ${formatDraftNumber(draft.estimatedGrams)}g。计重口径：$scopeLabel；$breakdown。"
            draft.estimatedGrams != null && draft.estimatedGrams > 0f ->
                "识别完成，已回填估算重量 ${formatDraftNumber(draft.estimatedGrams)}g，请确认后保存。"
            else ->
                "识别完成，请确认名称和每 100g 估算值。"
        }
        nutritionDraftPending = false
    }

    private fun formatDraftNumber(value: Float): String {
        val rounded = kotlin.math.round(value * 10f) / 10f
        return if (rounded % 1f == 0f) {
            rounded.toInt().toString()
        } else {
            rounded.toString()
        }
    }

    private fun buildWeightBreakdownText(total: Float?, solid: Float?, liquid: Float?): String {
        val parts = mutableListOf<String>()
        if (solid != null && solid > 0f) {
            parts += "固形物 ${formatDraftNumber(solid)}g"
        }
        if (liquid != null && liquid > 0f) {
            parts += "汤汁/液体 ${formatDraftNumber(liquid)}g"
        }
        if (total != null && total > 0f) {
            parts += "总量 ${formatDraftNumber(total)}g"
        }
        return parts.joinToString("，")
    }

    private fun weightScopeLabel(scope: String): String = when (scope) {
        "solid_only" -> "只算固形物"
        "includes_liquid" -> "包含汤汁/液体"
        "liquid_only" -> "只算液体"
        "unclear" -> "口径不明确"
        else -> scope
    }
    private fun startNutritionDraftPolling(draftId: String) {
        nutritionDraftPollingJob?.cancel()
        nutritionDraftPollingJob = viewModelScope.launch {
            repeat(30) {
                delay(2_000)
                try {
                    val draft = appStateRepository.getNutritionDraft(draftId)
                    when (draft.status) {
                        "ready" -> {
                            applyNutritionDraft(draft)
                            dishEstimateHint = ""
                            _notice.value = "AI 识别完成，请检查名称和估算结果，并手动输入实际重量。"
                            return@launch
                        }
                        "failed" -> {
                            dishEstimateHint = ""
                            nutritionDraftPending = false
                            nutritionDraftStatusText = draft.errorMessage ?: "后台识别失败，请稍后重试。"
                            _notice.value = nutritionDraftStatusText
                            return@launch
                        }
                    }
                } catch (_: Exception) {
                    // Ignore transient polling failures and keep waiting.
                }
            }
            nutritionDraftPending = false
            nutritionDraftStatusText = "后台识别仍在继续，可稍后刷新查看。"
        }
    }

    private fun per100Value(value: Float, actualGrams: Float): String {
        if (actualGrams <= 0f) return ""
        return ((value / actualGrams) * 100f).toString()
    }

    private fun queuedSyncNotice(baseMessage: String, syncedCount: Int): String {
        return if (syncedCount > 0) {
            "$baseMessage，已补传 $syncedCount 条离线晨重。"
        } else {
            baseMessage
        }
    }

    private fun friendlyMessage(error: Throwable, fallback: String): String {
        if (error is HttpException) {
            val body = runCatching { error.response()?.errorBody()?.string() }.getOrNull()?.trim().orEmpty()
            if (body.isNotBlank()) {
                val jsonDetail = runCatching { JSONObject(body).optString("detail") }.getOrNull().orEmpty()
                if (jsonDetail.isNotBlank()) {
                    return jsonDetail
                }
                return body
            }
        }
        return error.message ?: fallback
    }

    companion object {
        fun factory(
            themeRepository: ThemePreferencesRepository,
            appStateRepository: AppStateRepository,
            syncRepository: SyncRepository,
            foodPresetRepository: FoodPresetRepository
        ): ViewModelProvider.Factory {
            return object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    @Suppress("UNCHECKED_CAST")
                    return MainViewModel(
                        preferencesRepository = themeRepository,
                        appStateRepository = appStateRepository,
                        syncRepository = syncRepository,
                        foodPresetRepository = foodPresetRepository
                    ) as T
                }
            }
        }
    }
}
