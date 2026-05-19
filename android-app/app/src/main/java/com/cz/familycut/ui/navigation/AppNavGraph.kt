package com.cz.familycut.ui.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Assessment
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.MonitorWeight
import androidx.compose.material.icons.outlined.PhotoCamera
import androidx.compose.material.icons.outlined.Restaurant
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.cz.familycut.data.model.UserSession
import com.cz.familycut.ui.components.GlassSnackbarHost
import com.cz.familycut.ui.components.GlassSecondaryButton
import com.cz.familycut.ui.screens.HomeScreen
import com.cz.familycut.ui.screens.InviteJoinScreen
import com.cz.familycut.ui.screens.LoginScreen
import com.cz.familycut.ui.screens.MealsScreen
import com.cz.familycut.ui.screens.ProfileSetupScreen
import com.cz.familycut.ui.screens.ReportsScreen
import com.cz.familycut.ui.screens.SelfieScreen
import com.cz.familycut.ui.screens.SettingsScreen
import com.cz.familycut.ui.screens.WeightEntryScreen
import com.cz.familycut.ui.viewmodel.MainViewModel

private object Routes {
    const val Login = "login"
    const val InviteJoin = "invite_join"
    const val ProfileSetup = "profile_setup"
    const val Home = "home"
    const val Weight = "weight"
    const val Meals = "meals"
    const val Selfie = "selfie"
    const val Reports = "reports"
    const val Settings = "settings"
}

private data class MainDestination(
    val route: String,
    val label: String,
    val icon: @Composable () -> Unit
)

private val mainDestinations = listOf(
    MainDestination(Routes.Home, "首页") { Icon(Icons.Outlined.Home, contentDescription = null) },
    MainDestination(Routes.Weight, "晨重") { Icon(Icons.Outlined.MonitorWeight, contentDescription = null) },
    MainDestination(Routes.Meals, "餐食") { Icon(Icons.Outlined.Restaurant, contentDescription = null) },
    MainDestination(Routes.Selfie, "自拍") { Icon(Icons.Outlined.PhotoCamera, contentDescription = null) },
    MainDestination(Routes.Reports, "日报") { Icon(Icons.Outlined.Assessment, contentDescription = null) }
)

@Composable
fun AppNavGraph(
    session: UserSession?,
    viewModel: MainViewModel,
    snackbarHostState: SnackbarHostState,
    navController: NavHostController = rememberNavController()
) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    LaunchedEffect(session?.memberId, viewModel.profileNeedsCompletion) {
        val route = when {
            session == null -> Routes.Login
            viewModel.profileNeedsCompletion -> Routes.ProfileSetup
            else -> Routes.Home
        }
        navController.navigate(route) {
            popUpTo(navController.graph.startDestinationId) {
                inclusive = true
            }
            launchSingleTop = true
        }
    }

    LaunchedEffect(currentRoute, session?.memberId) {
        if (session != null && currentRoute == Routes.Reports) {
            viewModel.refreshReportsData()
        }
    }
    val showBottomBar = session != null && !viewModel.profileNeedsCompletion && currentRoute in mainDestinations.map { it.route }

    Scaffold(
        topBar = {
            AppTopBar(
                currentRoute = currentRoute,
                session = session,
                canNavigateBack = currentRoute in listOf(Routes.InviteJoin, Routes.Settings),
                onBack = { navController.popBackStack() },
                onOpenSettings = { navController.navigate(Routes.Settings) }
            )
        },
        bottomBar = {
            if (showBottomBar) {
                Card(
                    modifier = Modifier
                        .padding(horizontal = 14.dp, vertical = 10.dp)
                        .fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.94f)
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 10.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 8.dp, vertical = 6.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        mainDestinations.forEach { destination ->
                            val selected = backStackEntry?.destination?.hierarchy?.any { it.route == destination.route } == true
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .background(
                                        color = if (selected) {
                                            MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.76f)
                                        } else {
                                            MaterialTheme.colorScheme.surface.copy(alpha = 0f)
                                        },
                                        shape = MaterialTheme.shapes.medium
                                    )
                                    .clickable {
                                        navController.navigate(destination.route) {
                                            popUpTo(Routes.Home) {
                                                saveState = true
                                            }
                                            launchSingleTop = true
                                            restoreState = true
                                        }
                                    }
                                    .padding(vertical = 10.dp, horizontal = 6.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    val tint = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                                    androidx.compose.runtime.CompositionLocalProvider(androidx.compose.material3.LocalContentColor provides tint) {
                                        destination.icon()
                                    }
                                    Text(
                                        text = destination.label,
                                        style = MaterialTheme.typography.labelMedium,
                                        color = tint
                                    )
                                }
                            }
                        }
                    }
                }
            }
        },
        snackbarHost = { GlassSnackbarHost(hostState = snackbarHostState) }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = if (session == null) Routes.Login else Routes.Home
        ) {
            composable(Routes.Login) {
                LoginScreen(
                    loginBusy = viewModel.loginBusy,
                    serverUrl = viewModel.serverUrl.value,
                    onLogin = { serverUrl, username, password ->
                        viewModel.login(serverUrl, username, password)
                    },
                    onOpenInviteJoin = { navController.navigate(Routes.InviteJoin) }
                )
            }
            composable(Routes.InviteJoin) {
                InviteJoinScreen(
                    innerPadding = innerPadding,
                    busy = viewModel.loginBusy,
                    serverUrl = viewModel.serverUrl.value,
                    invitePreview = viewModel.invitePreviewText,
                    onPreviewInvite = { serverUrl, code ->
                        viewModel.previewInvite(serverUrl, code)
                    },
                    onJoin = { serverUrl, code, username, password, displayName, sex, birthYear ->
                        viewModel.registerByInvite(serverUrl, code, username, password, displayName, sex, birthYear)
                    }
                )
            }
            composable(Routes.ProfileSetup) {
                ProfileSetupScreen(
                    innerPadding = innerPadding,
                    session = session,
                    busy = viewModel.loginBusy,
                    onSave = viewModel::completeProfile
                )
            }
            composable(Routes.Home) {
                HomeScreen(
                    innerPadding = innerPadding,
                    session = session,
                    dashboardLoading = viewModel.dashboardLoading,
                    recentMeasurements = viewModel.recentMeasurements,
                    recentMeals = viewModel.recentMeals,
                    recentSelfies = viewModel.recentSelfies,
                    todayReport = viewModel.todayReport,
                    onOpenWeightEntry = { navController.navigate(Routes.Weight) },
                    onOpenMeals = { navController.navigate(Routes.Meals) },
                    onOpenSelfies = { navController.navigate(Routes.Selfie) },
                    onOpenReports = { navController.navigate(Routes.Reports) },
                    onOpenSettings = { navController.navigate(Routes.Settings) },
                    onRefresh = viewModel::refreshDashboardData
                )
            }
            composable(Routes.Weight) {
                WeightEntryScreen(
                    innerPadding = innerPadding,
                    weightInput = viewModel.weightInput,
                    bodyFatInput = viewModel.bodyFatInput,
                    lastWeightSubmitAt = viewModel.lastWeightSubmitAt,
                    recentMeasurements = viewModel.recentMeasurements,
                    onWeightChange = viewModel::updateWeightInput,
                    onBodyFatChange = viewModel::updateBodyFatInput,
                    onSave = viewModel::submitWeight,
                    onSaved = {
                        val returned = navController.popBackStack(Routes.Home, inclusive = false)
                        if (!returned) {
                            navController.navigate(Routes.Home) {
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                    },
                    onSavedHandled = viewModel::consumeWeightSubmitNavigation
                )
            }
            composable(Routes.Meals) {
                MealsScreen(
                    innerPadding = innerPadding,
                    serverUrl = viewModel.serverUrl.value,
                    todayReport = viewModel.todayReport,
                    mealBusy = viewModel.mealBusy,
                    nutritionDraftBusy = viewModel.nutritionDraftBusy,
                    nutritionDraftPending = viewModel.nutritionDraftPending,
                    lastNutritionDraftCreatedAt = viewModel.lastNutritionDraftCreatedAt,
                    selectedMealSlot = viewModel.selectedMealSlot,
                    foodName = viewModel.mealFoodName,
                    consumedAt = viewModel.mealConsumedAt,
                    actualGrams = viewModel.mealActualGrams,
                    kcal = viewModel.mealKcal,
                    carb = viewModel.mealCarb,
                    fat = viewModel.mealFat,
                    protein = viewModel.mealProtein,
                    sodium = viewModel.mealSodium,
                    presetName = viewModel.mealPresetName,
                    dishEstimateHint = viewModel.dishEstimateHint,
                    nutritionDraftRawText = viewModel.nutritionDraftRawText,
                    nutritionDraftConfidence = viewModel.nutritionDraftConfidence,
                    nutritionDraftStatusText = viewModel.nutritionDraftStatusText,
                    recentMeals = viewModel.recentMeals,
                    foodPresets = viewModel.foodPresets.value,
                    onSelectMealSlot = viewModel::selectMealSlot,
                    onFoodNameChange = viewModel::updateMealFoodName,
                    onConsumedAtChange = viewModel::updateMealConsumedAt,
                    onUseCurrentTime = viewModel::useCurrentMealTime,
                    onActualGramsChange = viewModel::updateMealActualGrams,
                    onKcalChange = viewModel::updateMealKcal,
                    onCarbChange = viewModel::updateMealCarb,
                    onFatChange = viewModel::updateMealFat,
                    onProteinChange = viewModel::updateMealProtein,
                    onSodiumChange = viewModel::updateMealSodium,
                    onPresetNameChange = viewModel::updateMealPresetName,
                    onDishEstimateHintChange = viewModel::updateDishEstimateHint,
                    onCreateNutritionDraft = viewModel::createNutritionDraft,
                    onApplyPreset = viewModel::applyPreset,
                    onDeletePreset = viewModel::deletePreset,
                    onCopyMeal = viewModel::copyMealToForm,
                    onCopyDay = viewModel::copyMealsFromDate,
                    onSaveCurrentAsPreset = viewModel::saveCurrentMealAsPreset,
                    onSubmitMeal = viewModel::submitMeal
                )
            }
            composable(Routes.Selfie) {
                SelfieScreen(
                    innerPadding = innerPadding,
                    serverUrl = viewModel.serverUrl.value,
                    selfieBusy = viewModel.selfieBusy,
                    lastSelfieUploadAt = viewModel.lastSelfieUploadAt,
                    selfieNote = viewModel.selfieNote,
                    recentSelfies = viewModel.recentSelfies,
                    onNoteChange = viewModel::updateSelfieNote,
                    onUpload = viewModel::uploadSelfie
                )
            }
            composable(Routes.Reports) {
                ReportsScreen(
                    innerPadding = innerPadding,
                    serverUrl = viewModel.serverUrl.value,
                    todayReport = viewModel.todayReport,
                    weeklyReport = viewModel.weeklyReport,
                    monthlyReport = viewModel.monthlyReport,
                    recentReports = viewModel.recentReports,
                    recentExercises = viewModel.recentExercises,
                    selectedExerciseType = viewModel.selectedExerciseType,
                    exerciseDistanceKm = viewModel.exerciseDistanceKm,
                    exerciseDurationMin = viewModel.exerciseDurationMin,
                    exerciseNote = viewModel.exerciseNote,
                    onApplyExerciseTemplate = viewModel::applyExerciseTemplate,
                    onExerciseDistanceChange = viewModel::updateExerciseDistanceKm,
                    onExerciseDurationChange = viewModel::updateExerciseDurationMin,
                    onExerciseNoteChange = viewModel::updateExerciseNote,
                    onSubmitExercise = viewModel::submitExercise,
                    dashboardLoading = viewModel.dashboardLoading,
                    onRefresh = viewModel::refreshReportsData
                )
            }
            composable(Routes.Settings) {
                SettingsScreen(
                    innerPadding = innerPadding,
                    selectedThemeMode = viewModel.themeModeValue,
                    serverUrl = viewModel.serverUrl.value,
                    onSelectTheme = viewModel::setThemeMode,
                    onSaveServerUrl = viewModel::saveServerUrl,
                    onLogout = viewModel::logout
                )
            }
        }
    }
}

@Composable
private fun AppTopBar(
    currentRoute: String?,
    session: UserSession?,
    canNavigateBack: Boolean,
    onBack: () -> Unit,
    onOpenSettings: () -> Unit
) {
    val title = when (currentRoute) {
        Routes.Home -> "今日概览"
        Routes.Weight -> "晨重"
        Routes.Meals -> "餐食"
        Routes.Selfie -> "自拍"
        Routes.Reports -> "日报"
        Routes.Settings -> "设置"
        Routes.InviteJoin -> "邀请码加入"
        Routes.ProfileSetup -> "完善资料"
        else -> null
    }
    if (title == null || currentRoute == Routes.Login) {
        return
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.94f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 10.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(2.dp),
                modifier = Modifier.weight(1f)
            ) {
                Text(title, style = MaterialTheme.typography.titleLarge)
                if (session != null && currentRoute in mainDestinations.map { it.route }) {
                    Text(
                        text = session.displayName,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else if (currentRoute == Routes.ProfileSetup) {
                    Text(
                        text = "完成后自动进入首页",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.widthIn(max = 180.dp)) {
                if (canNavigateBack) {
                    GlassSecondaryButton(text = "返回", onClick = onBack, modifier = Modifier.weight(1f))
                }
                if (currentRoute in mainDestinations.map { it.route }) {
                    GlassSecondaryButton(text = "设置", onClick = onOpenSettings, modifier = Modifier.weight(1f))
                }
            }
        }
    }
}
